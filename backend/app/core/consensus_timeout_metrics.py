"""
ConsensusTimeoutMetrics — Thread-safe metrics collection for consensus timeout operations.

Tracks counters for:
    - Timeout events (per reason)
    - Degraded mode activations
    - Quorum fallback decisions
    - Hung agent detections
    - Cancellation events (per reason)
    - Adaptive timeout value snapshots
    - Cascading delay events
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from .consensus_cancellation import CancellationReason


@dataclass
class TimeoutMetricSnapshot:
    """Immutable snapshot of all metrics at a point in time."""

    timeouts_by_reason: dict[str, int] = field(default_factory=dict)
    degraded_count: int = 0
    quorum_fallback_count: int = 0
    hung_agent_count: int = 0
    cancellation_count: int = 0
    cascading_delay_count: int = 0
    total_consensus_runs: int = 0
    total_voters: int = 0
    timed_out_voters: int = 0
    skipped_voters: int = 0
    adaptive_multipliers: list[float] = field(default_factory=list)
    min_voter_duration_ms: list[float] = field(default_factory=list)
    avg_voter_duration_ms: list[float] = field(default_factory=list)
    max_voter_duration_ms: list[float] = field(default_factory=list)
    p95_voter_duration_ms: list[float] = field(default_factory=list)
    hung_agents: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_timeouts(self) -> int:
        return sum(self.timeouts_by_reason.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "timeouts_by_reason": dict(self.timeouts_by_reason),
            "degraded_count": self.degraded_count,
            "quorum_fallback_count": self.quorum_fallback_count,
            "hung_agent_count": self.hung_agent_count,
            "cancellation_count": self.cancellation_count,
            "cascading_delay_count": self.cascading_delay_count,
            "total_consensus_runs": self.total_consensus_runs,
            "total_voters": self.total_voters,
            "timed_out_voters": self.timed_out_voters,
            "skipped_voters": self.skipped_voters,
            "adaptive_multiplier_avg": (
                sum(self.adaptive_multipliers) / len(self.adaptive_multipliers)
                if self.adaptive_multipliers
                else 0.0
            ),
            "p95_voter_duration_ms_avg": (
                sum(self.p95_voter_duration_ms) / len(self.p95_voter_duration_ms)
                if self.p95_voter_duration_ms
                else 0.0
            ),
            "hung_agent_details": self.hung_agents,
        }


class ConsensusTimeoutMetrics:
    """Thread-safe collector for consensus timeout metrics.

    Usage:
        metrics = ConsensusTimeoutMetrics()
        metrics.record_timeout("voter_timeout", "mastery")
        metrics.record_degraded()
        snapshot = metrics.snapshot()
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Counters
        self._timeouts_by_reason: dict[str, int] = defaultdict(int)
        self._degraded_count: int = 0
        self._quorum_fallback_count: int = 0
        self._hung_agent_count: int = 0
        self._cancellation_count: int = 0
        self._cascading_delay_count: int = 0
        self._total_consensus_runs: int = 0
        self._total_voters: int = 0
        self._timed_out_voters: int = 0
        self._skipped_voters: int = 0
        # Sampled values
        self._adaptive_multipliers: list[float] = []
        self._min_voter_duration_ms: list[float] = []
        self._avg_voter_duration_ms: list[float] = []
        self._max_voter_duration_ms: list[float] = []
        self._p95_voter_duration_ms: list[float] = []
        self._hung_agents: list[dict[str, Any]] = []
        # Max samples to keep per list
        self._max_samples: int = 1000

    # ── Recording methods ──────────────────────────────────────────

    def record_timeout(
        self,
        reason: str | CancellationReason,
        voter_name: str | None = None,
    ) -> None:
        if isinstance(reason, CancellationReason):
            reason = reason.value
        with self._lock:
            self._timeouts_by_reason[reason] += 1
            if voter_name:
                logger.debug(
                    "Timeout recorded: reason=%s voter=%s", reason, voter_name
                )

    def record_degraded(self) -> None:
        with self._lock:
            self._degraded_count += 1

    def record_quorum_fallback(self) -> None:
        with self._lock:
            self._quorum_fallback_count += 1

    def record_hung_agent(
        self,
        agent_name: str,
        strikes: int,
        action: str = "skipped",
        details: dict[str, Any] | None = None,
    ) -> None:
        entry = {
            "agent_name": agent_name,
            "strikes": strikes,
            "action": action,
            "timestamp": time.time(),
        }
        if details:
            entry["details"] = details
        with self._lock:
            self._hung_agent_count += 1
            if len(self._hung_agents) < self._max_samples:
                self._hung_agents.append(entry)

    def record_cancellation(
        self,
        reason: str | CancellationReason,
        source: str | None = None,
    ) -> None:
        if isinstance(reason, CancellationReason):
            reason = reason.value
        with self._lock:
            self._cancellation_count += 1

    def record_cascading_delay(self) -> None:
        with self._lock:
            self._cascading_delay_count += 1

    def record_consensus_run(
        self,
        total_voters: int,
        timed_out: int,
        skipped: int,
        adaptive_multiplier: float | None = None,
        duration_stats: dict[str, float] | None = None,
    ) -> None:
        with self._lock:
            self._total_consensus_runs += 1
            self._total_voters += total_voters
            self._timed_out_voters += timed_out
            self._skipped_voters += skipped
            if adaptive_multiplier is not None and len(self._adaptive_multipliers) < self._max_samples:
                self._adaptive_multipliers.append(adaptive_multiplier)
            if duration_stats:
                if "min_ms" in duration_stats and len(self._min_voter_duration_ms) < self._max_samples:
                    self._min_voter_duration_ms.append(duration_stats["min_ms"])
                if "avg_ms" in duration_stats and len(self._avg_voter_duration_ms) < self._max_samples:
                    self._avg_voter_duration_ms.append(duration_stats["avg_ms"])
                if "max_ms" in duration_stats and len(self._max_voter_duration_ms) < self._max_samples:
                    self._max_voter_duration_ms.append(duration_stats["max_ms"])
                if "p95_ms" in duration_stats and len(self._p95_voter_duration_ms) < self._max_samples:
                    self._p95_voter_duration_ms.append(duration_stats["p95_ms"])

    # ── Inspection ─────────────────────────────────────────────────

    def snapshot(self) -> TimeoutMetricSnapshot:
        """Capture a point-in-time snapshot of all metrics."""
        with self._lock:
            return TimeoutMetricSnapshot(
                timeouts_by_reason=dict(self._timeouts_by_reason),
                degraded_count=self._degraded_count,
                quorum_fallback_count=self._quorum_fallback_count,
                hung_agent_count=self._hung_agent_count,
                cancellation_count=self._cancellation_count,
                cascading_delay_count=self._cascading_delay_count,
                total_consensus_runs=self._total_consensus_runs,
                total_voters=self._total_voters,
                timed_out_voters=self._timed_out_voters,
                skipped_voters=self._skipped_voters,
                adaptive_multipliers=list(self._adaptive_multipliers),
                min_voter_duration_ms=list(self._min_voter_duration_ms),
                avg_voter_duration_ms=list(self._avg_voter_duration_ms),
                max_voter_duration_ms=list(self._max_voter_duration_ms),
                p95_voter_duration_ms=list(self._p95_voter_duration_ms),
                hung_agents=list(self._hung_agents),
            )

    @property
    def total_timeouts(self) -> int:
        with self._lock:
            return sum(self._timeouts_by_reason.values())

    def reset(self) -> None:
        """Reset all counters and samples.  Useful for testing."""
        with self._lock:
            self._timeouts_by_reason.clear()
            self._degraded_count = 0
            self._quorum_fallback_count = 0
            self._hung_agent_count = 0
            self._cancellation_count = 0
            self._cascading_delay_count = 0
            self._total_consensus_runs = 0
            self._total_voters = 0
            self._timed_out_voters = 0
            self._skipped_voters = 0
            self._adaptive_multipliers.clear()
            self._min_voter_duration_ms.clear()
            self._avg_voter_duration_ms.clear()
            self._max_voter_duration_ms.clear()
            self._p95_voter_duration_ms.clear()
            self._hung_agents.clear()


import logging

logger = logging.getLogger(__name__)
