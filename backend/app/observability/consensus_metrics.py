"""
Consensus Metrics — in-process counters for consensus observability.

Collects:
    - Total consensus runs
    - Approval/rejection/abstention frequency
    - Voter disagreement (non-unanimous decisions)
    - Per-voter latency (min, max, avg, count)
    - Rejection reasons
    - Abstention reasons
    - Rollback frequency
    - Retry frequency

Thread-safe via threading.Lock.
"""

from __future__ import annotations

import logging
import threading
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import ConsensusResult, ConsensusVote, VoteDecision

logger = logging.getLogger(__name__)


@dataclass
class VoterStats:
    votes: int = 0
    approvals: int = 0
    rejections: int = 0
    abstentions: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    last_reason: str = ""

    @property
    def avg_latency_ms(self) -> float:
        if self.votes == 0:
            return 0.0
        return self.total_latency_ms / self.votes

    def record(self, decision: VoteDecision, latency_ms: float, reason: str) -> None:
        self.votes += 1
        self.total_latency_ms += latency_ms
        self.min_latency_ms = min(self.min_latency_ms, latency_ms)
        self.max_latency_ms = max(self.max_latency_ms, latency_ms)
        self.last_reason = reason
        if decision == VoteDecision.APPROVE:
            self.approvals += 1
        elif decision == VoteDecision.REJECT:
            self.rejections += 1
        else:
            self.abstentions += 1


class ConsensusMetrics:
    """Thread-safe collector for consensus observability metrics."""

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.total_runs: int = 0
            self.approvals: int = 0
            self.rejections: int = 0
            self.abstentions: int = 0
            self.disagreements: int = 0
            self.errors: int = 0
            self.total_latency_ms: float = 0.0
            self.min_latency_ms: float = float("inf")
            self.max_latency_ms: float = 0.0
            self.voter_stats: dict[str, VoterStats] = defaultdict(VoterStats)
            self.rejection_reasons: Counter = Counter()
            self.abstention_reasons: Counter = Counter()
            self.modules_completed: int = 0
            self.modules_locked: int = 0
            self.rollbacks: int = 0

    def record_run(self, result: ConsensusResult, duration_ms: float) -> None:
        with self._lock:
            self.total_runs += 1
            self.total_latency_ms += duration_ms
            self.min_latency_ms = min(self.min_latency_ms, duration_ms)
            self.max_latency_ms = max(self.max_latency_ms, duration_ms)

            if result.decision == VoteDecision.APPROVE:
                self.approvals += 1
            elif result.decision == VoteDecision.REJECT:
                self.rejections += 1
            else:
                self.abstentions += 1

            if not result.unanimous:
                self.disagreements += 1

            for vote in result.votes:
                self._record_vote(vote, 0.0)

    def record_vote(self, vote: ConsensusVote, latency_ms: float) -> None:
        with self._lock:
            self._record_vote(vote, latency_ms)

    def _record_vote(self, vote: ConsensusVote, latency_ms: float) -> None:
        self.voter_stats[vote.voter_name].record(vote.decision, latency_ms, vote.reason)
        if vote.decision == VoteDecision.REJECT:
            self.rejection_reasons[vote.reason[:100]] += 1
        elif vote.decision == VoteDecision.ABSTAIN and vote.reason:
            self.abstention_reasons[vote.reason[:100]] += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors += 1

    def record_rollback(self) -> None:
        with self._lock:
            self.rollbacks += 1

    def record_module_completed(self) -> None:
        with self._lock:
            self.modules_completed += 1

    def record_module_locked(self) -> None:
        with self._lock:
            self.modules_locked += 1

    def get_snapshot(self) -> dict[str, Any]:
        with self._lock:
            total = self.total_runs or 1
            return {
                "total_runs": self.total_runs,
                "approvals": self.approvals,
                "rejections": self.rejections,
                "abstentions": self.abstentions,
                "approval_rate": round(self.approvals / total, 4),
                "rejection_rate": round(self.rejections / total, 4),
                "disagreements": self.disagreements,
                "disagreement_rate": round(self.disagreements / total, 4),
                "errors": self.errors,
                "avg_latency_ms": round(self.total_latency_ms / total, 2),
                "min_latency_ms": round(self.min_latency_ms, 2) if self.min_latency_ms != float("inf") else 0.0,
                "max_latency_ms": round(self.max_latency_ms, 2),
                "modules_completed": self.modules_completed,
                "modules_locked": self.modules_locked,
                "rollbacks": self.rollbacks,
                "voter_stats": {
                    name: {
                        "votes": s.votes,
                        "approvals": s.approvals,
                        "rejections": s.rejections,
                        "abstentions": s.abstentions,
                        "avg_latency_ms": round(s.avg_latency_ms, 2),
                        "min_latency_ms": round(s.min_latency_ms, 2) if s.min_latency_ms != float("inf") else 0.0,
                        "max_latency_ms": round(s.max_latency_ms, 2),
                    }
                    for name, s in sorted(self.voter_stats.items())
                },
                "top_rejection_reasons": self.rejection_reasons.most_common(10),
                "top_abstention_reasons": self.abstention_reasons.most_common(10),
            }


# Module-level singleton for automatic metric collection
metrics: ConsensusMetrics = ConsensusMetrics()
