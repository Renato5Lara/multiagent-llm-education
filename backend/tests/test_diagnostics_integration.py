"""End-to-end integration tests: event emission → detection → metrics.

Validates the full diagnostics pipeline:
  1. Circuit breaker state transitions emit DiagnosticEvents
  2. Advisory lock acquisitions emit DiagnosticEvents
  3. Detectors receive and process those events
  4. Anomalies surface in the REST API
  5. Metrics exporter reflects all activity
"""

import threading
import time
from unittest.mock import PropertyMock, patch

import pytest

from app.core.circuit_breaker import (
    CircuitBreakerConfig,
    SwarmCircuitBreaker,
)
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
# 1. Circuit breaker → DiagnosticEvent pipeline
# =============================================================================


class TestCircuitBreakerDiagnostics:
    """Every circuit breaker state transition must emit a DiagnosticEvent."""

    def setup_method(self):
        self.breaker = SwarmCircuitBreaker(
            agent_name="test_agent",
            config=CircuitBreakerConfig(
                failure_threshold=2,
                recovery_timeout_ms=10_000.0,
                half_open_max_calls=2,
                consecutive_successes_to_close=1,
                max_isolation_strikes=2,
                isolation_timeout_ms=10_000.0,
            ),
        )

    def _flush_anomalies(self):
        diagnostics_engine._anomalies.clear()

    def test_closed_to_open_emits_event(self):
        self._flush_anomalies()
        self.breaker.record_failure()
        self.breaker.record_failure()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:open"]
        assert len(events) >= 1
        assert events[-1].payload.get("agent") == "test_agent"

    def test_half_open_to_closed_emits_event(self):
        self._flush_anomalies()
        # force into HALF_OPEN
        self.breaker._state = type(self.breaker._state).HALF_OPEN
        self.breaker._state_change_time_ms = time.monotonic_ns() / 1_000_000 - 100
        self.breaker.record_success()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:close"]
        assert len(events) >= 1

    def test_half_open_to_open_emits_event(self):
        self._flush_anomalies()
        self.breaker._state = type(self.breaker._state).HALF_OPEN
        self.breaker.record_failure()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:reopen"]
        assert len(events) >= 1

    def test_open_to_isolated_emits_event(self):
        self._flush_anomalies()
        self.breaker._state = type(self.breaker._state).OPEN
        self.breaker._total_open_count = 2
        self.breaker.record_failure()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:isolate"]
        assert len(events) >= 1

    def test_open_to_half_open_emits_event(self):
        self._flush_anomalies()
        self.breaker._state = type(self.breaker._state).OPEN
        self.breaker._state_change_time_ms = time.monotonic_ns() / 1_000_000 - 100_000
        self.breaker.allow_request()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:half_open"]
        assert len(events) >= 1

    def test_isolated_to_open_emits_event(self):
        self._flush_anomalies()
        self.breaker._state = type(self.breaker._state).ISOLATED
        self.breaker._state_change_time_ms = time.monotonic_ns() / 1_000_000 - 100_000
        self.breaker.allow_request()
        events = [e for e in diagnostics_engine._events if e.event_type == "circuit_breaker:auto_recover"]
        assert len(events) >= 1


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


