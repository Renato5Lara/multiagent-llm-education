"""
SwarmMetricsCollector — Async-safe, low-overhead metrics aggregation.

Provides per-scope counters, histograms, and rate calculations used by
all detectors and the health report.
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import RLock
from typing import Any

from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent


class SwarmMetricsCollector:
    """Thread-safe metrics collector with scoped counters."""

    def __init__(self) -> None:
        self._lock = RLock()

        self._event_counts: dict[str, int] = defaultdict(int)
        self._event_type_counts: dict[str, int] = defaultdict(int)
        self._scope_event_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._scope_error_counts: dict[str, int] = defaultdict(int)

        self._durations: dict[str, list[float]] = defaultdict(list)
        self._max_duration_samples = 100

        self._event_timestamps: list[float] = []
        self._event_types: list[str] = []  # parallel to _event_timestamps
        self._max_timestamps = 1000

        self._vote_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    def record_event(self, event: DiagnosticEvent) -> None:
        with self._lock:
            now = time.time()
            self._event_counts["total"] += 1
            self._event_type_counts[event.event_type] += 1
            self._scope_event_counts[event.scope][event.event_type] += 1

            if event.error:
                self._scope_error_counts[event.scope] += 1

            if event.duration_ms is not None:
                bucket = event.event_type.split(":")[0]  # "vote", "consensus", etc.
                vals = self._durations[bucket]
                vals.append(event.duration_ms)
                if len(vals) > self._max_duration_samples:
                    self._durations[bucket] = vals[-self._max_duration_samples:]

            self._event_timestamps.append(now)
            self._event_types.append(event.event_type)
            if len(self._event_timestamps) > self._max_timestamps:
                self._event_timestamps = self._event_timestamps[-self._max_timestamps:]
                self._event_types = self._event_types[-self._max_timestamps:]

            if event.event_type.startswith("vote:"):
                voter = event.source
                decision = event.payload.get("decision", "unknown")
                self._vote_counts[voter][decision] += 1

    # ── Queries ──────────────────────────────────────────────────

    def get_event_rate(self, window_seconds: float = 60.0) -> float:
        with self._lock:
            if not self._event_timestamps:
                return 0.0
            cutoff = time.time() - window_seconds
            recent = [t for t in self._event_timestamps if t >= cutoff]
            return len(recent) / max(window_seconds, 1.0)

    def get_event_type_rate(self, event_type: str, window_seconds: float = 60.0) -> float:
        with self._lock:
            cutoff = time.time() - window_seconds
            recent = [
                ts for ts, etype in zip(
                    self._event_timestamps, self._event_types
                ) if ts >= cutoff and etype == event_type
            ]
            return len(recent) / max(window_seconds, 1.0)

    def get_scope_event_count(self, scope: str, event_type: str | None = None) -> int:
        with self._lock:
            if event_type:
                return self._scope_event_counts[scope].get(event_type, 0)
            return sum(self._scope_event_counts[scope].values())

    def get_scope_error_count(self, scope: str) -> int:
        with self._lock:
            return self._scope_error_counts.get(scope, 0)

    def get_total_events(self) -> int:
        with self._lock:
            return self._event_counts["total"]

    def get_total_by_type(self, event_type: str) -> int:
        with self._lock:
            return self._event_type_counts.get(event_type, 0)

    def get_avg_duration(self, bucket: str) -> float:
        with self._lock:
            vals = self._durations.get(bucket, [])
            if not vals:
                return 0.0
            return sum(vals) / len(vals)

    def get_p99_duration(self, bucket: str) -> float:
        with self._lock:
            vals = sorted(self._durations.get(bucket, []))
            if not vals:
                return 0.0
            idx = int(len(vals) * 0.99)
            return vals[min(idx, len(vals) - 1)]

    def get_voter_vote_count(self, voter: str, decision: str | None = None) -> int:
        with self._lock:
            counts = self._vote_counts.get(voter, {})
            if decision:
                return counts.get(decision, 0)
            return sum(counts.values())

    def get_scope_metrics(self, scope: str) -> dict[str, float]:
        with self._lock:
            return {
                "total_events": float(sum(self._scope_event_counts[scope].values())),
                "error_count": float(self._scope_error_counts.get(scope, 0)),
                "event_rate": self.get_event_rate(),
            }

    def voter_approval_rate(self, voter: str) -> float:
        with self._lock:
            counts = self._vote_counts.get(voter, {})
            total = sum(counts.values())
            if total == 0:
                return 0.0
            approves = counts.get("approve", 0)
            return approves / total

    def reset(self) -> None:
        with self._lock:
            self._event_counts.clear()
            self._event_type_counts.clear()
            self._scope_event_counts.clear()
            self._scope_error_counts.clear()
            self._durations.clear()
            self._event_timestamps.clear()
            self._vote_counts.clear()
