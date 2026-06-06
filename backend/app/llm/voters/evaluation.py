"""EvaluationVoter — LLM-powered evaluation readiness assessment."""

from __future__ import annotations

import logging

from app.core.consensus import ConsensusVote, VoteContext, VoteDecision
from app.llm.prompts.evaluation import EVALUATION_SYSTEM_PROMPT
from app.llm.voters.base import HybridVoter

logger = logging.getLogger(__name__)


class EvaluationVoter(HybridVoter):
    """Determines if a student is ready for formal evaluation on a module.

    LLM mode: analyzes mastery scores, practice sufficiency, timing.
    Heuristic fallback: score-threshold based.
    """

    voter_name = "evaluation"

    def _build_messages(self, ctx: VoteContext) -> list[dict]:
        mastery_scores = ctx.evidence.get("mastery_scores", {})
        total_exercises = ctx.evidence.get("total_exercises", 0)
        concepts_covered = ctx.evidence.get("concepts_covered", [])
        previous_attempts = ctx.evidence.get("previous_attempts", 0)
        best_score = ctx.evidence.get("best_score", 0.0)
        time_since_last = ctx.evidence.get("time_since_last_attempt", "unknown")

        mastery_str = ", ".join(
            f"{k}={v:.2f}" for k, v in list(mastery_scores.items())[:5]
        )

        user_prompt = (
            f"Student ID: {ctx.student_id}\n"
            f"Current score: {ctx.score:.2f}\n"
            f"Mastery scores: {mastery_str or 'none'}\n"
            f"Total exercises completed: {total_exercises}\n"
            f"Concepts covered: {', '.join(concepts_covered[:5]) if concepts_covered else 'none'}\n"
            f"Previous evaluation attempts: {previous_attempts}\n"
            f"Best score: {best_score:.2f}\n"
            f"Time since last attempt: {time_since_last}\n"
            f"Module ID: {ctx.module_id}\n"
            f"Module title: {getattr(ctx.module, 'title', 'unknown')}\n"
            f"Module type: {getattr(ctx.module, 'module_type', 'unknown')}\n"
            f"Bloom level: {getattr(ctx.module, 'bloom_level', 'unknown')}\n"
        )
        return [
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _heuristic_vote(self, ctx: VoteContext) -> ConsensusVote:
        """Score and exercise-based fallback."""
        if ctx.score >= 0.7 and ctx.evidence.get("total_exercises", 0) >= 3:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.APPROVE,
                confidence=min(1.0, ctx.score + 0.15),
                reason=f"Score {ctx.score:.2f} >= 0.7 with sufficient practice",
                evidence={"heuristic": True, "reasoning": "score_and_practice_threshold"},
            )
        if ctx.score < 0.4:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.REJECT,
                confidence=min(1.0, (1.0 - ctx.score) + 0.1),
                reason=f"Score {ctx.score:.2f} < 0.4",
                evidence={"heuristic": True, "reasoning": "score_too_low"},
            )
        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.5,
            reason=f"Insufficient evidence (score={ctx.score:.2f}, exercises={ctx.evidence.get('total_exercises', 0)})",
            evidence={"heuristic": True, "reasoning": "insufficient_evidence"},
        )
