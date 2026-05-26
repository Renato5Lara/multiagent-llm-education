"""
Trust System — Dynamic trust scoring for consensus voters.

Each voter accumulates a trust score based on historical accuracy,
consistency, latency, and confidence calibration.

Trust formula:
    trust = base * accuracy_factor * consistency_factor * latency_factor * decay

    - accuracy_factor: 0.5 + 0.5 * historical_accuracy
    - consistency_factor: 1.0 - disagreement_rate * 0.5
    - latency_factor: 1.0 - latency_percentile * 0.2
    - decay: 1.0 - decay_rate * hours_since_last_vote

Thread-safe for concurrent consensus runs.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.consensus import VoteDecision
from app.observability.tracing import TraceContext

logger = logging.getLogger(__name__)


@dataclass
class VoterTrustRecord:
    """Historical performance record for a single voter."""

    voter_name: str
    total_votes: int = 0
    correct_votes: int = 0
    incorrect_votes: int = 0
    abstentions: int = 0
    errors: int = 0
    total_confidence: float = 0.0
    total_latency_ms: float = 0.0
    trust_score: float = 1.0
    last_vote_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def accuracy(self) -> float:
        """Fraction of non-abstain votes that matched final consensus."""
        decisions = self.total_votes - self.abstentions
        if decisions == 0:
            return 0.0
        return self.correct_votes / decisions

    @property
    def disagreement_rate(self) -> float:
        """Fraction of non-abstain votes that disagreed with final consensus."""
        decisions = self.total_votes - self.abstentions
        if decisions == 0:
            return 0.0
        return self.incorrect_votes / decisions

    @property
    def avg_confidence(self) -> float:
        if self.total_votes == 0:
            return 0.0
        return self.total_confidence / self.total_votes

    @property
    def avg_latency_ms(self) -> float:
        if self.total_votes == 0:
            return 0.0
        return self.total_latency_ms / self.total_votes

    @property
    def confidence_calibration(self) -> float:
        """Difference between avg confidence and accuracy.
        Positive = overconfident, Negative = underconfident, 0 = perfect.
        """
        return self.avg_confidence - self.accuracy

    def to_dict(self) -> dict[str, Any]:
        return {
            "voter_name": self.voter_name,
            "total_votes": self.total_votes,
            "correct_votes": self.correct_votes,
            "incorrect_votes": self.incorrect_votes,
            "abstentions": self.abstentions,
            "errors": self.errors,
            "accuracy": round(self.accuracy, 4),
            "disagreement_rate": round(self.disagreement_rate, 4),
            "avg_confidence": round(self.avg_confidence, 4),
            "confidence_calibration": round(self.confidence_calibration, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "trust_score": round(self.trust_score, 4),
            "last_vote_at": self.last_vote_at.isoformat() if self.last_vote_at else None,
        }


class TrustSystem:
    """Thread-safe trust scoring for consensus voters.

    Maintains historical performance records and computes dynamic
    trust scores based on accuracy, consistency, latency, and decay.
    """

    def __init__(self, decay_rate: float = 0.005, min_trust: float = 0.1):
        if not 0.0 <= decay_rate <= 1.0:
            raise ValueError(f"decay_rate must be in [0,1], got {decay_rate}")
        if not 0.0 <= min_trust <= 1.0:
            raise ValueError(f"min_trust must be in [0,1], got {min_trust}")
        self._decay_rate = decay_rate
        self._min_trust = min_trust
        self._records: dict[str, VoterTrustRecord] = {}
        self._lock = threading.Lock()

    def _get_or_create(self, voter_name: str) -> VoterTrustRecord:
        """Internal: assumes lock is held."""
        if voter_name not in self._records:
            self._records[voter_name] = VoterTrustRecord(voter_name=voter_name)
        return self._records[voter_name]

    def record_vote_outcome(
        self,
        voter_name: str,
        decision: VoteDecision,
        confidence: float,
        latency_ms: float,
        final_decision: VoteDecision,
    ) -> None:
        """Record a vote outcome and update trust score.

        Args:
            voter_name: Which voter cast the vote.
            decision: What the voter decided.
            confidence: The voter's stated confidence.
            latency_ms: How long the voter took.
            final_decision: The aggregated final decision.
        """
        with self._lock:
            record = self._get_or_create(voter_name)
            record.total_votes += 1
            record.total_confidence += confidence
            record.total_latency_ms += latency_ms
            record.last_vote_at = datetime.now(timezone.utc)

            if decision == VoteDecision.ABSTAIN:
                record.abstentions += 1
            elif decision == final_decision:
                record.correct_votes += 1
            else:
                record.incorrect_votes += 1

            self._recompute(voter_name)

    def record_error(self, voter_name: str) -> None:
        """Record that a voter raised an exception.

        Does not increment total_votes — the synthetic ABSTAIN vote
        is already counted by record_vote_outcome. This only tracks
        the error count for the error_factor in trust computation.
        """
        with self._lock:
            record = self._get_or_create(voter_name)
            record.errors += 1
            record.last_vote_at = datetime.now(timezone.utc)
            self._recompute(voter_name)

    def _recompute(self, voter_name: str) -> None:
        """Recompute trust score for a single voter."""
        record = self._records[voter_name]
        if record.total_votes == 0:
            record.trust_score = 1.0
            return

        # Accuracy factor: [0.5, 1.0]
        accuracy = record.accuracy
        accuracy_factor = 0.5 + 0.5 * accuracy

        # Consistency factor: [0.5, 1.0]
        disagreement = record.disagreement_rate
        consistency_factor = 1.0 - disagreement * 0.5

        # Latency factor: degrade if significantly slower than peers
        # (uses per-voter latency — no cross-voter comparison needed)
        latency = record.avg_latency_ms
        if latency > 100:
            latency_factor = max(0.8, 1.0 - (latency - 100) / 1000 * 0.2)
        else:
            latency_factor = 1.0

        # Error factor
        if record.total_votes > 0:
            error_rate = record.errors / record.total_votes
            error_factor = 1.0 - error_rate * 0.5
        else:
            error_factor = 1.0

        # Time-based decay: trust decays with inactivity
        if record.last_vote_at:
            hours_since = (
                datetime.now(timezone.utc) - record.last_vote_at
            ).total_seconds() / 3600
            decay = 1.0 - min(self._decay_rate * hours_since, 0.5)
        else:
            decay = 1.0

        # Composite trust
        trust = accuracy_factor * consistency_factor * latency_factor * error_factor * decay
        record.trust_score = max(trust, self._min_trust)

        logger.debug(
            "Trust[%s]: score=%.4f accuracy=%.3f disagreement=%.3f "
            "latency=%.1fms decay=%.3f",
            voter_name, record.trust_score, accuracy,
            disagreement, latency, decay,
        )

    def get_trust(self, voter_name: str) -> float:
        with self._lock:
            return self._get_or_create(voter_name).trust_score

    def get_trust_scores(self, voter_names: list[str]) -> dict[str, float]:
        with self._lock:
            return {name: self._get_or_create(name).trust_score for name in voter_names}

    def get_record(self, voter_name: str) -> VoterTrustRecord | None:
        with self._lock:
            return self._records.get(voter_name)

    def get_all_records(self) -> list[VoterTrustRecord]:
        with self._lock:
            return list(self._records.values())

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                name: record.to_dict()
                for name, record in sorted(self._records.items())
            }

    def reset(self) -> None:
        with self._lock:
            self._records.clear()


# Module-level singleton
_trust_system: TrustSystem | None = None
_trust_lock = threading.Lock()


def get_trust_system() -> TrustSystem:
    global _trust_system
    if _trust_system is None:
        with _trust_lock:
            if _trust_system is None:
                _trust_system = TrustSystem()
    return _trust_system


def reset_trust_system() -> None:
    global _trust_system
    with _trust_lock:
        if _trust_system is not None:
            _trust_system.reset()
