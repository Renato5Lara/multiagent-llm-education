"""TavilyClient — async HTTP client with tenacity retries, timeout policies, and observability."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.core.config import settings
from app.integrations.tavily.errors import (
    TavilyAPIError,
    TavilyAuthError,
    TavilyConfigurationError,
    TavilyError,
    TavilyRateLimitError,
    TavilyTimeoutError,
)
from app.integrations.tavily.schemas import (
    SearchDepth,
    TavilyQueryResult,
    TavilySearchResponse,
    TavilySource,
)
from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)

TAVILY_API_KEY_ENV = "TAVILY_API_KEY"
TAVILY_DEFAULT_TIMEOUT = 15.0
TAVILY_MAX_RETRIES = 3
TAVILY_BASE_URL = "https://api.tavily.com"


def _load_api_key() -> str:
    key = os.getenv(TAVILY_API_KEY_ENV) or getattr(settings, "TAVILY_API_KEY", "")
    if not key:
        logger.warning(
            "TAVILY_API_KEY not found in environment or settings. "
            "ResearchAgent will operate in degraded heuristic mode."
        )
        return ""
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    logger.info("Tavily API key loaded: %s", masked)
    return key


def _query_hash(query: str, depth: SearchDepth) -> str:
    raw = f"{query}|{depth.value}"
    return hashlib.sha256(raw.encode()).hexdigest()


class TavilyClient:
    """Async HTTP client for Tavily Search API with production-grade resilience.

    Features:
    - httpx.AsyncClient with connection pooling
    - tenacity-based retry with exponential backoff
    - Structured error hierarchy
    - Observability (metrics, tracing)
    - Graceful degradation
    - Connection timeout + read timeout
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = TAVILY_BASE_URL,
        timeout_seconds: float = TAVILY_DEFAULT_TIMEOUT,
        max_retries: int = TAVILY_MAX_RETRIES,
    ):
        self._api_key = api_key or _load_api_key()
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._initialized = bool(self._api_key)

        if not self._initialized:
            logger.warning("TavilyClient initialized without API key — all searches will fail gracefully.")

        self._client: httpx.AsyncClient | None = None

    @property
    def api_key(self) -> str:
        return self._api_key

    @property
    def is_enabled(self) -> bool:
        return self._initialized

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=5.0),
                limits=limits,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> TavilyClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Public search API ─────────────────────────────────────────

    async def search(
        self,
        query: str,
        depth: SearchDepth = SearchDepth.BASIC,
        max_results: int = 5,
        include_answer: bool = True,
        include_raw_content: bool = False,
    ) -> TavilySearchResponse:
        """Execute a single Tavily search query with retries.

        Args:
            query: Search query string
            depth: SearchDepth.BASIC (faster, cheaper) or ADVANCED
            max_results: Max sources to return (1-10)
            include_answer: Include AI-generated answer
            include_raw_content: Include full raw page content

        Returns:
            TavilySearchResponse with results, answer, metadata

        Raises:
            TavilyAuthError: Invalid/missing API key
            TavilyRateLimitError: Rate limited
            TavilyTimeoutError: Request timed out
            TavilyAPIError: Other API errors
        """
        if not self._initialized:
            exporter.inc_counter("tavily_skipped_no_key")
            raise TavilyConfigurationError(
                "Tavily API key not configured. Set TAVILY_API_KEY env var."
            )

        payload = {
            "query": query,
            "search_depth": depth.value,
            "max_results": min(max(max_results, 1), 10),
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        start_ms = time.monotonic() * 1000
        exporter.inc_counter("tavily_queries_total")

        try:
            response = await self._execute_with_retry(payload)
            elapsed_ms = (time.monotonic() * 1000) - start_ms
            exporter.observe_histogram("tavily_query_duration_ms", elapsed_ms)
            exporter.inc_counter("tavily_queries_success")

            parsed = self._parse_response(response, query, elapsed_ms)
            logger.debug(
                "Tavily search OK: query='%s' sources=%d time=%.0fms",
                query[:40], parsed.source_count, elapsed_ms,
            )
            return parsed

        except TavilyRateLimitError:
            exporter.inc_counter("tavily_rate_limited")
            raise
        except TavilyAuthError:
            exporter.inc_counter("tavily_auth_errors")
            raise
        except TavilyTimeoutError:
            exporter.inc_counter("tavily_timeouts")
            raise
        except TavilyError:
            exporter.inc_counter("tavily_errors")
            raise
        except Exception as e:
            elapsed_ms = (time.monotonic() * 1000) - start_ms
            exporter.inc_counter("tavily_unexpected_errors")
            raise TavilyError(f"Unexpected Tavily error: {e}", original=e) from e

    # ── Retry logic ──────────────────────────────────────────────

    @retry(
        retry=(
            retry_if_exception_type(TavilyTimeoutError)
            | retry_if_exception_type(TavilyAPIError)
        ),
        stop=stop_after_attempt(TAVILY_MAX_RETRIES),
        wait=wait_exponential(multiplier=1.0, min=1.0, max=10.0),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _execute_with_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        client = await self._get_client()
        url = f"{self._base_url}/search"

        try:
            response = await client.post(url, json=payload)
        except httpx.TimeoutException as e:
            raise TavilyTimeoutError(self._timeout) from e
        except httpx.ConnectError as e:
            raise TavilyTimeoutError(self._timeout) from e
        except httpx.HTTPError as e:
            raise TavilyAPIError(0, str(e)) from e

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "60"))
            raise TavilyRateLimitError(retry_after=retry_after)

        if response.status_code == 401 or response.status_code == 403:
            raise TavilyAuthError()

        if response.status_code >= 500:
            raise TavilyAPIError(response.status_code, response.text)

        if response.status_code != 200:
            raise TavilyAPIError(response.status_code, response.text)

        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise TavilyAPIError(response.status_code, "Invalid JSON response") from e

    # ── Response parsing ──────────────────────────────────────────

    def _parse_response(
        self,
        data: dict[str, Any],
        query: str,
        elapsed_ms: float,
    ) -> TavilySearchResponse:
        results = []
        for item in data.get("results", []):
            try:
                source = TavilySource(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=float(item.get("score", 0.0)),
                    raw_content=item.get("raw_content"),
                )
                results.append(source)
            except (ValueError, TypeError) as e:
                logger.debug("Skipping malformed Tavily result: %s", e)
                continue

        return TavilySearchResponse(
            query=query,
            results=results,
            answer=data.get("answer"),
            response_time_ms=elapsed_ms,
            tokens_used=data.get("tokens_used", 0),
        )

    # ── Health check ──────────────────────────────────────────────

    async def health_check(self) -> dict[str, Any]:
        """Check API key validity and service availability."""
        if not self._initialized:
            return {"ok": False, "error": "No API key configured", "configured": False}

        try:
            result = await self.search(
                query="health check",
                depth=SearchDepth.BASIC,
                max_results=1,
                include_answer=False,
            )
            return {
                "ok": True,
                "latency_ms": result.response_time_ms,
                "configured": True,
                "key_preview": self._api_key[:8] + "..." if self._api_key else "",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)[:200], "configured": True}


# Singleton instance — lazy-initialized
_client_instance: TavilyClient | None = None


def get_tavily_client() -> TavilyClient:
    global _client_instance
    if _client_instance is None:
        _client_instance = TavilyClient()
    return _client_instance
