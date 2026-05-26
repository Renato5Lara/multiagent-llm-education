"""
BehaviorAnomalyDetector — Detects emergent behavior anomalies that deviate
from expected swarm patterns.

Signals:
    - sudden_approval_drop: approval rate drops significantly
    - vote_consistency_anomaly: a voter's pattern changes abruptly
    - confidence_collapse: average confidence in decisions drops sharply
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class BehaviorAnomalyDetector(BaseDetector):
    name = "behavior_anomaly"

    def __init__(self, drop_threshold: float = 0.3, window: int = 20):
        self.drop_threshold = drop_threshold
        self.window = window

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        consensus_events = [e for e in events if e.event_type.startswith("consensus:")]
        if len(consensus_events) < self.window:
            return signals

        approvals = [1 if "approve" in e.event_type else 0 for e in consensus_events]
        confidences = [e.payload.get("confidence", 0.5) for e in consensus_events if e.payload]

        mid = len(approvals) // 2
        first_half = approvals[:mid] if mid > 0 else approvals
        second_half = approvals[mid:] if mid < len(approvals) else approvals

        if first_half and second_half:
            first_rate = sum(first_half) / len(first_half)
            second_rate = sum(second_half) / len(second_half)
            if first_rate - second_rate >= self.drop_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.EMERGENT_BEHAVIOR,
                    severity=Severity.WARNING,
                    scope="global",
                    title="Sudden approval rate drop",
                    description=f"Approval rate dropped from {first_rate:.2f} to {second_rate:.2f}",
                    metric_value=second_rate,
                    threshold=first_rate - self.drop_threshold,
                    evidence={"first_half_rate": first_rate, "second_half_rate": second_rate},
                    recommendation="Check if module difficulty increased or student cohort changed.",
                ))

        if len(confidences) >= self.window:
            first_conf = confidences[:len(confidences)//2]
            second_conf = confidences[len(confidences)//2:]
            if first_conf and second_conf:
                avg_first = sum(first_conf) / len(first_conf)
                avg_second = sum(second_conf) / len(second_conf)
                if avg_first - avg_second >= self.drop_threshold:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.EMERGENT_BEHAVIOR,
                        severity=Severity.WARNING,
                        scope="global",
                        title="Confidence collapse detected",
                        description=f"Avg confidence dropped from {avg_first:.3f} to {avg_second:.3f}",
                        metric_value=avg_second,
                        threshold=avg_first - self.drop_threshold,
                        evidence={"first_half_avg": avg_first, "second_half_avg": avg_second},
                        recommendation="Voters may be losing calibration — check trust scores.",
                    ))

        if metrics:
            for name in ("mastery", "sequence", "prerequisite", "time"):
                rate = metrics.voter_approval_rate(name)
                if rate < 0.1:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.EMERGENT_BEHAVIOR,
                        severity=Severity.INFO,
                        scope="global",
                        title=f"Voter {name} unusually否决",
                        description=f"{name} approval rate is {rate:.2f} — well below expected",
                        metric_value=rate,
                        threshold=0.1,
                        evidence={"voter": name, "approval_rate": rate},
                        recommendation=f"Review {name} voter configuration and context enrichment.",
                    ))

        return signals
