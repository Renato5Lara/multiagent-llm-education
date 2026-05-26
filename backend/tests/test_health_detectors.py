"""Tests for Agent Health detectors."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.swarm_diagnostics.detectors.degraded_agent import DegradedAgentDetector
from app.swarm_diagnostics.detectors.hallucination import HallucinationDetector
from app.swarm_diagnostics.detectors.slow_agent import SlowAgentDetector
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, AnomalyType
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent


# ══════════════════════════════════════════════════════════════════════════
# DegradedAgentDetector
# ══════════════════════════════════════════════════════════════════════════


class TestDegradedAgentDetector:
    def test_no_events_no_signal(self):
        detector = DegradedAgentDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_no_degradation_for_healthy_agent(self):
        detector = DegradedAgentDetector(min_window_events=1)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="vote:approve", source="voter_a",
                created_at=now, payload={},
            ),
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0

    def test_cb_opens_trigger_degradation(self):
        detector = DegradedAgentDetector(min_window_events=1, cb_open_threshold=2)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="breaker.open", source="voter_a",
                created_at=now, payload={},
            )
            for i in range(3)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any(s.anomaly_type == AnomalyType.DEGRADED_AGENT for s in signals)
        assert any("voter_a" in s.title for s in signals)

    def test_high_error_rate_triggers(self):
        detector = DegradedAgentDetector(min_window_events=1)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="execution:process:error",
                source="voter_a", created_at=now,
                error="timeout", payload={},
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any("error rate" in s.description for s in signals)

    def test_multiple_agents_isolated(self):
        detector = DegradedAgentDetector(min_window_events=1, cb_open_threshold=2)
        now = datetime.now(timezone.utc)
        events = []
        for i in range(3):
            events.append(DiagnosticEvent(
                event_id=f"a{i}", event_type="breaker.open",
                source="voter_a", created_at=now, payload={},
            ))
            events.append(DiagnosticEvent(
                event_id=f"b{i}", event_type="breaker.open",
                source="voter_b", created_at=now, payload={},
            ))
        signals = detector.analyze(events)
        assert len(signals) >= 2

    def test_non_cb_timeout_events_ignored(self):
        detector = DegradedAgentDetector(min_window_events=5, cb_open_threshold=10)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now, payload={},
            )
            for i in range(10)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0


# ══════════════════════════════════════════════════════════════════════════
# HallucinationDetector
# ══════════════════════════════════════════════════════════════════════════


class TestHallucinationDetector:
    def test_no_events_no_signal(self):
        detector = HallucinationDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_few_votes_no_signal(self):
        detector = HallucinationDetector(min_votes=10)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now,
                payload={"decision": "approve", "confidence": 0.9},
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0

    def test_overconfidence_detected(self):
        detector = HallucinationDetector(
            min_votes=5, overconfidence_threshold=0.3, flip_window=10,
        )
        now = datetime.now(timezone.utc)
        events = []
        for i in range(10):
            events.append(DiagnosticEvent(
                event_id=str(i), event_type="vote:reject", source="voter_a",
                created_at=now,
                payload={"decision": "reject", "confidence": 0.95},
            ))
        signals = detector.analyze(events)
        overconfidence = [s for s in signals if "overconfidence" in s.evidence.get("pattern", "")]
        assert len(overconfidence) >= 1

    def test_decision_flipping_detected(self):
        detector = HallucinationDetector(
            min_votes=5, flip_window=10,
        )
        now = datetime.now(timezone.utc)
        events = []
        for i in range(10):
            decision = "approve" if i % 2 == 0 else "reject"
            events.append(DiagnosticEvent(
                event_id=str(i), event_type=f"vote:{decision}", source="voter_b",
                created_at=now,
                payload={"decision": decision, "confidence": 0.8},
            ))
        signals = detector.analyze(events)
        flipping = [s for s in signals if "decision_flipping" in s.evidence.get("pattern", "")]
        assert len(flipping) >= 1

    def test_calibration_drift_detected(self):
        detector = HallucinationDetector(
            min_votes=10, calibration_error_threshold=0.3,
            flip_window=5,
        )
        now = datetime.now(timezone.utc)
        events = []
        # Older: approve with confidence matching reality
        for i in range(10):
            events.append(DiagnosticEvent(
                event_id=f"old{i}", event_type="vote:approve", source="voter_c",
                created_at=now,
                payload={"decision": "approve", "confidence": 0.7},
            ))
        # Recent: reject with high confidence (poor calibration → high error)
        for i in range(5):
            events.append(DiagnosticEvent(
                event_id=f"new{i}", event_type="vote:reject", source="voter_c",
                created_at=now,
                payload={"decision": "reject", "confidence": 0.9},
            ))
        signals = detector.analyze(events)
        drift = [s for s in signals if "calibration_drift" in s.evidence.get("pattern", "")]
        assert len(drift) >= 1


# ══════════════════════════════════════════════════════════════════════════
# SlowAgentDetector
# ══════════════════════════════════════════════════════════════════════════


class TestSlowAgentDetector:
    def test_no_events_no_signal(self):
        detector = SlowAgentDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_few_samples_no_signal(self):
        detector = SlowAgentDetector(min_samples=10)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now, duration_ms=100.0, payload={},
            )
            for i in range(3)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0

    def test_high_p95_latency_detected(self):
        detector = SlowAgentDetector(min_samples=5, latency_p95_threshold_ms=1000.0)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now, duration_ms=5000.0, payload={},
            )
            for i in range(10)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any("P95" in s.description for s in signals)

    def test_high_timeout_rate_detected(self):
        detector = SlowAgentDetector(min_samples=1, timeout_rate_threshold=0.3)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="vote:approve", source="voter_a",
                created_at=now, duration_ms=100.0, payload={},
            ),
            DiagnosticEvent(
                event_id="2", event_type="consensus:approve", source="engine",
                created_at=now,
                payload={"decision": "approve", "timeout_info": {"voter": "voter_a"}},
            ),
        ]
        signals = detector.analyze(events)
        timeout_signals = [s for s in signals if "timeout" in s.title.lower()]
        assert len(timeout_signals) >= 1

    def test_latency_trend_detected(self):
        detector = SlowAgentDetector(min_samples=1, latency_p95_threshold_ms=50000.0, trend_window=10)
        now = datetime.now(timezone.utc)
        events = []
        for i in range(10):
            events.append(DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now,
                duration_ms=float(100 + i * 100),  # Increasing latency
                payload={},
            ))
        signals = detector.analyze(events)
        trend_signals = [s for s in signals if "increasing" in s.title.lower()]
        assert len(trend_signals) >= 1

    def test_fast_agent_no_signal(self):
        detector = SlowAgentDetector(min_samples=5, latency_p95_threshold_ms=5000.0)
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="vote:approve", source="voter_a",
                created_at=now, duration_ms=10.0, payload={},
            )
            for i in range(10)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0
