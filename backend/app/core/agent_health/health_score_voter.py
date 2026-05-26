from __future__ import annotations

import time
from typing import Any

from app.core.agent_health.models import AgentHealthProfile, DegradationLevel
from app.core.consensus import BaseVoter, ConsensusVote, VoteDecision, VoteContext


DEGRADATION_WEIGHTS = {
    DegradationLevel.NONE: 1.0,
    DegradationLevel.MILD: 0.9,
    DegradationLevel.MODERATE: 0.7,
    DegradationLevel.SEVERE: 0.4,
    DegradationLevel.CRITICAL: 0.0,
}


class HealthScoreVoter(BaseVoter):
    def __init__(
        self,
        voter: BaseVoter,
        get_profile: Any,
    ) -> None:
        self._voter = voter
        self._get_profile = get_profile
        self._health_score: float = 1.0
        self._last_update: float = 0.0
        self._cache_ttl: float = 5.0

    @property
    def voter_name(self) -> str:
        return self._voter.voter_name

    @property
    def inner_voter(self) -> BaseVoter:
        return self._voter

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        now = time.time()
        if now - self._last_update > self._cache_ttl:
            profile = self._get_profile(self._voter.voter_name)
            self._health_score = profile.health_score if profile else 1.0
            self._last_update = now

        if self._health_score < 0.2:
            return ConsensusVote(
                voter_name=self.voter_name,
                decision=VoteDecision.ABSTAIN,
                confidence=0.0,
                reason=f"Agent health critical: score={self._health_score:.2f}",
                evidence={
                    "health_score": self._health_score,
                    "action": "quarantined",
                },
            )

        vote = self._voter.vote(ctx)

        if self._health_score < 0.8:
            level = DegradationLevel.from_health_score(self._health_score)
            weight = DEGRADATION_WEIGHTS.get(level, 1.0)
            adjusted_confidence = vote.confidence * weight
            vote = ConsensusVote(
                voter_name=vote.voter_name,
                decision=vote.decision,
                confidence=adjusted_confidence,
                reason=(
                    f"{vote.reason} [health-adjusted: weight={weight:.2f}, "
                    f"score={self._health_score:.2f}, level={level.label}]"
                ),
                evidence={
                    **vote.evidence,
                    "health_score": self._health_score,
                    "health_weight": weight,
                    "degradation_level": level.label,
                },
            )

        return vote
