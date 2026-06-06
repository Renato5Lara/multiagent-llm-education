"""LLM configuration — provider, model, budget, and timeout settings."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class ProviderKind(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENAI_COMPATIBLE = "openai_compatible"


_DEFAULT_BUDGETS: dict[str, int] = {
    "pedagogical": 100_000,
    "adaptive": 500_000,
    "evaluation": 500_000,
    "mediator": 50_000,
}


@dataclass
class LLMConfig:
    """Per-voter LLM configuration.

    Each voter can have its own model, provider, temperature, and budget.
    Defaults are designed for cost-sensitive educational deployment.
    """

    provider_kind: ProviderKind = ProviderKind.OPENAI
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.3
    max_tokens: int = 1024
    timeout_seconds: float = 30.0
    max_retries: int = 2
    retry_delay_seconds: float = 1.0
    budget_tokens_per_day: int = 500_000

    @classmethod
    def from_env(cls, prefix: str = "LLM_") -> LLMConfig:
        return cls(
            provider_kind=ProviderKind(os.getenv(f"{prefix}PROVIDER", "openai").lower()),
            model=os.getenv(f"{prefix}MODEL", "gpt-4o-mini"),
            api_key=os.getenv(f"{prefix}API_KEY", ""),
            base_url=os.getenv(f"{prefix}BASE_URL", ""),
            temperature=float(os.getenv(f"{prefix}TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv(f"{prefix}MAX_TOKENS", "1024")),
            timeout_seconds=float(os.getenv(f"{prefix}TIMEOUT", "30.0")),
            max_retries=int(os.getenv(f"{prefix}MAX_RETRIES", "2")),
        )


DEFAULT_LLM_CONFIGS: dict[str, LLMConfig] = {
    "pedagogical": LLMConfig(
        model="gpt-4o",
        temperature=0.3,
        max_tokens=1024,
        budget_tokens_per_day=100_000,
    ),
    "adaptive": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=768,
        budget_tokens_per_day=500_000,
    ),
    "evaluation": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=768,
        budget_tokens_per_day=500_000,
    ),
    "mediator": LLMConfig(
        model="gpt-4o",
        temperature=0.2,
        max_tokens=2048,
        budget_tokens_per_day=50_000,
    ),
    "research": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=1024,
        budget_tokens_per_day=200_000,
    ),
    "adaptive_learning": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=768,
        budget_tokens_per_day=200_000,
    ),
    "multimodal_planning": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=1024,
        budget_tokens_per_day=100_000,
    ),
    "prompt_engineering": LLMConfig(
        model="gpt-4o",
        temperature=0.4,
        max_tokens=2048,
        budget_tokens_per_day=300_000,
    ),
    "consistency": LLMConfig(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=1024,
        budget_tokens_per_day=100_000,
    ),
    "consensus_mediator": LLMConfig(
        model="gpt-4o",
        temperature=0.2,
        max_tokens=2048,
        budget_tokens_per_day=50_000,
    ),
}
