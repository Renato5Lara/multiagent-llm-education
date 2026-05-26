"""
ConflictAnalyzer — Detects persistent consensus conflicts across voters.

Signals:
    - elevated_conflict_ratio: high proportion of reject+abstain vs approve
    - persistent_disagreement: same voter pair disagrees repeatedly
    - decision_flip: consensus flips between approve/reject for same scope
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


class ConflictAnalyzer(BaseDetector):
    name = "conflict_analyzer"

    def __init__(
        self,
        conflict_ratio_threshold: float = 0.5,
        disagreement_window: int = 10,
    ):
        self.conflict_ratio_threshold = conflict_ratio_threshold
        self.disagreement_window = disagreement_window

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics=None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        consensus_events = [e for e in events if e.event_type.startswith("consensus:")]
        if len(consensus_events) < 3:
            return signals

        scope_decisions: dict[str, list[str]] = defaultdict(list)
        for e in consensus_events:
            decision = e.event_type.split(":", 1)[1] if ":" in e.event_type else ""
            scope_decisions[e.scope].append(decision)

        for scope, decisions in scope_decisions.items():
            recent = decisions[-self.disagreement_window:]
            if len(recent) < 3:
                continue
            rejects = sum(1 for d in recent if d == "reject")
            ratio = rejects / len(recent)
            if ratio >= self.conflict_ratio_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.CONSENSUS_CONFLICT,
                    severity=Severity.WARNING,
                    scope=scope,
                    title="Elevated consensus conflict ratio",
                    description=f"{rejects}/{len(recent)} recent decisions are reject (ratio={ratio:.2f})",
                    metric_value=ratio,
                    threshold=self.conflict_ratio_threshold,
                    evidence={"scope": scope, "decisions": recent},
                    recommendation="Review voter trust scores and module difficulty calibration.",
                ))

            flips = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])
            if flips >= 3:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.CONSENSUS_CONFLICT,
                    severity=Severity.WARNING,
                    scope=scope,
                    title="Decision flipping detected",
                    description=f"{flips} decision changes in last {len(recent)} runs",
                    metric_value=float(flips),
                    threshold=3.0,
                    evidence={"scope": scope, "decisions": recent},
                    recommendation="Inspect voter context — unstable signals indicate misconfiguration.",
                ))

        vote_events = [e for e in events if e.event_type.startswith("vote:")]
        voter_disagreements: dict[tuple[str, str], int] = defaultdict(int)
        for i in range(len(vote_events)):
            for j in range(i + 1, len(vote_events)):
                a, b = vote_events[i], vote_events[j]
                if a.source == b.source:
                    continue
                if a.scope != b.scope:
                    continue
                a_dec = a.payload.get("decision", "")
                b_dec = b.payload.get("decision", "")
                if a_dec != b_dec and a_dec in ("approve", "reject") and b_dec in ("approve", "reject"):
                    pair = tuple(sorted([a.source, b.source]))
                    voter_disagreements[pair] += 1

        for (v1, v2), count in voter_disagreements.items():
            if count >= self.disagreement_window:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.CONSENSUS_CONFLICT,
                    severity=Severity.INFO,
                    scope="global",
                    title="Persistent voter disagreement",
                    description=f"Voters {v1} and {v2} disagree {count} times",
                    metric_value=float(count),
                    threshold=float(self.disagreement_window),
                    evidence={"voter_a": v1, "voter_b": v2, "disagreement_count": count},
                    recommendation="Review specialization profiles — voters may need recalibration.",
                ))

        return signals
