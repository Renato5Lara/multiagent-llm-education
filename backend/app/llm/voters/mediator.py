"""MediatorVoter — LLM-powered mediator for final escalation in deliberation."""

from __future__ import annotations

import logging

from app.core.consensus import ConsensusVote, VoteContext, VoteDecision
from app.llm.prompts.deliberation import MEDIATION_SYSTEM_PROMPT
from app.llm.voters.base import HybridVoter

logger = logging.getLogger(__name__)


class MediatorVoter(HybridVoter):
    """Synthesizes a final decision when LLM voters cannot reach consensus.

    Activated only after max_rounds of deliberation without convergence.
    Receives the full vote history and agent agendas.
    """

    voter_name = "mediator"

    def _build_messages(self, ctx: VoteContext) -> list[dict]:
        vote_history = ctx.evidence.get("vote_history", "No history available")
        agent_agendas = ctx.evidence.get("agent_agendas", "No agendas available")
        student_data = (
            f"Student ID: {ctx.student_id}\n"
            f"Score: {ctx.score:.2f}\n"
            f"Module ID: {ctx.module_id}\n"
        )
        module_data = (
            f"Title: {getattr(ctx.module, 'title', 'unknown')}\n"
            f"Type: {getattr(ctx.module, 'module_type', 'unknown')}\n"
            f"Bloom level: {getattr(ctx.module, 'bloom_level', 'unknown')}\n"
        )

        prompt = (
            f"## Vote History\n{vote_history}\n\n"
            f"## Agent Agendas\n{agent_agendas}\n\n"
            f"## Student Data\n{student_data}\n"
            f"## Module Data\n{module_data}\n"
        )

        return [
            {"role": "system", "content": MEDIATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

    def _heuristic_vote(self, ctx: VoteContext) -> ConsensusVote:
        """Fallback: majority vote from previous rounds."""
        return ConsensusVote(
            voter_name=self.voter_name,
            decision=VoteDecision.ABSTAIN,
            confidence=0.3,
            reason="Mediation heuristic fallback: insufficient data",
            evidence={"heuristic": True, "reasoning": "mediation_fallback"},
        )
