"""
MetricsExporter reset tests.

TestMetricsExporterReset: verify MetricsExporter.reset() clears all
accumulators. Extracted from the broader experiment-isolation suite
when ADR-0017 (Fase 4+5, fusionadas) retiró app/experiment/* — el
resto de las clases de este archivo dependían de ExperimentContext,
ExperimentState y TrustSystem, todos parte del clúster retirado.
"""

from __future__ import annotations

from app.observability.metrics_exporter import MetricsExporter


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


