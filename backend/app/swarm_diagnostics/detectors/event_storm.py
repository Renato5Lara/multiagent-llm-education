"""
EventStormDetector — Detects abnormal spikes in event volume that may
indicate cascading or runaway behavior.

Signals:
    - event_rate_spike: events/sec exceeds threshold
    - scope_storm: specific scope shows sudden event burst
    - type_concentration: single event type dominates the stream
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class EventStormDetector(BaseDetector):
    name = "event_storm"

    def __init__(self, rate_spike_threshold: float = 50.0, type_concentration_threshold: float = 0.8):
        self.rate_spike_threshold = rate_spike_threshold
        self.type_concentration_threshold = type_concentration_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        if len(events) < 10:
            return signals

        scope_counts: dict[str, int] = defaultdict(int)
        type_counts: dict[str, int] = defaultdict(int)
        for e in events:
            scope_counts[e.scope] += 1
            type_counts[e.event_type] += 1

        if metrics:
            rate = metrics.get_event_rate(window_seconds=60.0)
            if rate > self.rate_spike_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EVENT_STORM,
                    severity=Severity.WARNING,
                    scope="global",
                    title="Event rate spike detected",
                    description=f"Event rate {rate:.1f} events/sec exceeds threshold {self.rate_spike_threshold}",
                    metric_value=rate,
                    threshold=self.rate_spike_threshold,
                    evidence={"events_per_sec": rate, "total_in_window": len(events)},
                    recommendation="Check for runaway loops or cascading agent activations.",
                ))

        for scope, count in scope_counts.items():
            if count > len(events) * 0.5 and count >= 20:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EVENT_STORM,
                    severity=Severity.INFO,
                    scope=scope,
                    title=f"Scope {scope} event concentration",
                    description=f"{count} events in scope ({count/len(events):.0%} of total)",
                    metric_value=float(count),
                    threshold=float(len(events) * 0.5),
                    evidence={"scope": scope, "event_count": count, "total": len(events)},
                    recommendation="Scoped event bursts may indicate tight processing loops.",
                ))

        if type_counts:
            dominant_type = max(type_counts, key=type_counts.get)
            dominant_count = type_counts[dominant_type]
            concentration = dominant_count / len(events)
            if concentration >= self.type_concentration_threshold and dominant_count >= 10:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EVENT_STORM,
                    severity=Severity.INFO,
                    scope="global",
                    title=f"Event type concentration: {dominant_type}",
                    description=f"{dominant_type} accounts for {concentration:.0%} of all events",
                    metric_value=concentration,
                    threshold=self.type_concentration_threshold,
                    evidence={"dominant_type": dominant_type, "count": dominant_count, "total": len(events)},
                    recommendation="High single-type concentration may indicate a one-task bottleneck.",
                ))

        return signals
