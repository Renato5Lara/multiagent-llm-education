"""
Specialization Tracking — Detects which voters specialize in which contexts.

Each voter accumulates domain-specific accuracy. The system builds
a profile of which voters perform better on specific topics, bloom
levels, or course types.

Specialization affinity formula:
    affinity = domain_accuracy * confidence_weight

    - domain_accuracy: historical accuracy for a specific context
    - confidence_weight: weight based on number of votes in the domain

Used by AdaptiveWeighting to adjust voter weights per decision context.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import VoteContext

logger = logging.getLogger(__name__)


def context_key(ctx: VoteContext) -> str:
    """Build a context key for specialization tracking.

    Uses the module's bloom level as the primary dimension,
    falling back to 'unknown' if no module is available.
    """
    if ctx.module is not None:
        bloom = ctx.module.bloom_level or "unknown"
        return f"bloom:{bloom}"
    return "bloom:unknown"


@dataclass
class SpecializationProfile:
    """Per-voter specialization data.

    Tracks accuracy per domain (context key) and overall stats.
    """

    voter_name: str
    domain_correct: dict[str, int] = field(default_factory=dict)
    domain_total: dict[str, int] = field(default_factory=dict)
    total_votes: int = 0

    def record(self, context_key: str, correct: bool) -> None:
        """Record a vote outcome for a specific context domain."""
        self.total_votes += 1
        if context_key not in self.domain_total:
            self.domain_total[context_key] = 0
            self.domain_correct[context_key] = 0
        self.domain_total[context_key] += 1
        if correct:
            self.domain_correct[context_key] += 1

    def domain_accuracy(self, context_key: str) -> float:
        """Accuracy for a specific context domain."""
        total = self.domain_total.get(context_key, 0)
        if total == 0:
            return 0.0
        return self.domain_correct[context_key] / total

    def domain_confidence(self, context_key: str) -> float:
        """Confidence weight based on number of votes in domain.
        Ranges from 0 (no data) to 1 (many votes).
        """
        total = self.domain_total.get(context_key, 0)
        return min(total / 10.0, 1.0)  # 10 votes = full confidence

    def specialization_affinity(self, context_key: str) -> float:
        """Combined affinity score, symmetric around 0.5.

        Maps accuracy [0, 1] to affinity [0, 1] where:
        - acc=1.0 → affinity = 0.5 + 0.5*conf (max)
        - acc=0.5 → affinity = 0.5 (neutral)
        - acc=0.0 → affinity = 0.5 - 0.5*conf (min)

        Returns 0.5 (neutral) when no data is available.
        """
        acc = self.domain_accuracy(context_key)
        conf = self.domain_confidence(context_key)
        if self.domain_total.get(context_key, 0) == 0:
            return 0.5
        return max(0.0, min(1.0, 0.5 + 0.5 * (acc * 2 - 1) * conf))

    def to_dict(self) -> dict[str, Any]:
        return {
            "voter_name": self.voter_name,
            "total_votes": self.total_votes,
            "domains": {
                key: {
                    "accuracy": round(self.domain_accuracy(key), 4),
                    "votes": self.domain_total[key],
                }
                for key in sorted(self.domain_total.keys())
            },
        }


class SpecializationTracker:
    """Thread-safe specialization tracking for all voters.

    Tracks per-domain accuracy and computes specialization affinities
    for adaptive weighting.
    """

    def __init__(self):
        self._profiles: dict[str, SpecializationProfile] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, voter_name: str) -> SpecializationProfile:
        """Internal: assumes lock is held."""
        if voter_name not in self._profiles:
            self._profiles[voter_name] = SpecializationProfile(voter_name=voter_name)
        return self._profiles[voter_name]

    def record_vote(
        self,
        voter_name: str,
        context_key: str,
        agreed_with_consensus: bool,
    ) -> None:
        """Record whether a voter's decision agreed with the final consensus.

        Args:
            voter_name: Which voter cast the vote.
            context_key: The specialization context (e.g., 'bloom:3').
            agreed_with_consensus: True if the voter's decision matched
                the final aggregated decision (excluding abstentions).
        """
        with self._lock:
            profile = self._get_or_create(voter_name)
            profile.record(context_key, agreed_with_consensus)
            logger.debug(
                "Specialization[%s/%s]: agreed=%s accuracy=%.3f",
                voter_name, context_key, agreed_with_consensus,
                profile.domain_accuracy(context_key),
            )

    def get_affinity(self, voter_name: str, context_key: str) -> float:
        with self._lock:
            profile = self._profiles.get(voter_name)
            if not profile:
                return 0.5
            return profile.specialization_affinity(context_key)

    def get_affinities(
        self, voter_names: list[str], context_key: str,
    ) -> dict[str, float]:
        with self._lock:
            return {
                name: self.get_affinity(name, context_key)
                for name in voter_names
            }

    def get_profile(self, voter_name: str) -> SpecializationProfile | None:
        with self._lock:
            return self._profiles.get(voter_name)

    def get_all_profiles(self) -> list[SpecializationProfile]:
        with self._lock:
            return list(self._profiles.values())

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                name: profile.to_dict()
                for name, profile in sorted(self._profiles.items())
            }

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()


# Module-level singleton
_tracker: SpecializationTracker | None = None
_tracker_lock = threading.Lock()


def get_specialization_tracker() -> SpecializationTracker:
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                _tracker = SpecializationTracker()
    return _tracker


def reset_specialization_tracker() -> None:
    global _tracker
    with _tracker_lock:
        if _tracker is not None:
            _tracker.reset()
