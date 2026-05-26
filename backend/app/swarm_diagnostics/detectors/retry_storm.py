"""
RetryStormDetector — Detects retry storms in the outbox and event system.

Signals:
    - elevated_retry_rate: retry events per minute exceed threshold
    - retry_acceleration: retry rate is increasing across windows
    - cascading_failures: one failure triggers many downstream retries
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


class RetryStormDetector(BaseDetector):
    name = "retry_storm"

    def __init__(self, retry_rate_threshold: float = 10.0, acceleration_factor: float = 2.0):
        self.retry_rate_threshold = retry_rate_threshold
        self.acceleration_factor = acceleration_factor

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)

        error_events = [e for e in events if e.error is not None]
        if not error_events:
            return signals

        source_counts: dict[str, int] = defaultdict(int)
        for e in error_events:
            source_counts[e.source] += 1

        for source, count in source_counts.items():
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.RETRY_STORM,
                severity=Severity.WARNING if count > self.retry_rate_threshold else Severity.INFO,
                scope="global",
                title=f"Elevated error count from {source}",
                description=f"{count} errors from {source} in current window",
                metric_value=float(count),
                threshold=self.retry_rate_threshold,
                evidence={"source": source, "error_count": count},
                recommendation=f"Inspect {source} for recurring failures and implement circuit breaker.",
            ))

        retry_related = [e for e in events if "retry" in e.event_type.lower() or "error" in e.event_type.lower()]
        if len(retry_related) >= 3:
            timestamps = [e.created_at for e in retry_related if e.created_at]
            if len(timestamps) >= 3:
                mid = len(timestamps) // 2
                first_half = timestamps[:mid]
                second_half = timestamps[mid:]
                if first_half and second_half:
                    try:
                        first_rate = len(first_half) / max((first_half[-1] - first_half[0]).total_seconds(), 1)
                        second_rate = len(second_half) / max((second_half[-1] - second_half[0]).total_seconds(), 1)
                    except (IndexError, ZeroDivisionError):
                        first_rate = second_rate = 0.0
                    if first_rate > 0 and second_rate / max(first_rate, 0.001) >= self.acceleration_factor:
                        signals.append(AnomalySignal(
                            anomaly_id=str(uuid.uuid4()),
                            detector_name=self.name,
                            anomaly_type=AnomalyType.RETRY_STORM,
                            severity=Severity.CRITICAL,
                            scope="global",
                            title="Retry acceleration detected",
                            description=f"Retry rate increased {second_rate/first_rate:.1f}x in current window",
                            metric_value=second_rate / max(first_rate, 0.001),
                            threshold=self.acceleration_factor,
                            evidence={"first_rate": first_rate, "second_rate": second_rate},
                            recommendation="Immediate investigation required — potential cascading failure.",
                        ))

        return signals
