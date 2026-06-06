"""
Experiment isolation, reproducibility, and contamination tests.

Tests:
    - StateContamination: verify that running multiple experiments
      sequentially does NOT leak state between them.
    - TestFreshInstanceIsolation: verify that fresh ExperimentContext
      instances are fully independent.
    - TestResetProtocol: verify reset_all_global_state() works.
    - TestMetricsExporterReset: verify MetricsExporter.reset() clears all.
    - TestExperimentRegistry: register, query, compare, get_by_hash.
    - TestReproducibility: same inputs → same hash.
    - TestSnapshot: snapshot captures correct pre/post state.
"""

from __future__ import annotations

import json
import threading
from collections import Counter

import pytest

from app.core.consensus import VoteContext, VoteDecision
from app.core.trust import TrustSystem, get_trust_system, reset_trust_system
from app.experiment import (
    ExperimentContext,
    ExperimentRegistry,
    reset_all_global_state,
)
from app.experiment.context import ExperimentState, registry
from app.observability.consensus_metrics import ConsensusMetrics, metrics as global_metrics
from app.observability.metrics_exporter import MetricsExporter, exporter as global_exporter
from app.swarm_diagnostics import diagnostics_engine as global_diagnostics
from app.swarm_diagnostics.core import SwarmDiagnosticsEngine


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _contaminate_globals() -> None:
    """Deliberately contaminate every global singleton with dummy state."""
    ts = get_trust_system()
    ts.record_error("voter_a")

    global_metrics.total_runs = 99
    global_metrics.approvals = 50
    global_metrics.errors = 5
    global_metrics.record_rollback()

    global_exporter.inc_counter("test_contamination", 42)
    global_exporter.track_anomalies([{
        "anomaly_id": "contam-1",
        "severity": "critical",
        "anomaly_type": "test",
        "title": "contamination",
        "description": "deliberate",
        "detector_name": "test",
        "scope": "global",
    }])
    global_exporter.track_recovery(success=True)
    global_exporter.track_activation("ctx-contam", "test", "completed")

    global_diagnostics.make_event(
        event_type="test:contamination",
        source="test",
        payload={"msg": "contaminated"},
    )


_COUNTER = 0

def _fresh_experiment_state(experiment_id: str | None = None) -> ExperimentState:
    """Factory for a minimal ExperimentState."""
    global _COUNTER
    _COUNTER += 1
    eid = experiment_id or f"test-{_COUNTER}"
    return ExperimentState(
        experiment_id=eid,
        label="test",
        trust_system=TrustSystem(),
        consensus_metrics=ConsensusMetrics(),
        exporter=MetricsExporter(),
        diagnostics_engine=SwarmDiagnosticsEngine(),
        created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
    )


# ═══════════════════════════════════════════════════════════════════
# State Contamination Tests
# ═══════════════════════════════════════════════════════════════════

class TestStateContamination:
    """Verify that pre-existing global state does NOT leak into a fresh experiment."""

    def setup_method(self) -> None:
        reset_all_global_state()

    def test_fresh_experiment_trust_is_zero(self):
        """Fresh ExperimentContext trust should have zero records regardless of globals."""
        _contaminate_globals()
        ts = get_trust_system()
        assert len(ts.get_all_records()) > 0, "contamination should have added records"

        fresh = _fresh_experiment_state()
        assert len(fresh.trust_system.get_all_records()) == 0
        assert fresh.trust_system is not ts  # different objects

    def test_fresh_experiment_metrics_are_zero(self):
        _contaminate_globals()
        assert global_metrics.total_runs == 99

        fresh = _fresh_experiment_state()
        assert fresh.consensus_metrics.total_runs == 0
        assert fresh.consensus_metrics.approvals == 0
        assert fresh.consensus_metrics.errors == 0
        assert fresh.consensus_metrics.rollbacks == 0

    def test_fresh_experiment_exporter_is_zero(self):
        _contaminate_globals()
        assert global_exporter._custom_counters.get("test_contamination") == 42

        fresh = _fresh_experiment_state()
        assert fresh.exporter._custom_counters.get("test_contamination") is None
        assert fresh.exporter._anomaly_total_count == 0
        assert fresh.exporter._recovery_attempts == 0

    def test_fresh_experiment_diagnostics_is_zero(self):
        _contaminate_globals()
        assert len(global_diagnostics._events) > 0

        fresh = _fresh_experiment_state()
        assert len(fresh.diagnostics_engine._events) == 0
        assert len(fresh.diagnostics_engine._anomalies) == 0

    def test_two_experiments_do_not_contaminate_each_other(self):
        a = _fresh_experiment_state()
        b = _fresh_experiment_state()

        # Contaminate A only
        a.trust_system.record_error("voter_a")
        a.consensus_metrics.total_runs = 10
        a.exporter.inc_counter("a_only", 1)
        a.diagnostics_engine.make_event(event_type="test:a_only", source="test")

        # B should be pristine
        assert len(b.trust_system.get_all_records()) == 0
        assert b.consensus_metrics.total_runs == 0
        assert b.exporter._custom_counters.get("a_only") is None
        assert len(b.diagnostics_engine._events) == 0


