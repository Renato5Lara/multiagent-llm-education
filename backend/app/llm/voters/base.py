"""HybridVoter — base class for LLM-powered voters with heuristic fallback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.core.consensus import BaseVoter, ConsensusVote, VoteContext, VoteDecision
from app.llm.service import LLMResponse, LLMService
from app.llm.cost_tracker import TokenBudgetTracker
from app.llm.confidence import ConfidenceCalibrator
from app.llm.grounding import HallucinationGuard
from app.llm.response_parser import LLMResponseParser, ParseError, ParsedVote

logger = logging.getLogger(__name__)


class HybridVoter(BaseVoter):
    """Base class for LLM-powered voters with automatic heuristic fallback.

    Pipeline:
        1. _should_use_heuristic? → heuristic fallback
        2. _build_messages → LLM call
        3. Parse response → ParsedVote
        4. HallucinationGuard.verify → reject if severe
        5. ConfidenceCalibrator.calibrate → calibrated confidence
        6. Return ConsensusVote with full evidence

    On any error/exception → heuristic fallback.

    Deliberation support:
        If ctx.evidence["deliberation_context"] is set (by SwarmDeliberationOrchestrator),
        it is automatically appended to the user message after _build_messages.
        Subclasses should NOT handle deliberation context in _build_messages.
    """

    def __init__(
        self,
        llm_service: LLMService,
        budget_tracker: TokenBudgetTracker,
        calibrator: ConfidenceCalibrator,
        guard: HallucinationGuard,
        parser: LLMResponseParser | None = None,
        *,
        min_llm_confidence: float = 0.6,
    ):
        self._llm = llm_service
        self._budgets = budget_tracker
        self._calibrator = calibrator
        self._guard = guard
        self._parser = parser or LLMResponseParser()
        self._min_llm_confidence = min_llm_confidence

    def _build_messages(self, ctx: VoteContext) -> list[dict]:
        """Build [system, user] messages for the LLM."""
        raise NotImplementedError

    def _heuristic_vote(self, ctx: VoteContext) -> ConsensusVote:
        """Fallback vote when LLM is unavailable or fails."""
        raise NotImplementedError

    def _should_use_heuristic(self, ctx: VoteContext) -> bool:
        """Override to trigger fallback based on context (e.g., low score)."""
        return False

    # ── Public entry point ────────────────────────────────────

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        if self._should_use_heuristic(ctx):
            return self._heuristic_vote(ctx)
        try:
            return asyncio.run(self._async_vote(ctx))
        except Exception as e:
            logger.warning("LLM vote failed for %s: %s", self.voter_name, e)
            return self._heuristic_vote(ctx)

    # ── Async pipeline ────────────────────────────────────────

    async def _async_vote(self, ctx: VoteContext) -> ConsensusVote:
        messages = self._build_messages(ctx)

        # Inject deliberation context from orchestrator (Phase 2)
        delib = ctx.evidence.get("deliberation_context", "")
        if delib:
            for msg in messages:
                if msg["role"] == "user":
                    msg["content"] += self._format_deliberation_context(delib)
                    break

        response = await self._llm.generate(
            messages=messages,
            voter_name=self.voter_name,
        )

        if not response.success or not response.content:
            return self._heuristic_vote(ctx)

        try:
            parsed = self._parser.parse_vote(response.content)
        except ParseError:
            logger.info("Unparseable LLM response for %s", self.voter_name)
            return self._heuristic_vote(ctx)

        hallucination = await self._guard.verify(
            voter_name=self.voter_name,
            decision=parsed.decision,
            confidence=parsed.confidence,
            reasoning=parsed.reasoning,
            evidence=parsed.evidence,
            score=ctx.score,
            bloom_level=getattr(ctx.module, "bloom_level", "unknown"),
        )

        if hallucination.is_severe:
            logger.info(
                "Hallucination detected for %s (score=%.2f)",
                self.voter_name, hallucination.hallucination_score,
            )
            self._guard.record_outcome(self.voter_name, parsed.decision, parsed.confidence, False)
            return self._heuristic_vote(ctx)

        calibrated_conf = self._calibrator.calibrate(parsed.confidence, self.voter_name)
        self._calibrator.record_outcome(self.voter_name, parsed.confidence, True)
        self._guard.record_outcome(self.voter_name, parsed.decision, calibrated_conf, True)

        if calibrated_conf < self._min_llm_confidence:
            logger.info(
                "Calibrated confidence %.2f < min %.2f for %s",
                calibrated_conf, self._min_llm_confidence, self.voter_name,
            )
            return self._heuristic_vote(ctx)

        return ConsensusVote(
            voter_name=self.voter_name,
            decision=parsed.decision,
            confidence=calibrated_conf,
            reason=parsed.reason_summary,
            evidence={
                **parsed.evidence,
                "hallucination_score": hallucination.hallucination_score,
                "confidence_raw": parsed.confidence,
                "confidence_calibrated": calibrated_conf,
                "llm_model": response.model,
                "tokens_used": response.tokens_total,
            },
        )

    # ── Deliberation helpers ──────────────────────────────────

    @staticmethod
    def _format_deliberation_context(delib: str) -> str:
        return (
            "\n\n## Razonamientos de Otros Agentes (Deliberación)\n"
            "Los siguientes son los análisis de otros agentes en rondas anteriores. "
            "Evalúa sus argumentos y decide si mantienes tu posición o la revisas.\n\n"
            f"{delib}"
        )
