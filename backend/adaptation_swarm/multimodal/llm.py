"""Cliente LLM de los generadores (AG2/AG4): reutiliza `app.llm.service.LLMService` (reintentos,
control de presupuesto, proveedor OpenAI). temperature=0 para reproducibilidad razonable."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings
from app.llm.config import LLMConfig
from app.llm.service import LLMService

from adaptation_swarm.schemas.errors import GenerationError

DEFAULT_MODEL = "gpt-4o-mini"


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    tokens_total: int
    duration_ms: float


class LLMClient:
    def __init__(self, model: str = DEFAULT_MODEL, *, max_tokens: int = 900, service: LLMService | None = None):
        if service is None and not settings.has_openai:
            raise GenerationError("OPENAI_API_KEY no configurada: la generación real de AG2/AG4 la requiere")
        self.model = model
        self._svc = service or LLMService(default_config=LLMConfig(
            model=model, api_key=settings.OPENAI_API_KEY or "", temperature=0.0, max_tokens=max_tokens,
            timeout_seconds=90.0, max_retries=2, budget_tokens_per_day=5_000_000,
        ))

    async def complete(self, system: str, user: str) -> LLMResult:
        resp = await self._svc.generate(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            voter_name="adaptation_swarm", response_format="text",
        )
        if not resp.success or not resp.content.strip():
            raise GenerationError(f"LLM falló: {resp.error}")
        return LLMResult(text=resp.content, model=resp.model, tokens_total=resp.tokens_total,
                         duration_ms=resp.duration_ms)