# ═══════════════════════════════════════════════════════════════════
# Fresh Instance Isolation Tests
# ═══════════════════════════════════════════════════════════════════

class TestFreshInstanceIsolation:
    """Verify that ExperimentContext provides truly independent instances."""

    async def test_context_creates_fresh_instances(self):
        async with ExperimentContext(label="isolation-1") as exp:
            assert isinstance(exp.trust_system, TrustSystem)
            assert isinstance(exp.consensus_metrics, ConsensusMetrics)
            assert isinstance(exp.exporter, MetricsExporter)
            assert isinstance(exp.diagnostics_engine, SwarmDiagnosticsEngine)
            assert exp.trust_system is not get_trust_system()
            assert exp.consensus_metrics is not global_metrics
            assert exp.exporter is not global_exporter
            assert exp.diagnostics_engine is not global_diagnostics

    async def test_two_contexts_produce_different_instances(self):
        async with ExperimentContext(label="a") as a:
            async with ExperimentContext(label="b") as b:
                assert a.trust_system is not b.trust_system
                assert a.consensus_metrics is not b.consensus_metrics
                assert a.exporter is not b.exporter
                assert a.diagnostics_engine is not b.diagnostics_engine

    async def test_context_instances_are_independent(self):
        async with ExperimentContext(label="indep-a") as a:
            async with ExperimentContext(label="indep-b") as b:
                a.trust_system.record_error("voter_x")
                a.consensus_metrics.total_runs = 42
                a.exporter.inc_counter("indep", 7)
                a.diagnostics_engine.make_event(event_type="test:indep", source="test")

                assert len(b.trust_system.get_all_records()) == 0
                assert b.consensus_metrics.total_runs == 0
                assert b.exporter._custom_counters.get("indep") is None
                assert len(b.diagnostics_engine._events) == 0

    async def test_experiment_id_is_unique(self):
        ids = set()
        for _ in range(10):
            async with ExperimentContext() as exp:
                ids.add(exp.experiment_id)
        assert len(ids) == 10

    async def test_experiment_id_uuid_format(self):
        async with ExperimentContext() as exp:
            import uuid
            parsed = uuid.UUID(exp.experiment_id)
            assert str(parsed) == exp.experiment_id


# ═══════════════════════════════════════════════════════════════════
# Reset Protocol Tests
# ═══════════════════════════════════════════════════════════════════

