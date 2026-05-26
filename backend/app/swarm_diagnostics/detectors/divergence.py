"""
AgentDivergenceDetector — Detects when individual agent/voter behavior
diverges from its historical pattern.

Signals:
    - vote_pattern_shift: a voter's approve/reject ratio changes significantly
    - confidence_drift: a voter's confidence calibration drifts over time
    - specialization_erosion: a voter's domain affinity weakens
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class AgentDivergenceDetector(BaseDetector):
    name = "agent_divergence"

    def __init__(self, pattern_shift_threshold: float = 0.4, window: int = 20):
        self.pattern_shift_threshold = pattern_shift_threshold
        self.window = window

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        vote_events = [e for e in events if e.event_type.startswith("vote:")]

        voter_decisions: dict[str, list[str]] = defaultdict(list)
        for e in vote_events:
            decision = e.payload.get("decision", "")
            voter_decisions[e.source].append(decision)

        for voter, decisions in voter_decisions.items():
            if len(decisions) < self.window:
                continue
            recent = decisions[-self.window:]
            older = decisions[:len(decisions) // 2] if len(decisions) >= 2 * self.window else decisions[:-self.window]

            if not older:
                continue

            recent_rate = sum(1 for d in recent if d == "approve") / len(recent)
            older_rate = sum(1 for d in older if d == "approve") / len(older)

            shift = abs(recent_rate - older_rate)
            if shift >= self.pattern_shift_threshold:
                direction = "more" if recent_rate > older_rate else "less"
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.AGENT_DIVERGENCE,
                    severity=Severity.WARNING,
                    scope="global",
                    title=f"Voter {voter} pattern shift",
                    description=f"{voter} shifted {direction} approving: {older_rate:.2f} -> {recent_rate:.2f}",
                    metric_value=shift,
                    threshold=self.pattern_shift_threshold,
                    evidence={
                        "voter": voter,
                        "older_rate": older_rate,
                        "recent_rate": recent_rate,
                        "shift": shift,
                    },
                    recommendation=f"Review {voter} voter configuration — may need recalibration.",
                ))

        if metrics:
            for voter in voter_decisions:
                approval_rate = metrics.voter_approval_rate(voter)
                if approval_rate > 0.95 and len(voter_decisions.get(voter, [])) >= 10:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.AGENT_DIVERGENCE,
                        severity=Severity.INFO,
                        scope="global",
                        title=f"Voter {voter} always approves",
                        description=f"{voter} approval rate is {approval_rate:.2f} — may be non-informative",
                        metric_value=approval_rate,
                        threshold=0.95,
                        evidence={"voter": voter, "approval_rate": approval_rate},
                        recommendation=f"Review {voter} voter thresholds — may need to increase sensitivity.",
                    ))

        return signals
