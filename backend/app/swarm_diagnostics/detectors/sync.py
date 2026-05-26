"""
SyncDelayMonitor — Monitors synchronization delays between event creation
and consumption, and outbox queue depth trends.

Signals:
    - processing_delay: event processing latency exceeds threshold
    - outbox_backlog: pending outbox events exceed threshold
    - batch_accumulation: events accumulate in bursts
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class SyncDelayMonitor(BaseDetector):
    name = "sync_delay_monitor"

    def __init__(self, delay_threshold_ms: float = 2000.0, backlog_threshold: int = 50):
        self.delay_threshold_ms = delay_threshold_ms
        self.backlog_threshold = backlog_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)

        causation_pairs: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        for e in events:
            if e.causation_id:
                causation_pairs.setdefault(e.causation_id, []).append(e)

        for parent_id, children in causation_pairs.items():
            parent = None
            for e in events:
                if e.event_id == parent_id:
                    parent = e
                    break
            if not parent or parent.created_at is None:
                continue
            for child in children:
                if child.created_at is None:
                    continue
                delay = (child.created_at - parent.created_at).total_seconds() * 1000
                if delay > self.delay_threshold_ms:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.SYNC_DELAY,
                        severity=Severity.WARNING,
                        scope=child.scope,
                        title="Event synchronization delay",
                        description=f"Processing delay {delay:.0f}ms exceeds threshold {self.delay_threshold_ms:.0f}ms",
                        metric_value=delay,
                        threshold=self.delay_threshold_ms,
                        evidence={
                            "parent_id": parent_id,
                            "child_id": child.event_id,
                            "parent_type": parent.event_type,
                            "child_type": child.event_type,
                            "delay_ms": delay,
                        },
                        recommendation="Check consumer processing capacity and queue depth.",
                    ))

        execution_events = [e for e in events if e.event_type.startswith("execution:")]
        slow_executions = [e for e in execution_events if e.duration_ms is not None and e.duration_ms > self.delay_threshold_ms]
        if len(slow_executions) > len(execution_events) * 0.5 and len(slow_executions) >= 3:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.SYNC_DELAY,
                severity=Severity.WARNING,
                scope="global",
                title="Widespread execution delays",
                description=f"{len(slow_executions)}/{len(execution_events)} executions exceed threshold",
                metric_value=float(len(slow_executions)),
                threshold=float(max(1, int(len(execution_events) * 0.5))),
                evidence={"slow_count": len(slow_executions), "total_count": len(execution_events)},
                recommendation="Generalized slowdown — consider scaling or optimizing agent execution.",
            ))

        outbox_events = [e for e in events if "outbox" in e.event_type.lower()]
        pending = [e for e in outbox_events if "pending" in e.event_type.lower() or (e.payload or {}).get("status") == "pending"]
        if len(pending) >= self.backlog_threshold:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.SYNC_DELAY,
                severity=Severity.WARNING,
                scope="global",
                title="Outbox backlog detected",
                description=f"{len(pending)} pending outbox events exceed threshold {self.backlog_threshold}",
                metric_value=float(len(pending)),
                threshold=float(self.backlog_threshold),
                evidence={"pending_count": len(pending)},
                recommendation="Outbox publisher may be stalled. Check OutboxService health.",
            ))

        return signals