class TestResetProtocol:
    """Verify reset_all_global_state() clears every global singleton."""

    def setup_method(self) -> None:
        reset_all_global_state()

    def _verify_empty(self):
        assert len(get_trust_system().get_all_records()) == 0
        assert global_metrics.total_runs == 0
        assert global_metrics.approvals == 0
        assert global_metrics.errors == 0
        assert len(global_exporter._custom_counters) == 0
        assert global_exporter._anomaly_total_count == 0
        assert global_exporter._recovery_attempts == 0
        assert len(global_diagnostics._events) == 0
        assert len(global_diagnostics._anomalies) == 0

    def test_reset_clears_everything(self):
        _contaminate_globals()
        # Verify contamination is real
        assert len(get_trust_system().get_all_records()) > 0
        assert global_metrics.total_runs > 0

        results = reset_all_global_state()
        assert all(results.values()), f"Some resets failed: {results}"
        self._verify_empty()

    def test_consecutive_resets_are_safe(self):
        for _ in range(5):
            results = reset_all_global_state()
            assert all(results.values())
            self._verify_empty()

    def test_reset_after_no_contamination_is_safe(self):
        results = reset_all_global_state()
        assert all(results.values())
        self._verify_empty()

    def test_reset_after_partial_contamination(self):
        get_trust_system().record_error("voter_a")
        global_metrics.record_rollback()
        global_exporter.track_activation("ctx-1", "phase-1", "active")

        results = reset_all_global_state()
        assert all(results.values())
        self._verify_empty()

    async def test_reset_context_manager(self):
        _contaminate_globals()
        assert len(global_diagnostics._events) > 0

        async with ExperimentContext(label="reset-test", reset_globals=True):
            # Globals were reset on enter
            assert len(global_diagnostics._events) == 0

        # Globals are reset again on exit
        assert len(global_diagnostics._events) == 0

    def test_reset_returns_status_dict(self):
        results = reset_all_global_state()
        assert isinstance(results, dict)
        assert "trust_system" in results
        assert "consensus_metrics" in results
        assert "diagnostics_engine" in results
        assert "metrics_exporter" in results
        assert "shared_memory_store" in results


# ═══════════════════════════════════════════════════════════════════
# MetricsExporter Reset Tests
# ═══════════════════════════════════════════════════════════════════

class TestMetricsExporterReset:
    """Verify MetricsExporter.reset() clears all accumulators specifically."""

    def test_reset_clears_custom_counters(self):
        exp = MetricsExporter()
        exp.inc_counter("a", 10)
        exp.inc_counter("b", 20)
        exp.reset()
        assert exp._custom_counters == {}

    def test_reset_clears_gauges(self):
        exp = MetricsExporter()
        exp.set_gauge("cpu", 0.5)
        exp.reset()
        assert exp._custom_gauges == {}

    def test_reset_clears_histograms(self):
        exp = MetricsExporter()
        exp.observe_histogram("latency", 100)
        exp.observe_histogram("latency", 200)
        exp.reset()
        assert all(len(v) == 0 for v in exp._custom_histograms.values())

    def test_reset_clears_activations(self):
        exp = MetricsExporter()
        exp.track_activation("ctx-1", "phase-1", "completed")
        assert len(exp._activation_history) == 1
        exp.reset()
        assert len(exp._activations) == 0
        assert len(exp._activation_history) == 0

    def test_reset_clears_sessions(self):
        exp = MetricsExporter()
        exp.track_session("sess-1", "start")
        exp.track_session("sess-1", "end")
        assert len(exp._session_history) == 1
        exp.reset()
        assert len(exp._sessions) == 0
        assert len(exp._session_history) == 0

    def test_reset_clears_resilience_state(self):
        exp = MetricsExporter()
        exp.track_circuit_breaker("cb-1", "open")
        exp.track_retry("op-1")
        exp.track_recovery(success=True)
        exp.reset()
        assert exp._circuit_breaker_states == {}
        assert exp._retry_counts == {}
        assert exp._recovery_attempts == 0
        assert exp._recovery_successes == 0

    def test_reset_clears_propagation_chains(self):
        exp = MetricsExporter()
        exp.track_propagation_hop("chain-1", 1, "a", "b", 10.0, "ok")
        exp.reset()
        assert exp._propagation_chains == {}
        assert exp._propagation_hops == []

    def test_reset_clears_anomaly_buffer(self):
        exp = MetricsExporter()
        exp.track_anomalies([{
            "anomaly_id": "a1", "severity": "warning",
            "anomaly_type": "test", "title": "t", "description": "d",
            "detector_name": "test", "scope": "global",
        }])
        exp.reset()
        assert exp._anomaly_total_count == 0
        assert exp._anomaly_buffer == []
        assert exp._anomaly_severity_counts == {}
        assert exp._anomaly_type_counts == {}

    def test_reset_clears_experiment_metrics(self):
        exp = MetricsExporter()
        exp.track_experiment("group-a", "accuracy", 0.95)
        exp.reset()
        assert exp._experiment_metrics == {}
        assert exp._experiment_groups == {}

    def test_reset_restarts_uptime_timer(self):
        exp = MetricsExporter()
        import time
        time.sleep(0.01)
        old_start = exp._start_time
        exp.reset()
        assert exp._start_time > old_start

    def test_produces_empty_snapshot_after_reset(self):
        exp = MetricsExporter()
        exp.inc_counter("should_be_gone", 999)
        exp.reset()
        snap = exp.json_snapshot()
        assert snap["counters"] == {}
        assert snap["resilience"]["recovery_attempts"] == 0
        assert snap["anomalies"]["total_count"] == 0
        assert snap["activations"]["active_count"] == 0


