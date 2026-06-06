"""LLM Service — unified async interface for multiple LLM providers.

Supports OpenAI SDK, Anthropic SDK, and any OpenAI-compatible endpoint.
All calls are traced, budget-checked, and retried with exponential backoff.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

import httpx

from app.llm.config import LLMConfig, ProviderKind
from app.llm.cost_tracker import TokenBudgetTracker

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from an LLM invocation."""

    content: str
    parsed: dict[str, Any] | None
    model: str
    provider: str
    tokens_prompt: int
    tokens_completion: int
    tokens_total: int
    confidence_raw: float
    duration_ms: float
    success: bool
    error: str | None = None
    raw_response: Any = None


class LLMService:
    """Async LLM invocation with provider abstraction, retry, and budget control.

    Usage:
        service = LLMService(budget_tracker)
        response = await service.generate(
            messages=[{"role": "user", "content": "..."}],
            voter_name="pedagogical",
        )
    """

    def __init__(
        self,
        budget_tracker: TokenBudgetTracker | None = None,
        configs: dict[str, LLMConfig] | None = None,
        default_config: LLMConfig | None = None,
    ):
        self._budget_tracker = budget_tracker or TokenBudgetTracker()
        self._configs = configs or {}
        self._default = default_config or LLMConfig()
        self._client = httpx.AsyncClient(timeout=30.0)

    async def generate(
        self,
        messages: list[dict],
        voter_name: str = "default",
        *,
        config: LLMConfig | None = None,
        response_format: Literal["json", "text"] | None = "json",
    ) -> LLMResponse:
        """Invoke the LLM with budget check, retry, and structured parsing.

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            voter_name: Used to look up per-voter config and budget
            config: Override config (uses voter config or default otherwise)
            response_format: "json" forces JSON mode, "text" returns raw

        Returns:
            LLMResponse with parsed content and metadata
        """
        cfg = config or self._configs.get(voter_name, self._default)
        estimated = self._estimate_tokens(messages, cfg.max_tokens)

        if not self._budget_tracker.check_budget(voter_name, estimated, cfg.budget_tokens_per_day):
            logger.warning("Budget exceeded for voter=%s, estimated=%d", voter_name, estimated)
            return LLMResponse(
                content="",
                parsed=None,
                model=cfg.model,
                provider=cfg.provider_kind.value,
                tokens_prompt=0,
                tokens_completion=0,
                tokens_total=0,
                confidence_raw=0.0,
                duration_ms=0.0,
                success=False,
                error="budget_exceeded",
            )

        provider = self._get_provider(cfg)
        start = time.monotonic()

        for attempt in range(cfg.max_retries + 1):
            try:
                result = await provider(messages, cfg, response_format)
                elapsed_ms = (time.monotonic() - start) * 1000
                await self._budget_tracker.record_usage(voter_name, result.tokens_total)
                return result

            except Exception as e:
                elapsed_ms = (time.monotonic() - start) * 1000
                logger.warning(
                    "LLM call failed voter=%s attempt=%d/%d error=%s",
                    voter_name, attempt + 1, cfg.max_retries + 1, e,
                )
                if attempt < cfg.max_retries:
                    await self._wait(cfg.retry_delay_seconds * (2 ** attempt))
                else:
                    return LLMResponse(
                        content="",
                        parsed=None,
                        model=cfg.model,
                        provider=cfg.provider_kind.value,
                        tokens_prompt=0,
                        tokens_completion=0,
                        tokens_total=0,
                        confidence_raw=0.0,
                        duration_ms=elapsed_ms,
                        success=False,
                        error=str(e),
                    )

    def _get_provider(self, cfg: LLMConfig):
        providers = {
            ProviderKind.OPENAI: self._call_openai,
            ProviderKind.OPENAI_COMPATIBLE: self._call_openai_compatible,
            ProviderKind.ANTHROPIC: self._call_anthropic,
        }
        return providers.get(cfg.provider_kind, self._call_openai_compatible)

    async def _call_openai(self, messages: list[dict], cfg: LLMConfig, fmt) -> LLMResponse:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=cfg.api_key,
            timeout=httpx.Timeout(cfg.timeout_seconds),
        )
        kwargs = dict(
            model=cfg.model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        if fmt == "json":
            kwargs["response_format"] = {"type": "json_object"}

        resp = await client.chat.completions.create(**kwargs)
        choice = resp.choices[0]

        content = choice.message.content or ""
        parsed = self._try_parse_json(content)
        raw_conf = self._extract_openai_confidence(choice)

        return LLMResponse(
            content=content,
            parsed=parsed,
            model=cfg.model,
            provider="openai",
            tokens_prompt=resp.usage.prompt_tokens if resp.usage else 0,
            tokens_completion=resp.usage.completion_tokens if resp.usage else 0,
            tokens_total=resp.usage.total_tokens if resp.usage else 0,
            confidence_raw=raw_conf,
            duration_ms=0.0,
            success=True,
            raw_response=resp,
        )

    async def _call_openai_compatible(self, messages: list[dict], cfg: LLMConfig, fmt) -> LLMResponse:
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        body = dict(
            model=cfg.model,
            messages=messages,
            temperature=cfg.temperature,
            max_tokens=cfg.max_tokens,
        )
        if fmt == "json":
            body["response_format"] = {"type": "json_object"}

        resp = await self._client.post(
            cfg.base_url or "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=cfg.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]
        content = choice.get("message", {}).get("content", "")

        usage = data.get("usage", {})
        parsed = self._try_parse_json(content)

        return LLMResponse(
            content=content,
            parsed=parsed,
            model=cfg.model,
            provider="openai_compatible",
            tokens_prompt=usage.get("prompt_tokens", 0),
            tokens_completion=usage.get("completion_tokens", 0),
            tokens_total=usage.get("total_tokens", 0),
            confidence_raw=self._extract_json_confidence(parsed),
            duration_ms=0.0,
            success=True,
            raw_response=data,
        )

    async def _call_anthropic(self, messages: list[dict], cfg: LLMConfig, fmt) -> LLMResponse:
        headers = {
            "Content-Type": "application/json",
            "x-api-key": cfg.api_key,
            "anthropic-version": "2023-06-01",
        }
        system = ""
        chat_messages = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})

        body = dict(
            model=cfg.model,
            messages=chat_messages,
            max_tokens=cfg.max_tokens,
            temperature=cfg.temperature,
        )
        if system:
            body["system"] = system

        resp = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
            timeout=cfg.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["content"][0]["text"] if data.get("content") else ""
        usage = data.get("usage", {})

        parsed = self._try_parse_json(content)

        return LLMResponse(
            content=content,
            parsed=parsed,
            model=cfg.model,
            provider="anthropic",
            tokens_prompt=usage.get("input_tokens", 0),
            tokens_completion=usage.get("output_tokens", 0),
            tokens_total=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            confidence_raw=self._extract_json_confidence(parsed),
            duration_ms=0.0,
            success=True,
            raw_response=data,
        )

    @staticmethod
    def _try_parse_json(content: str) -> dict | None:
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            import re
            m = re.search(r"\{.*\}", content, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
            return None

    @staticmethod
    def _extract_json_confidence(parsed: dict | None) -> float:
        if parsed and isinstance(parsed, dict):
            conf = parsed.get("confidence", 0.5)
            if isinstance(conf, (int, float)):
                return max(0.0, min(1.0, float(conf)))
        return 0.5

    @staticmethod
    def _extract_openai_confidence(choice) -> float:
        if hasattr(choice, "logprobs") and choice.logprobs and choice.logprobs.content:
            probs = [t.logprob for t in choice.logprobs.content if t.logprob is not None]
            if probs:
                return float(2 ** (sum(probs) / len(probs)))
        return 0.5

    @staticmethod
    def _estimate_tokens(messages: list[dict], max_tokens: int) -> int:
        total = sum(len(str(m.get("content", ""))) // 4 for m in messages)
        return total + max_tokens

    @staticmethod
    async def _wait(seconds: float):
        import asyncio
        await asyncio.sleep(seconds)

    async def close(self):
        await self._client.aclose()
