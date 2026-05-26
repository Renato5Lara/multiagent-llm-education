"""
PropagationFailureDetector — Detects events that were created but never
consumed, and events whose processing exceeded expected latency.

Signals:
    - orphaned_event: event published but no downstream event correlated
    - slow_propagation: time between cause and effect exceeds threshold
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


class PropagationFailureDetector(BaseDetector):
    name = "propagation_failure"

    def __init__(self, latency_threshold_ms: float = 5000.0, orphan_min_age_seconds: float = 60.0):
        self.latency_threshold_ms = latency_threshold_ms
        self.orphan_min_age_seconds = orphan_min_age_seconds

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics=None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        causation_map: dict[str, list[DiagnosticEvent]] = {}
        now = datetime.now(timezone.utc)

        for e in events:
            if e.causation_id:
                causation_map.setdefault(e.causation_id, []).append(e)

        for e in events:
            if not e.causation_id:
                continue
            children = causation_map.get(e.event_id, [])
            if not children:
                age = (now - e.created_at).total_seconds() if e.created_at else 0
                if age >= self.orphan_min_age_seconds:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.PROPAGATION_FAILURE,
                        severity=Severity.WARNING,
                        scope=e.scope,
                        title="Orphaned event detected",
                        description=f"Event {e.event_type} ({e.event_id[:8]}) has no children after {age:.0f}s",
                        metric_value=age,
                        threshold=self.orphan_min_age_seconds,
                        evidence={"event_id": e.event_id, "event_type": e.event_type},
                        recommendation="Check downstream consumer health and event bus connectivity.",
                    ))

        for parent_id, children in causation_map.items():
            parent_event = None
            for e in events:
                if e.event_id == parent_id:
                    parent_event = e
                    break
            if not parent_event or parent_event.created_at is None:
                continue
            for child in children:
                if child.created_at is None:
                    continue
                latency = (child.created_at - parent_event.created_at).total_seconds() * 1000
                if latency > self.latency_threshold_ms:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.PROPAGATION_FAILURE,
                        severity=Severity.WARNING,
                        scope=child.scope,
                        title="Slow event propagation",
                        description=f"Latency {latency:.0f}ms exceeds threshold {self.latency_threshold_ms:.0f}ms",
                        metric_value=latency,
                        threshold=self.latency_threshold_ms,
                        evidence={
                            "parent_id": parent_id,
                            "child_id": child.event_id,
                            "parent_type": parent_event.event_type,
                            "child_type": child.event_type,
                        },
                        recommendation="Investigate queue congestion or processing bottleneck.",
                    ))

        return signals