# ═══════════════════════════════════════════════════════════════════
# Experiment Registry Tests
# ═══════════════════════════════════════════════════════════════════

class TestExperimentRegistry:
    """Verify ExperimentRegistry correctly tracks experiments."""

    def setup_method(self) -> None:
        registry.reset()

    def test_register_and_get(self):
        state = _fresh_experiment_state()
        registry.register(state)
        assert registry.get(state.experiment_id) is state

    def test_register_and_get_snapshot(self):
        state = _fresh_experiment_state()
        snap = state.to_snapshot()
        registry.register(state)
        registry.archive(snap)
        retrieved = registry.get_snapshot(state.experiment_id)
        assert retrieved is not None
        assert retrieved.hash == snap.hash
        assert retrieved.experiment_id == state.experiment_id

    def test_unregister_removes_state(self):
        state = _fresh_experiment_state()
        registry.register(state)
        assert registry.get(state.experiment_id) is state
        registry.unregister(state.experiment_id)
        assert registry.get(state.experiment_id) is None

    def test_list_experiments(self):
        state = _fresh_experiment_state()
        registry.register(state)
        lst = registry.list_experiments()
        assert any(e["experiment_id"] == state.experiment_id for e in lst)

    def test_get_by_hash(self):
        state = _fresh_experiment_state()
        snap = state.to_snapshot()
        registry.archive(snap)

        # Same initial state → same hash
        state2 = _fresh_experiment_state()
        snap2 = state2.to_snapshot()
        registry.archive(snap2)

        matches = registry.get_by_hash(snap.hash)
        assert len(matches) >= 2
        assert all(m.hash == snap.hash for m in matches)

    def test_compare_identical_experiments(self):
        state_a = _fresh_experiment_state()
        state_b = _fresh_experiment_state()
        snap_a = state_a.to_snapshot()
        snap_b = state_b.to_snapshot()
        registry.archive(snap_a)
        registry.archive(snap_b)

        comp = registry.compare(snap_a.experiment_id, snap_b.experiment_id)
        assert comp["same_hash"] is True
        assert comp["trust_system_equal"] is True
        assert comp["consensus_metrics_equal"] is True

    def test_compare_different_experiments(self):
        state_a = _fresh_experiment_state()
        state_b = _fresh_experiment_state()

        # Contaminate B
        state_b.trust_system.record_error("voter_x")
        state_b.consensus_metrics.total_runs = 1

        snap_a = state_a.to_snapshot()
        snap_b = state_b.to_snapshot()
        registry.archive(snap_a)
        registry.archive(snap_b)

        comp = registry.compare(snap_a.experiment_id, snap_b.experiment_id)
        assert comp["same_hash"] is False
        assert comp["trust_system_equal"] is False
        assert comp["consensus_metrics_equal"] is False

    def test_registry_reset_clears_everything(self):
        state = _fresh_experiment_state()
        registry.register(state)
        snap = state.to_snapshot()
        registry.archive(snap)
        registry.reset()
        assert registry.list_experiments() == []
        assert registry.get_snapshot(state.experiment_id) is None

    def test_registry_handles_missing_experiment(self):
        assert registry.get("nonexistent") is None
        assert registry.get_snapshot("nonexistent") is None

    def test_registry_max_snapshots(self):
        for i in range(600):
            s = _fresh_experiment_state()
            s.experiment_id = f"eid-{i}"
            snap = s.to_snapshot()
            snap.experiment_id = f"eid-{i}"
            registry.archive(snap)
        assert len(registry._snapshots) <= 500


