"""
Tests for the circuit breaker swarm diagnostics detectors:
  - CircuitBreakerRetryStormDetector
  - CascadingFailureDetector
  - RecoveryInstabilityDetector
"""
from __future__ import annotations

from app.swarm_diagnostics.detectors.circuit_breaker import (
    CircuitBreakerRetryStormDetector,
    CascadingFailureDetector,
    RecoveryInstabilityDetector,
)
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalyType


# ── Helpers ────────────────────────────────────────────────────────────


def make_event(
    event_type: str = "circuit_breaker.transition",
    *,
    source: str = "circuit_breaker",
    state: str = "open",
    agent: str = "mastery",
    error: str | None = None,
) -> DiagnosticEvent:
    from datetime import datetime, timezone
    return DiagnosticEvent(
        event_id="test-id",
        event_type=event_type,
        source=source,
        payload={
            "circuit_breaker": True,
            "state": state,
            "agent": agent,
        },
        error=error,
        created_at=datetime.now(timezone.utc),
    )


class TestCircuitBreakerRetryStormDetector:
    def test_no_events_no_signal(self):
        detector = CircuitBreakerRetryStormDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_high_failure_rate_triggers_signal(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=3, window_seconds=60.0,
        )
        events = [
            make_event("breaker.failure", agent="mastery", error="timeout")
            for _ in range(5)
        ]
        signals = detector.analyze(events)
        retry_signals = [s for s in signals if s.anomaly_type == AnomalyType.RETRY_STORM_AGENT]
        assert len(retry_signals) == 1
        assert "mastery" in retry_signals[0].scope

    def test_low_failure_rate_no_signal(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=5, window_seconds=60.0,
        )
        events = [
            make_event("breaker.failure", agent="mastery", error="err")
            for _ in range(3)
        ]
        signals = detector.analyze(events)
        retry_signals = [s for s in signals if s.anomaly_type == AnomalyType.RETRY_STORM_AGENT]
        assert retry_signals == []

    def test_non_cb_events_ignored(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=1, window_seconds=60.0,
        )
        events = [
            DiagnosticEvent(
                event_id="x", event_type="consensus.vote", source="mastery",
                payload={}, created_at=None,
            )
        ]
        signals = detector.analyze(events)
        assert signals == []

    def test_rapid_cycling_detected(self):
        detector = CircuitBreakerRetryStormDetector(
            min_transitions_for_storm=3, window_seconds=60.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = []
        for i, state in enumerate(["closed", "open", "half_open", "open", "half_open"]):
            events.append(DiagnosticEvent(
                event_id=str(i), event_type="breaker.transition",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": state, "agent": "flaky"},
                created_at=now + timedelta(seconds=i * 0.5),
            ))
        signals = detector.analyze(events)
        instability_signals = [s for s in signals if s.anomaly_type == AnomalyType.RECOVERY_INSTABILITY]
        assert len(instability_signals) >= 1
        assert "flaky" in instability_signals[0].scope


class TestCascadingFailureDetector:
    def test_no_open_events_no_signal(self):
        detector = CascadingFailureDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_single_agent_open_no_signal(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
        )
        events = [make_event(agent="mastery")]
        signals = detector.analyze(events)
        assert signals == []

    def test_multiple_agents_open_triggers_cascade(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
            max_agent_gap_seconds=5.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "a"},
                created_at=now,
            ),
            DiagnosticEvent(
                event_id="2", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "b"},
                created_at=now + timedelta(seconds=1),
            ),
        ]
        signals = detector.analyze(events)
        cascade = [s for s in signals if s.anomaly_type == AnomalyType.CASCADING_FAILURE]
        assert len(cascade) >= 1

    def test_agents_outside_window_no_cascade(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
            max_agent_gap_seconds=1.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "a"},
                created_at=now,
            ),
            DiagnosticEvent(
                event_id="2", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "b"},
                created_at=now + timedelta(seconds=10),  # too late
            ),
        ]
        signals = detector.analyze(events)
        cascade = [s for s in signals if s.anomaly_type == AnomalyType.CASCADING_FAILURE]
        assert cascade == []


class TestRecoveryInstabilityDetector:
    def test_no_transitions_no_signal(self):
        detector = RecoveryInstabilityDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_oscillation_detected(self):
        detector = RecoveryInstabilityDetector(
            instability_window_seconds=120.0,
            min_open_half_open_cycles=2,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = []
        for i in range(4):
            events.append(DiagnosticEvent(
                event_id=str(i * 2),
                event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "osc"},
                created_at=now + timedelta(seconds=i * 2),
            ))
            events.append(DiagnosticEvent(
                event_id=str(i * 2 + 1),
                event_type="breaker.half_open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "half_open", "agent": "osc"},
                created_at=now + timedelta(seconds=i * 2 + 1),
            ))
        signals = detector.analyze(events)
        instability = [s for s in signals if s.anomaly_type == AnomalyType.RECOVERY_INSTABILITY]
        assert len(instability) >= 1
        assert "osc" in instability[0].scope

    def test_stable_breaker_no_signal(self):
        detector = RecoveryInstabilityDetector(
            min_open_half_open_cycles=5,
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "stable"},
                created_at=now,
            ),
        ]
        signals = detector.analyze(events)
        assert signals == []

    def test_repeated_isolation_detected(self):
        detector = RecoveryInstabilityDetector(
            consecutively_isolated_threshold=2,
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="breaker.isolated",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "isolated", "agent": "bad"},
                created_at=now,
            )
            for i in range(3)
        ]
        signals = detector.analyze(events)
        isolated = [s for s in signals if "isolation" in s.title.lower()]
        assert len(isolated) >= 1


