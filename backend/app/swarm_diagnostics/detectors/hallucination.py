from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


class HallucinationDetector(BaseDetector):
    name = "hallucination_detector"

    def __init__(
        self,
        overconfidence_threshold: float = 0.3,
        flip_window: int = 10,
        calibration_error_threshold: float = 0.5,
        min_votes: int = 10,
    ) -> None:
        self.overconfidence_threshold = overconfidence_threshold
        self.flip_window = flip_window
        self.calibration_error_threshold = calibration_error_threshold
        self.min_votes = min_votes

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics=None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        vote_events = [e for e in events if e.event_type.startswith("vote:")]

        voter_decisions: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for e in vote_events:
            voter_decisions[e.source].append({
                "decision": e.payload.get("decision", ""),
                "confidence": e.payload.get("confidence", 0.5),
                "created_at": e.created_at,
            })

        for voter, decisions in voter_decisions.items():
            if len(decisions) < self.min_votes:
                continue

            signals.extend(self._detect_overconfidence(voter, decisions))
            signals.extend(self._detect_flipping(voter, decisions))
            signals.extend(self._detect_calibration_drift(voter, decisions))

        return signals

    def _detect_overconfidence(
        self, voter: str, decisions: list[dict],
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        recent = decisions[-self.flip_window:]
        if not recent:
            return signals

        avg_confidence = sum(d["confidence"] for d in recent) / len(recent)
        approvals = sum(1 for d in recent if d["decision"] == "approve")
        approval_rate = approvals / len(recent)

        error = avg_confidence - approval_rate
        if error > self.overconfidence_threshold and avg_confidence > 0.7:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.HALLUCINATION,
                severity=Severity.CRITICAL,
                scope="global",
                title=f"Potential hallucination: {voter}",
                description=(
                    f"{voter} shows overconfidence pattern: "
                    f"avg confidence {avg_confidence:.2f} vs approval rate {approval_rate:.2f}"
                ),
                metric_value=error,
                threshold=self.overconfidence_threshold,
                evidence={
                    "voter": voter,
                    "avg_confidence": avg_confidence,
                    "approval_rate": approval_rate,
                    "calibration_error": error,
                    "pattern": "overconfidence",
                    "window_size": len(recent),
                },
                recommendation=(
                    f"Review {voter} voter calibration. "
                    "High confidence with low approval suggests unreliable outputs."
                ),
            ))

        return signals

    def _detect_flipping(
        self, voter: str, decisions: list[dict],
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        recent = decisions[-self.flip_window:]
        if len(recent) < 4:
            return signals

        decisions_seq = [d["decision"] for d in recent]
        flips = sum(1 for i in range(1, len(decisions_seq)) if decisions_seq[i] != decisions_seq[i - 1])
        flip_rate = flips / (len(decisions_seq) - 1)

        if flip_rate > 0.5:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.HALLUCINATION,
                severity=Severity.WARNING,
                scope="global",
                title=f"Decision flipping: {voter}",
                description=(
                    f"{voter} flips decisions {flip_rate:.0%} of the time — erratic behavior pattern"
                ),
                metric_value=flip_rate,
                threshold=0.5,
                evidence={
                    "voter": voter,
                    "flip_rate": flip_rate,
                    "total_flips": flips,
                    "window_size": len(recent),
                    "pattern": "decision_flipping",
                },
                recommendation=(
                    f"Review {voter} voter. "
                    "Frequent decision changes may indicate instability."
                ),
            ))

        return signals

    def _detect_calibration_drift(
        self, voter: str, decisions: list[dict],
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        recent = decisions[-self.flip_window:]
        older = decisions[:len(decisions) // 2] if len(decisions) >= 2 * self.flip_window else decisions[:-self.flip_window]

        if not older or not recent:
            return signals

        recent_conf = sum(d["confidence"] for d in recent) / len(recent)
        recent_approval = sum(1 for d in recent if d["decision"] == "approve") / len(recent)
        recent_error = abs(recent_conf - recent_approval)

        older_conf = sum(d["confidence"] for d in older) / len(older)
        older_approval = sum(1 for d in older if d["decision"] == "approve") / len(older)
        older_error = abs(older_conf - older_approval)

        drift = recent_error - older_error
        if drift > self.calibration_error_threshold:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.HALLUCINATION,
                severity=Severity.WARNING,
                scope="global",
                title=f"Calibration drift: {voter}",
                description=(
                    f"{voter} calibration error increased from {older_error:.2f} to {recent_error:.2f}"
                ),
                metric_value=drift,
                threshold=self.calibration_error_threshold,
                evidence={
                    "voter": voter,
                    "recent_calibration_error": recent_error,
                    "older_calibration_error": older_error,
                    "drift": drift,
                    "pattern": "calibration_drift",
                },
                recommendation=(
                    f"Review {voter} voter confidence calibration."
                ),
            ))

        return signals