# ═══════════════════════════════════════════════════════════════════
# Reproducibility Tests
# ═══════════════════════════════════════════════════════════════════

class TestReproducibility:
    """Verify that same initial state produces same experiment hash."""

    def test_same_state_same_hash(self):
        snap_a = _fresh_experiment_state().to_snapshot()
        snap_b = _fresh_experiment_state().to_snapshot()
        assert snap_a.hash == snap_b.hash

    def test_different_state_different_hash(self):
        a = _fresh_experiment_state()
        b = _fresh_experiment_state()
        b.trust_system.record_error("voter_x")
        assert a.to_snapshot().hash != b.to_snapshot().hash

    def test_hash_is_deterministic(self):
        snap = _fresh_experiment_state().to_snapshot()
        for _ in range(10):
            assert snap.hash == _fresh_experiment_state().to_snapshot().hash

    def test_hash_changes_when_metrics_change(self):
        a = _fresh_experiment_state()
        b = _fresh_experiment_state()
        b.consensus_metrics.total_runs = 1
        assert a.to_snapshot().hash != b.to_snapshot().hash


# ═══════════════════════════════════════════════════════════════════
# Snapshot Tests
# ═══════════════════════════════════════════════════════════════════

class TestSnapshot:
    """Verify ExperimentSnapshot captures correct pre/post state."""

    def test_snapshot_includes_all_fields(self):
        snap = _fresh_experiment_state().to_snapshot()
        d = snap.to_dict()
        required = [
            "experiment_id", "label", "timestamp",
            "trust_system", "consensus_metrics",
            "diagnostics_events_count", "diagnostics_anomalies_count",
            "exporter_counters", "exporter_anomaly_count",
            "exporter_recovery_attempts", "hash",
        ]
        for field in required:
            assert field in d, f"Missing field: {field}"

    def test_snapshot_is_serializable(self):
        snap = _fresh_experiment_state().to_snapshot()
        raw = json.dumps(snap.to_dict(), default=str)
        assert isinstance(raw, str)
        parsed = json.loads(raw)
        assert parsed["experiment_id"] == snap.experiment_id

    def test_post_experiment_snapshot_reflects_changes(self):
        state = _fresh_experiment_state()
        state.trust_system.record_error("voter_a")
        state.consensus_metrics.total_runs = 5
        snap = state.to_snapshot()

        assert "voter_a" in snap.trust_system
        assert snap.consensus_metrics["total_runs"] == 5

    def test_pre_and_post_snapshots_differ(self):
        state = _fresh_experiment_state()
        pre = state.to_snapshot()
        state.trust_system.record_error("voter_a")
        post = state.to_snapshot()
        assert pre.hash != post.hash

    def test_empty_experiment_hash_is_stable(self):
        h1 = _fresh_experiment_state().to_snapshot().hash
        h2 = _fresh_experiment_state().to_snapshot().hash
        assert h1 == h2


# ═══════════════════════════════════════════════════════════════════
# Thread safety (basic)
# ═══════════════════════════════════════════════════════════════════

class TestThreadSafety:
    """Basic thread-safety verification for fresh instances."""

    def test_concurrent_trust_records_are_independent(self):
        state_a = _fresh_experiment_state()
        state_b = _fresh_experiment_state()

        errors: list[Exception] = []

        def contaminate_a():
            try:
                for i in range(100):
                    state_a.trust_system.record_error(f"voter_{i}")
            except Exception as e:
                errors.append(e)

        def contaminate_b():
            try:
                for i in range(100):
                    state_b.trust_system.record_error(f"voter_{i}")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=contaminate_a)
        t2 = threading.Thread(target=contaminate_b)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        assert len(state_a.trust_system.get_all_records()) == 100
        assert len(state_b.trust_system.get_all_records()) == 100
