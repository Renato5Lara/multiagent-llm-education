"""
DeadlockDetector — Monitors advisory lock acquisition times and detects
contention patterns.

Signals:
    - slow_lock_acquisition: lock wait time exceeds threshold
    - lock_contention_hotspot: specific lock key shows repeated slow acquires
    - deadlock_timeout: lock acquisition failed entirely (timeout)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class DeadlockDetector(BaseDetector):
    name = "deadlock_detector"

    def __init__(self, slow_lock_threshold_ms: float = 1000.0, hotspot_threshold: int = 3):
        self.slow_lock_threshold_ms = slow_lock_threshold_ms
        self.hotspot_threshold = hotspot_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        lock_events = [e for e in events if "lock" in e.event_type.lower()]

        slow_locks: list[DiagnosticEvent] = []
        for e in lock_events:
            if e.duration_ms is not None and e.duration_ms > self.slow_lock_threshold_ms:
                slow_locks.append(e)

        if slow_locks:
            lock_key_counts: dict[str, int] = defaultdict(int)
            for e in slow_locks:
                key = e.payload.get("lock_key", e.scope)
                lock_key_counts[key] += 1
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.DEADLOCK,
                    severity=Severity.WARNING,
                    scope=e.scope,
                    title="Slow lock acquisition",
                    description=f"Lock on '{key}' took {e.duration_ms:.0f}ms (threshold {self.slow_lock_threshold_ms:.0f}ms)",
                    metric_value=e.duration_ms,
                    threshold=self.slow_lock_threshold_ms,
                    evidence={
                        "lock_key": key,
                        "duration_ms": e.duration_ms,
                        "event_type": e.event_type,
                    },
                    recommendation="Check for long-running transactions on the same lock key.",
                ))

            for key, count in lock_key_counts.items():
                if count >= self.hotspot_threshold:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.DEADLOCK,
                        severity=Severity.WARNING,
                        scope="global",
                        title="Lock contention hotspot",
                        description=f"Key '{key}' had {count} slow acquisitions",
                        metric_value=float(count),
                        threshold=float(self.hotspot_threshold),
                        evidence={"lock_key": key, "slow_acquire_count": count},
                        recommendation="Review transaction scope — consider finer-grained locks.",
                    ))

        error_lock_events = [e for e in lock_events if e.error is not None]
        if error_lock_events:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.DEADLOCK,
                severity=Severity.CRITICAL,
                scope="global",
                title="Lock acquisition failures",
                description=f"{len(error_lock_events)} lock operations failed with errors",
                metric_value=float(len(error_lock_events)),
                threshold=1.0,
                evidence={"failed_locks": [{"key": e.payload.get("lock_key", ""), "error": e.error} for e in error_lock_events[:10]]},
                recommendation="Investigate deadlock conditions — reduce lock scope or increase timeouts.",
            ))

        return signals
