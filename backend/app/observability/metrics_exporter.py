"""
Metrics Exporter — central registry that wraps all in-process counters
and exposes them in Prometheus text format and JSON snapshots.

Sources integrated:
    - ConsensusMetrics (observability/consensus_metrics.py)
    - SwarmActivationMetrics (swarm/activation_metrics.py)
    - SwarmMetricsCollector (swarm_diagnostics/pipeline/metrics.py)
    - EventLineageTracker (swarm_diagnostics/pipeline/lineage.py)
    - SwarmDiagnosticsEngine (swarm_diagnostics/core.py)
    - QueryCounter (db/query_counter.py)
    - DecisionTimeline (observability/swarm_diagnostics.py)
    - PropagationTTLManager (events/propagation_ttl.py)
    - CircuitBreaker (events/retry.py)

Usage:
    exporter = MetricsExporter()
    prometheus_text = exporter.prometheus()
    json_snapshot = exporter.json_snapshot()
"""
from __future__ import annotations

import functools
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.observability.consensus_metrics import metrics as consensus_metrics


class MetricsExporter:
    """Thread-safe registry that aggregates all in-process metrics
    and produces Prometheus-text / JSON-snapshot output."""

    def __init__(self):
        self._lock = threading.Lock()
        self._custom_gauges: dict[str, float] = {}
        self._custom_counters: dict[str, int] = {}
        self._custom_histograms: dict[str, list[float]] = defaultdict(list)
        self._max_histogram_samples = 500
        self._start_time = time.time()

        # Activation lifecycle tracking
        self._activations: dict[str, dict] = {}  # context_key -> state
        self._activation_history: list[dict] = []
        self._max_activation_history = 1000

        # Session lifecycle tracking  
        self._sessions: dict[str, dict] = {}
        self._session_history: list[dict] = []
        self._max_session_history = 1000

        # Resilience tracking
        self._circuit_breaker_states: dict[str, str] = {}
        self._retry_counts: dict[str, int] = defaultdict(int)
        self._recovery_attempts: int = 0
        self._recovery_successes: int = 0

        # Propagation tracking
        self._propagation_chains: dict[str, dict] = {}
        self._propagation_hops: list[dict] = []
        self._max_propagation_hops = 2000

        # Anomaly tracking for snapshot
        self._anomaly_buffer: list[dict] = []
        self._max_anomaly_buffer = 100
        self._anomaly_severity_counts: dict[str, int] = defaultdict(int)
        self._anomaly_type_counts: dict[str, int] = defaultdict(int)
        self._anomaly_total_count: int = 0

        # Experimental / A-B metrics
        self._experiment_groups: dict[str, str] = {}
        self._experiment_metrics: dict[str, dict] = defaultdict(
            lambda: {"count": 0, "total": 0.0, "min": float("inf"), "max": 0.0}
        )

        # Sandbox metrics (registered lazily)
        self._sandbox_collector = None

    # ── Gauge / Counter / Histogram API ──────────────────────────

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._custom_gauges[name] = value

    def inc_counter(self, name: str, delta: int = 1) -> None:
        with self._lock:
            self._custom_counters[name] = self._custom_counters.get(name, 0) + delta

    def observe_histogram(self, name: str, value: float) -> None:
        with self._lock:
            hist = self._custom_histograms[name]
            hist.append(value)
            if len(hist) > self._max_histogram_samples:
                self._custom_histograms[name] = hist[-self._max_histogram_samples:]

    # ── Activation lifecycle ──────────────────────────────────────

    def track_activation(
        self, context_key: str, phase: str, status: str,
        duration_ms: float = 0.0, error: str | None = None,
    ) -> None:
        with self._lock:
            now = time.time()
            if context_key not in self._activations:
                self._activations[context_key] = {
                    "context_key": context_key,
                    "started_at": now,
                    "phases": [],
                    "current_phase": None,
                    "status": "active",
                    "errors": [],
                }
            entry = self._activations[context_key]
            entry["current_phase"] = phase
            entry["phases"].append({
                "phase": phase,
                "status": status,
                "duration_ms": duration_ms,
                "timestamp": now,
            })
            if status in ("completed", "failed"):
                entry["status"] = status
                entry["completed_at"] = now
                self._activation_history.append(dict(entry))
                if len(self._activation_history) > self._max_activation_history:
                    self._activation_history = self._activation_history[-self._max_activation_history:]
                del self._activations[context_key]
            if error:
                entry["errors"].append(error)

    # ── Session lifecycle ─────────────────────────────────────────

    def track_session(
        self, session_id: str, event: str,
        student_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        with self._lock:
            now = time.time()
            if event == "start":
                self._sessions[session_id] = {
                    "session_id": session_id,
                    "student_id": student_id,
                    "started_at": now,
                    "events": [{"event": "start", "timestamp": now}],
                    "status": "active",
                }
            elif session_id in self._sessions:
                entry = self._sessions[session_id]
                entry["events"].append({"event": event, "timestamp": now, **(metadata or {})})
                if event == "end":
                    entry["status"] = "completed"
                    entry["completed_at"] = now
                    self._session_history.append(dict(entry))
                    if len(self._session_history) > self._max_session_history:
                        self._session_history = self._session_history[-self._max_session_history:]
                    del self._sessions[session_id]

    # ── Resilience tracking ───────────────────────────────────────

    def track_circuit_breaker(self, name: str, state: str) -> None:
        with self._lock:
            self._circuit_breaker_states[name] = state

    def track_retry(self, operation: str) -> None:
        with self._lock:
            self._retry_counts[operation] += 1

    def track_recovery(self, success: bool) -> None:
        with self._lock:
            self._recovery_attempts += 1
            if success:
                self._recovery_successes += 1

    # ── Propagation tracking ──────────────────────────────────────

    def track_propagation_hop(
        self, chain_id: str, hop: int, source: str, target: str,
        duration_ms: float, status: str,
    ) -> None:
        with self._lock:
            if chain_id not in self._propagation_chains:
                self._propagation_chains[chain_id] = {
                    "chain_id": chain_id, "hops": [], "status": "active",
                }
            chain = self._propagation_chains[chain_id]
            chain["hops"].append({
                "hop": hop, "source": source, "target": target,
                "duration_ms": duration_ms, "status": status,
            })
            chain["status"] = status
            self._propagation_hops.append({
                "chain_id": chain_id, "hop": hop,
                "source": source, "target": target,
                "duration_ms": duration_ms, "status": status,
            })
            if len(self._propagation_hops) > self._max_propagation_hops:
                self._propagation_hops = self._propagation_hops[-self._max_propagation_hops:]

    # ── Anomaly tracking ──────────────────────────────────────────

    def track_anomalies(self, signals: list[dict]) -> None:
        """Store anomaly signals for the next JSON snapshot."""
        with self._lock:
            self._anomaly_total_count += len(signals)
            for s in signals:
                sev = s.get("severity", "info")
                atype = s.get("anomaly_type", "unknown")
                self._anomaly_severity_counts[sev] += 1
                self._anomaly_type_counts[atype] += 1
            self._anomaly_buffer.extend(signals)
            if len(self._anomaly_buffer) > self._max_anomaly_buffer:
                self._anomaly_buffer = self._anomaly_buffer[-self._max_anomaly_buffer:]

    # ── Experimental metrics ──────────────────────────────────────

    def track_experiment(
        self, group: str, metric_name: str, value: float,
    ) -> None:
        with self._lock:
            entry = self._experiment_metrics[f"{group}:{metric_name}"]
            entry["count"] += 1
            entry["total"] += value
            entry["min"] = min(entry["min"], value)
            entry["max"] = max(entry["max"], value)

    def reset(self) -> None:
        """Reset ALL internal state to initial values.

        Full destructive reset — all counters, histograms, activations,
        sessions, resilience state, propagation chains, and anomaly
        buffers are cleared.  Use for experiment isolation.
        """
        with self._lock:
            self._custom_gauges.clear()
            self._custom_counters.clear()
            self._custom_histograms.clear()
            self._activations.clear()
            self._activation_history.clear()
            self._sessions.clear()
            self._session_history.clear()
            self._circuit_breaker_states.clear()
            self._retry_counts.clear()
            self._recovery_attempts = 0
            self._recovery_successes = 0
            self._propagation_chains.clear()
            self._propagation_hops.clear()
            self._anomaly_buffer.clear()
            self._anomaly_severity_counts.clear()
            self._anomaly_type_counts.clear()
            self._anomaly_total_count = 0
            self._experiment_groups.clear()
            self._experiment_metrics.clear()
            self._start_time = time.time()

    def register_sandbox(self, collector) -> None:
        """Register a sandbox metrics collector callable.

        The collector must be a callable (or have a .collect() method)
        that returns a dict with sandbox execution/security/Docker stats.
        """
        self._sandbox_collector = collector

    # ── Snapshots ─────────────────────────────────────────────────

    def json_snapshot(self) -> dict[str, Any]:
        with self._lock:
            consensus = consensus_metrics.get_snapshot()

            active_activations = list(self._activations.values())
            active_sessions = list(self._sessions.values())

            uptime = time.time() - self._start_time

            hist_summary = {}
            for name, vals in self._custom_histograms.items():
                if vals:
                    hist_summary[name] = {
                        "count": len(vals),
                        "min": round(min(vals), 2),
                        "max": round(max(vals), 2),
                        "avg": round(sum(vals) / len(vals), 2),
                    }

            experiment_summary = {}
            for key, entry in self._experiment_metrics.items():
                experiment_summary[key] = {
                    "count": entry["count"],
                    "avg": round(entry["total"] / entry["count"], 2) if entry["count"] else 0,
                    "min": round(entry["min"], 2) if entry["min"] != float("inf") else 0,
                    "max": round(entry["max"], 2),
                }

            return {
                "uptime_seconds": round(uptime, 1),
                "timestamp": time.time(),
                "consensus": consensus,
                "counters": dict(self._custom_counters),
                "gauges": dict(self._custom_gauges),
                "histograms": hist_summary,
                "activations": {
                    "active_count": len(active_activations),
                    "active": active_activations,
                    "history_count": len(self._activation_history),
                },
                "sessions": {
                    "active_count": len(active_sessions),
                    "active": active_sessions,
                    "history_count": len(self._session_history),
                },
                "resilience": {
                    "circuit_breakers": dict(self._circuit_breaker_states),
                    "retry_counts": dict(self._retry_counts),
                    "recovery_attempts": self._recovery_attempts,
                    "recovery_successes": self._recovery_successes,
                    "recovery_rate": round(
                        self._recovery_successes / self._recovery_attempts, 4
                    ) if self._recovery_attempts else 1.0,
                },
                "propagation": {
                    "active_chains": len(self._propagation_chains),
                    "total_hops": len(self._propagation_hops),
                    "chains": dict(self._propagation_chains),
                },
                "anomalies": {
                    "active_count": sum(self._anomaly_severity_counts.values()),
                    "total_count": self._anomaly_total_count,
                    "by_severity": dict(self._anomaly_severity_counts),
                    "by_type": dict(self._anomaly_type_counts),
                    "latest": list(self._anomaly_buffer),
                },
                "experiments": experiment_summary,
                "sandbox": self._sandbox_snapshot(),
            }

    def _sandbox_snapshot(self) -> dict[str, Any]:
        if not self._sandbox_collector:
            return {"status": "unregistered"}
        try:
            collector = self._sandbox_collector
            if callable(collector):
                return collector()
            if hasattr(collector, "collect"):
                return collector.collect()
        except Exception:
            return {"status": "error"}
        return {"status": "unregistered"}

    def prometheus(self) -> str:
        data = self.json_snapshot()
        lines = [
            '# HELP swarm_uptime_seconds System uptime',
            '# TYPE swarm_uptime_seconds gauge',
            f'swarm_uptime_seconds {data["uptime_seconds"]}',
            '',
            '# HELP swarm_consensus_total Total consensus runs',
            '# TYPE swarm_consensus_total counter',
            f'swarm_consensus_total {data["consensus"]["total_runs"]}',
            f'swarm_consensus_approvals_total {data["consensus"]["approvals"]}',
            f'swarm_consensus_rejections_total {data["consensus"]["rejections"]}',
            f'swarm_consensus_abstentions_total {data["consensus"]["abstentions"]}',
            f'swarm_consensus_disagreements_total {data["consensus"]["disagreements"]}',
            f'swarm_consensus_errors_total {data["consensus"]["errors"]}',
            f'swarm_consensus_rollbacks_total {data["consensus"]["rollbacks"]}',
            '',
            '# HELP swarm_consensus_latency_ms Consensus latency',
            '# TYPE swarm_consensus_latency_ms gauge',
            f'swarm_consensus_avg_latency_ms {data["consensus"]["avg_latency_ms"]}',
            f'swarm_consensus_min_latency_ms {data["consensus"]["min_latency_ms"]}',
            f'swarm_consensus_max_latency_ms {data["consensus"]["max_latency_ms"]}',
            '',
            '# HELP swarm_activations_active Current active activations',
            '# TYPE swarm_activations_active gauge',
            f'swarm_activations_active {data["activations"]["active_count"]}',
            f'swarm_activations_history_total {data["activations"]["history_count"]}',
            '',
            '# HELP swarm_sessions_active Current active sessions',
            '# TYPE swarm_sessions_active gauge',
            f'swarm_sessions_active {data["sessions"]["active_count"]}',
            f'swarm_sessions_history_total {data["sessions"]["history_count"]}',
            '',
            '# HELP swarm_resilience_recovery_rate Recovery success rate',
            '# TYPE swarm_resilience_recovery_rate gauge',
            f'swarm_resilience_recovery_rate {data["resilience"]["recovery_rate"]}',
            f'swarm_resilience_recovery_attempts_total {data["resilience"]["recovery_attempts"]}',
            f'swarm_resilience_recovery_successes_total {data["resilience"]["recovery_successes"]}',
            '',
            '# HELP swarm_propagation_active_chains Active propagation chains',
            '# TYPE swarm_propagation_active_chains gauge',
            f'swarm_propagation_active_chains {data["propagation"]["active_chains"]}',
            f'swarm_propagation_total_hops {data["propagation"]["total_hops"]}',
        ]
        for name, value in data["counters"].items():
            safe = name.replace(" ", "_").replace(".", "_")
            lines.append(f'# HELP swarm_{safe}_total Custom counter')
            lines.append('# TYPE swarm_{}_total counter'.format(safe))
            lines.append(f'swarm_{safe}_total {value}')
        for name, value in data["gauges"].items():
            safe = name.replace(" ", "_").replace(".", "_")
            lines.append(f'# HELP swarm_{safe} Custom gauge')
            lines.append(f'# TYPE swarm_{safe} gauge')
            lines.append(f'swarm_{safe} {value}')
        for name, h in data["histograms"].items():
            safe = name.replace(" ", "_").replace(".", "_")
            lines.append(f'# HELP swarm_{safe}_ms Histogram bucket')
            lines.append(f'# TYPE swarm_{safe}_ms histogram')
            lines.append(f'swarm_{safe}_ms_count {h["count"]}')
            lines.append(f'swarm_{safe}_ms_sum {h["avg"] * h["count"]}')
        # Anomaly metrics
        anomalies = data.get("anomalies", {})
        lines.append('')
        lines.append('# HELP swarm_anomalies_total Total anomaly signals')
        lines.append('# TYPE swarm_anomalies_total counter')
        lines.append(f'swarm_anomalies_total {anomalies.get("total_count", 0)}')
        lines.append(f'swarm_anomalies_active {anomalies.get("active_count", 0)}')
        for sev, count in anomalies.get("by_severity", {}).items():
            lines.append(f'swarm_anomalies_severity_total{{severity="{sev}"}} {count}')
        for atype, count in anomalies.get("by_type", {}).items():
            lines.append(f'swarm_anomalies_type_total{{type="{atype}"}} {count}')
        # Sandbox metrics
        sandbox = data.get("sandbox", {})
        if sandbox.get("status") == "active":
            execs = sandbox.get("executions", {})
            lines.append('')
            lines.append('# HELP sandbox_executions_total Total code executions')
            lines.append('# TYPE sandbox_executions_total counter')
            lines.append(f'sandbox_executions_total {execs.get("total", 0)}')
            lines.append(f'sandbox_docker_executions_total {execs.get("docker", 0)}')
            lines.append(f'sandbox_fallback_executions_total {execs.get("fallback", 0)}')
            lines.append(f'sandbox_avg_execution_time_ms {execs.get("avg_time_ms", 0)}')
            lines.append(f'sandbox_p95_execution_time_ms {execs.get("p95_time_ms", 0)}')
            errors = sandbox.get("errors", {})
            lines.append(f'sandbox_security_violations_total {errors.get("security_violations", 0)}')
            lines.append(f'sandbox_timeouts_total {errors.get("timeouts", 0)}')
            lines.append(f'sandbox_memory_exceeded_total {errors.get("memory_exceeded", 0)}')
            lines.append(f'sandbox_execution_errors_total {errors.get("execution_errors", 0)}')
            security = sandbox.get("security", {})
            lines.append(f'sandbox_security_total_violations {security.get("total_violations", 0)}')
            docker = sandbox.get("docker", {})
            lines.append(f'sandbox_docker_available {int(docker.get("available", False))}')
            lines.append(f'sandbox_docker_active_containers {docker.get("active_containers", 0)}')
        for vname, vstats in data["consensus"].get("voter_stats", {}).items():
            safe_v = vname.replace(" ", "_")
            lines.append(f'voter_votes_total{{voter="{safe_v}"}} {vstats["votes"]}')
            lines.append(f'voter_avg_latency_ms{{voter="{safe_v}"}} {vstats["avg_latency_ms"]}')
        lines.append("")
        return "\n".join(lines)


# Module-level singleton
exporter: MetricsExporter = MetricsExporter()