class TestAnomalyEndpoint:
    """End-to-end tests for GET /api/observability/anomalies."""

    def _seed_anomalies(self, engine, count: int = 5):
        """Populate engine with test anomalies via run_detectors or direct injection."""
        from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
        from datetime import datetime, timezone, timedelta
        import uuid
        with engine._lock:
            for i in range(count):
                a = AnomalySignal(
                    anomaly_id=f"test-ano-{i}",
                    detector_name="test_detector",
                    anomaly_type=AnomalyType.DEADLOCK if i % 2 == 0 else AnomalyType.EVENT_STORM,
                    severity=Severity.CRITICAL if i == 0 else Severity.WARNING if i < 3 else Severity.INFO,
                    scope=f"test:scope-{i % 2}",
                    title=f"Test anomaly {i}",
                    description=f"Description for test anomaly {i}",
                    metric_value=float(i),
                    threshold=3.0,
                    evidence={"key": f"value_{i}"},
                    recommendation=f"Fix anomaly {i}",
                    correlation_id=f"corr-{i}",
                )
                engine._anomalies.append(a)

    def test_list_empty(self, client):
        resp = client.get("/api/observability/anomalies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["anomalies"] == []

    def test_list_with_anomalies(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp = client.get("/api/observability/anomalies")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 5
            assert len(data["anomalies"]) == 5
            assert data["returned"] == 5
            # Verify serialization fields
            first = data["anomalies"][0]
            assert "anomaly_id" in first
            assert "severity" in first
            assert "anomaly_type" in first
            assert "correlation_id" in first
            assert "created_at" in first
            assert "title" in first
            assert "description" in first
            assert "detector_name" in first
        finally:
            diagnostics_engine._anomalies.clear()

    def test_pagination_offset_limit(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 10)
        try:
            resp = client.get("/api/observability/anomalies?limit=3&offset=2")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 10
            assert len(data["anomalies"]) == 3
            assert data["offset"] == 2
            assert data["limit"] == 3
            assert data["returned"] == 3
        finally:
            diagnostics_engine._anomalies.clear()

    def test_filter_by_severity(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp = client.get("/api/observability/anomalies?severity=critical")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            for a in data["anomalies"]:
                assert a["severity"] == "critical"

            resp2 = client.get("/api/observability/anomalies?severity=warning")
            assert resp2.status_code == 200
            assert resp2.json()["total"] == 2
        finally:
            diagnostics_engine._anomalies.clear()

    def test_filter_by_type(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 4)
        try:
            resp = client.get("/api/observability/anomalies?anomaly_type=deadlock")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            for a in data["anomalies"]:
                assert a["anomaly_type"] == "deadlock"
        finally:
            diagnostics_engine._anomalies.clear()

    def test_filter_by_scope(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 4)
        try:
            resp = client.get("/api/observability/anomalies?scope=scope-0")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 2
            for a in data["anomalies"]:
                assert "scope-0" in a["scope"]
        finally:
            diagnostics_engine._anomalies.clear()

    def test_filter_by_detector(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 3)
        try:
            resp = client.get("/api/observability/anomalies?detector_name=test_detector")
            assert resp.status_code == 200
            assert resp.json()["total"] == 3

            resp2 = client.get("/api/observability/anomalies?detector_name=nonexistent")
            assert resp2.json()["total"] == 0
        finally:
            diagnostics_engine._anomalies.clear()

    def test_search_filter(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp = client.get("/api/observability/anomalies?search=anomaly+2")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert "anomaly 2" in data["anomalies"][0]["title"]
        finally:
            diagnostics_engine._anomalies.clear()

    def test_sort_asc_desc(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp_desc = client.get("/api/observability/anomalies?sort=desc")
            resp_asc = client.get("/api/observability/anomalies?sort=asc")
            assert resp_desc.status_code == 200
            assert resp_asc.status_code == 200
            ids_desc = [a["anomaly_id"] for a in resp_desc.json()["anomalies"]]
            ids_asc = [a["anomaly_id"] for a in resp_asc.json()["anomalies"]]
            assert ids_desc == list(reversed(ids_asc))
        finally:
            diagnostics_engine._anomalies.clear()

    def test_limit_clamped(self, client):
        resp = client.get("/api/observability/anomalies?limit=9999")
        assert resp.status_code == 422  # FastAPI validation rejects > 1000

    def test_get_single_anomaly(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 3)
        try:
            resp = client.get("/api/observability/anomalies/test-ano-1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["anomaly_id"] == "test-ano-1"
            assert data["severity"] == "warning"
            assert data["correlation_id"] == "corr-1"
        finally:
            diagnostics_engine._anomalies.clear()

    def test_get_single_anomaly_not_found(self, client):
        resp = client.get("/api/observability/anomalies/nonexistent")
        assert resp.status_code == 404

    def test_anomaly_metrics_empty(self, client):
        resp = client.get("/api/observability/anomalies/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["health_score"] == 100.0

    def test_anomaly_metrics_with_data(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp = client.get("/api/observability/anomalies/metrics")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 5
            assert "by_severity" in data
            assert "by_type" in data
            assert "by_detector" in data
            assert data["by_severity"]["critical"] == 1
            assert data["health_score"] < 100.0  # critical anomalies reduce score
        finally:
            diagnostics_engine._anomalies.clear()

    def test_export_csv(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 3)
        try:
            resp = client.get("/api/observability/anomalies/export?format=csv")
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "text/csv; charset=utf-8"
            assert "anomaly_id" in resp.text
            assert "test-ano-0" in resp.text
        finally:
            diagnostics_engine._anomalies.clear()

    def test_export_json(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 3)
        try:
            resp = client.get("/api/observability/anomalies/export?format=json")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 3
        finally:
            diagnostics_engine._anomalies.clear()

    def test_export_filtered(self, client):
        from app.swarm_diagnostics import diagnostics_engine
        self._seed_anomalies(diagnostics_engine, 5)
        try:
            resp = client.get("/api/observability/anomalies/export?severity=critical&format=csv")
            assert resp.status_code == 200
            assert resp.text.count("critical") == 1  # only one critical anomaly
        finally:
            diagnostics_engine._anomalies.clear()


# =============================================================================
# 6. Anomaly serialization
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


class TestAnomalyFiltering:
    """_filter_anomalies pure function unit tests."""

    def _make_anomalies(self):
        from datetime import datetime, timezone
        return [
            {
                "anomaly_id": "a-1",
                "severity": "critical",
                "scope": "student:abc",
                "detector_name": "deadlock_detector",
                "anomaly_type": "deadlock",
                "title": "Deadlock detected",
                "description": "A deadlock was detected in resource X",
                "created_at": "2026-05-27T10:00:00+00:00",
                "correlation_id": "corr-1",
            },
            {
                "anomaly_id": "a-2",
                "severity": "warning",
                "scope": "global",
                "detector_name": "event_storm_detector",
                "anomaly_type": "event_storm",
                "title": "Event storm",
                "description": "Too many events in short period",
                "created_at": "2026-05-27T10:05:00+00:00",
                "correlation_id": "corr-2",
            },
            {
                "anomaly_id": "a-3",
                "severity": "info",
                "scope": "student:xyz",
                "detector_name": "test_detector",
                "anomaly_type": "propagation_failure",
                "title": "Propagation issue",
                "description": "Event propagation failed",
                "created_at": "2026-05-27T10:10:00+00:00",
                "correlation_id": None,
            },
        ]

    def test_filter_by_severity(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(self._make_anomalies(), severity="critical")
        assert len(result) == 1
        assert result[0]["anomaly_id"] == "a-1"

    def test_filter_by_scope(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(self._make_anomalies(), scope="student")
        assert len(result) == 2

    def test_filter_by_detector_and_type(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(
            self._make_anomalies(),
            detector_name="deadlock_detector",
            anomaly_type="deadlock",
        )
        assert len(result) == 1
        assert result[0]["anomaly_id"] == "a-1"

    def test_filter_by_time_range(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(
            self._make_anomalies(),
            since="2026-05-27T10:03:00+00:00",
            until="2026-05-27T10:12:00+00:00",
        )
        assert len(result) == 2
        assert result[0]["anomaly_id"] == "a-2"
        assert result[1]["anomaly_id"] == "a-3"

    def test_search_title(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(self._make_anomalies(), search="deadlock")
        assert len(result) == 1

    def test_search_description(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(self._make_anomalies(), search="too many")
        assert len(result) == 1
        assert result[0]["anomaly_id"] == "a-2"

    def test_no_filters_returns_all(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(self._make_anomalies())
        assert len(result) == 3

    def test_all_filters_combined(self):
        from app.api.routes.observability import _filter_anomalies
        result = _filter_anomalies(
            self._make_anomalies(),
            severity="warning",
            scope="global",
            detector_name="event_storm_detector",
            anomaly_type="event_storm",
        )
        assert len(result) == 1
        assert result[0]["anomaly_id"] == "a-2"


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
