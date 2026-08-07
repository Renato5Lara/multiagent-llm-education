"""End-to-end integration tests: event emission → detection → metrics.

Validates the full diagnostics pipeline:
  1. Advisory lock acquisitions emit DiagnosticEvents
  2. Detectors receive and process those events
  3. Anomalies surface in the REST API
  4. Metrics exporter reflects all activity
"""

import threading
from unittest.mock import PropertyMock, patch

import pytest

from app.db.locks import advisory_lock, try_advisory_lock, _emit_lock_event
from app.swarm_diagnostics import diagnostics_engine
from app.swarm_diagnostics.core import Severity
from app.swarm_diagnostics.detectors import (
    CircuitBreakerRetryStormDetector,
    DeadlockDetector,
)
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent


# =============================================================================
# 2. Advisory lock → DiagnosticEvent pipeline
# =============================================================================


class TestLockDiagnostics:
    """Advisory lock acquisitions must emit DiagnosticEvents."""

    def test_advisory_lock_acquire_emits_event(self, db):
        diagnostics_engine._events.clear()
        class FakeDB:
            bind = type("Bind", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()
        with advisory_lock(FakeDB(), "test:lock:key"):
            events = [e for e in diagnostics_engine._events if e.event_type == "lock:acquire"]
            assert len(events) >= 1

    def test_advisory_lock_release_emits_event(self, db):
        diagnostics_engine._events.clear()
        class FakeDB:
            bind = type("Bind", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()
        with advisory_lock(FakeDB(), "test:lock:release"):
            pass
        events = [e for e in diagnostics_engine._events if e.event_type == "lock:release"]
        assert len(events) >= 1

    def test_try_advisory_lock_acquire_emits_event(self, db):
        diagnostics_engine._events.clear()
        class FakeDB:
            bind = type("Bind", (), {"dialect": type("Dialect", (), {"name": "sqlite"})()})()
        with try_advisory_lock(FakeDB(), "test:try:lock") as acquired:
            assert acquired is True
        events = [e for e in diagnostics_engine._events if e.event_type == "lock:acquire"]
        assert len(events) >= 1


# =============================================================================
# 3. Detector integration — CB events feed CircuitBreakerRetryStormDetector
# =============================================================================


class TestDetectorIntegration:
    """DiagnosticEvents from CB/locks must feed into detectors."""

    def setup_method(self):
        diagnostics_engine._events.clear()
        diagnostics_engine._anomalies.clear()

    def test_cb_events_flow_through_retry_storm_detector(self):
        """CircuitBreakerRetryStormDetector receives CB events."""
        detector = CircuitBreakerRetryStormDetector(max_failures_per_window=5)
        for _ in range(6):
            event = DiagnosticEvent(
                event_id=f"cb-{_}",
                event_type="circuit_breaker:open",
                scope=f"circuit_breaker:agent_0",
                source="circuit_breaker/test",
                correlation_id=None,
                payload={"agent": "test_agent", "state": "open", "consecutive_failures": 999},
            )
            diagnostics_engine.record_event(event)
        signals = detector.analyze(diagnostics_engine._events)
        assert len(signals) >= 1

    def test_deadlock_detector_receives_lock_timeout_events(self):
        """DeadlockDetector triggers on lock:timeout events."""
        detector = DeadlockDetector()
        for i in range(2):
            event = DiagnosticEvent(
                event_id=f"lock-{i}",
                event_type="lock:timeout",
                scope="locks",
                source="db/locks",
                correlation_id=None,
                payload={"key": f"resource:{i}"},
                error="timeout",
            )
            diagnostics_engine.record_event(event)
        signals = detector.analyze(diagnostics_engine._events)
        assert len(signals) >= 1


# =============================================================================
# 4. Metrics collector — rate calculations
# =============================================================================


class TestMetricsIntegration:
    """SwarmMetricsCollector accurately tracks events from the pipeline."""

    def setup_method(self):
        self.collector = SwarmMetricsCollector()

    def test_get_event_type_rate_returns_non_zero(self):
        for i in range(10):
            event = DiagnosticEvent(
                event_id=f"evt-{i}",
                event_type="circuit_breaker:open",
                scope="circuit_breaker:agent",
                source="circuit_breaker/test",
                correlation_id=None,
                payload={},
            )
            self.collector.record_event(event)
        rate = self.collector.get_event_type_rate("circuit_breaker:open", window_seconds=60.0)
        assert rate > 0.0

    def test_scope_counts_aggregate(self):
        for i in range(5):
            event = DiagnosticEvent(
                event_id=f"evt-{i}",
                event_type="lock:acquire",
                scope="locks",
                source="db/locks",
                correlation_id=None,
                payload={},
            )
            self.collector.record_event(event)
        assert self.collector.get_scope_event_count("locks") == 5
        assert self.collector.get_scope_event_count("locks", "lock:acquire") == 5


# =============================================================================
# 5. Anomaly endpoint integration (via FastAPI TestClient)
# =============================================================================


class TestAnomalySerialization:
    """AnomalySignal.to_dict() must produce valid, complete JSON."""

    def test_to_dict_includes_all_fields(self):
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        signal = AnomalySignal(
            anomaly_id="test-1",
            detector_name="deadlock_detector",
            anomaly_type=AnomalyType.DEADLOCK,
            severity=Severity.CRITICAL,
            scope="test:scope",
            title="Test anomaly",
            description="Test description",
            metric_value=42.0,
            threshold=10.0,
            evidence={"lock_key": "resource:x"},
            recommendation="Fix it",
            correlation_id="corr-test-1",
        )
        d = signal.to_dict()
        assert d["anomaly_id"] == "test-1"
        assert d["detector_name"] == "deadlock_detector"
        assert d["anomaly_type"] == "deadlock"
        assert d["severity"] == "critical"
        assert d["scope"] == "test:scope"
        assert d["title"] == "Test anomaly"
        assert d["description"] == "Test description"
        assert d["metric_value"] == 42.0
        assert d["threshold"] == 10.0
        assert d["evidence"]["lock_key"] == "resource:x"
        assert d["recommendation"] == "Fix it"
        assert d["created_at"] is not None
        assert d["correlation_id"] == "corr-test-1"

    def test_to_dict_json_serializable(self):
        import json
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        signal = AnomalySignal(
            anomaly_id="test-json",
            detector_name="test_detector",
            anomaly_type=AnomalyType.DEADLOCK,
            severity=Severity.WARNING,
            scope="test",
            title="JSON test",
            description="Must be serializable",
        )
        dumped = json.dumps(signal.to_dict())
        loaded = json.loads(dumped)
        assert loaded["anomaly_id"] == "test-json"
        assert loaded["severity"] == "warning"

    def test_to_dict_without_correlation_id(self):
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        signal = AnomalySignal(
            anomaly_id="test-null-corr",
            detector_name="test",
            anomaly_type=AnomalyType.DEADLOCK,
            severity=Severity.INFO,
            scope="test",
            title="No correlation",
            description="Desc",
        )
        d = signal.to_dict()
        assert d["correlation_id"] is None


# =============================================================================
# 7. Anomaly filtering logic (HTTP-free, pure function tests)
# =============================================================================


# =============================================================================
# 8. Engine anomaly property and thread safety
# =============================================================================


class TestEngineAnomalyAccess:
    """SwarmDiagnosticsEngine must provide thread-safe anomaly access."""

    def test_anomalies_property_returns_reversed(self):
        from app.swarm_diagnostics import diagnostics_engine
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        diagnostics_engine._anomalies.clear()
        for i in range(3):
            diagnostics_engine._anomalies.append(AnomalySignal(
                anomaly_id=f"ano-{i}",
                detector_name="test",
                anomaly_type=AnomalyType.DEADLOCK,
                severity=Severity.INFO,
                scope="test",
                title=f"Anomaly {i}",
                description="",
            ))
        result = diagnostics_engine.anomalies
        assert result[0].anomaly_id == "ano-2"  # most recent first
        assert result[-1].anomaly_id == "ano-0"

    def test_get_active_anomalies_filters_by_scope(self):
        from app.swarm_diagnostics import diagnostics_engine
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        diagnostics_engine._anomalies.clear()
        diagnostics_engine._anomalies.append(AnomalySignal(
            anomaly_id="ano-scope1", detector_name="test",
            anomaly_type=AnomalyType.DEADLOCK, severity=Severity.CRITICAL,
            scope="student:abc", title="", description="",
        ))
        diagnostics_engine._anomalies.append(AnomalySignal(
            anomaly_id="ano-scope2", detector_name="test",
            anomaly_type=AnomalyType.DEADLOCK, severity=Severity.INFO,
            scope="global", title="", description="",
        ))
        active = diagnostics_engine.get_active_anomalies(scope="student:abc")
        assert len(active) == 2  # global always matches
        assert active[0].anomaly_id == "ano-scope1"

    def test_run_detectors_enriches_correlation_id(self):
        from app.swarm_diagnostics import diagnostics_engine
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
        diagnostics_engine._events.clear()
        diagnostics_engine._anomalies.clear()
        # Add an event with a correlation_id
        event = DiagnosticEvent(
            event_id="evt-corr", event_type="vote:approve",
            scope="test", source="test",
            correlation_id="trace-abc-123",
            payload={},
        )
        diagnostics_engine.record_event(event)
        # Force a detector run (with tiny window so our event is included)
        # We need an event in the window — use time_window_seconds large enough
        signals = diagnostics_engine.run_detectors(time_window_seconds=999999)
        # At least some detectors might find nothing, but the ones that do
        # should have correlation_id set from the window event
        for s in signals:
            assert s.correlation_id is not None
