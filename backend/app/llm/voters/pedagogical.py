"""PedagogicalVoter — LLM-powered cognitive readiness assessment."""

from __future__ import annotations

import logging

from app.core.consensus import ConsensusVote, VoteContext, VoteDecision
from app.llm.prompts.pedagogical import PEDAGOGICAL_SYSTEM_PROMPT
from app.llm.voters.base import HybridVoter

logger = logging.getLogger(__name__)


class PedagogicalVoter(HybridVoter):
    """Evaluates if a student is cognitively ready for a module.

    LLM mode: analyzes Bloom level, cognitive stage, mastery profile.
    Heuristic fallback: score-based threshold (same as MasteryVoter).
    """

    voter_name = "pedagogical"

    def _build_messages(self, ctx: VoteContext) -> list[dict]:
        mastery = ctx.evidence.get("mastered_concepts", [])
        weak = ctx.evidence.get("weak_concepts", [])
        cognitive_stage = ctx.evidence.get("cognitive_stage", "unknown")
        learning_profile = ctx.evidence.get("learning_profile", "standard")

        user_prompt = (
            f"Student ID: {ctx.student_id}\n"
            f"Score: {ctx.score:.2f}\n"
            f"Cognitive stage: {cognitive_stage}\n"
            f"Mastered concepts ({len(mastery)}): {', '.join(mastery[:5]) if mastery else 'none'}\n"
            f"Weak concepts ({len(weak)}): {', '.join(weak[:5]) if weak else 'none'}\n"
            f"Learning profile: {learning_profile}\n"
            f"Module ID: {ctx.module_id}\n"
            f"Module title: {getattr(ctx.module, 'title', 'unknown')}\n"
            f"Module type: {getattr(ctx.module, 'module_type', 'unknown')}\n"
            f"Bloom level: {getattr(ctx.module, 'bloom_level', 'unknown')}\n"
            f"Difficulty: {getattr(ctx.module, 'difficulty', 0.5)}\n"
        )
        return [
            {"role": "system", "content": PEDAGOGICAL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

    def _should_use_heuristic(self, ctx: VoteContext) -> bool:
        return False

    def _heuristic_vote(self, ctx: VoteContext) -> ConsensusVote:
        """Score-based fallback matching MasteryVoter logic."""
        if ctx.score >= 0.6:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.APPROVE,
                confidence=min(1.0, ctx.score + 0.1),
                reason=f"Score {ctx.score:.2f} >= 0.6",
                evidence={"heuristic": True, "reasoning": "score_threshold"},
            )
        if ctx.score < 0.4:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.REJECT,
                confidence=min(1.0, (1.0 - ctx.score) + 0.1),
                reason=f"Score {ctx.score:.2f} < 0.4",
                evidence={"heuristic": True, "reasoning": "score_threshold"},
            )
        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.5,
            reason=f"Score {ctx.score:.2f} in borderline range [0.4, 0.6)",
            evidence={"heuristic": True, "reasoning": "score_borderline"},
        )
