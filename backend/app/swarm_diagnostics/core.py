"""
SwarmDiagnosticsEngine — Central orchestrator for swarm observability.

Owns the event stream, coordinates all detectors, manages the metrics
pipeline, and produces health snapshots. Integrates with:
    - ConsensusEngine (vote/consensus events)
    - SharedMemoryStore (memory operations)
    - UnitOfWork (outbox events)
    - Tracing (trace_id propagation)
    - LangGraph (agent coordination events)
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.detectors.propagation import PropagationFailureDetector
from app.swarm_diagnostics.detectors.conflict import ConflictAnalyzer
from app.swarm_diagnostics.detectors.anomaly import BehaviorAnomalyDetector
from app.swarm_diagnostics.detectors.loops import DelegationLoopDetector
from app.swarm_diagnostics.detectors.retry_storm import RetryStormDetector
from app.swarm_diagnostics.detectors.deadlock import DeadlockDetector
from app.swarm_diagnostics.detectors.staleness import StaleMemoryMonitor
from app.swarm_diagnostics.detectors.divergence import AgentDivergenceDetector
from app.swarm_diagnostics.detectors.event_storm import EventStormDetector
from app.swarm_diagnostics.detectors.sync import SyncDelayMonitor
from app.swarm_diagnostics.detectors.propagation_storm import PropagationStormDetector
from app.swarm_diagnostics.detectors.recursive_amplification import RecursiveAmplificationDetector
from app.swarm_diagnostics.detectors.dag_traversal import DAGTraversalPitfallDetector
from app.swarm_diagnostics.detectors.consensus_timeout import (
    HungConsensusDetector,
    CascadingDelayDetector,
    QuorumInstabilityDetector,
)
from app.swarm_diagnostics.detectors.circuit_breaker import (
    CircuitBreakerRetryStormDetector,
    CascadingFailureDetector,
    RecoveryInstabilityDetector,
)
from app.swarm_diagnostics.detectors.degraded_agent import DegradedAgentDetector
from app.swarm_diagnostics.detectors.hallucination import HallucinationDetector
from app.swarm_diagnostics.detectors.slow_agent import SlowAgentDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.models.health_snapshot import HealthSnapshot
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector
from app.swarm_diagnostics.pipeline.lineage import EventLineageTracker


class SwarmDiagnosticsEngine:
    """Thread-safe central diagnostics engine.

    Usage:
        engine = SwarmDiagnosticsEngine()
        engine.record_event(event)
        signals = engine.run_detectors(scope="student:stu-1")
        report = engine.health_report(scope="student:stu-1")
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._events: list[DiagnosticEvent] = []
        self._anomalies: list[AnomalySignal] = []
        self._max_events = 10_000
        self._max_anomalies = 1_000

        self.metrics = SwarmMetricsCollector()
        self.lineage = EventLineageTracker()

        self._detectors: dict[str, BaseDetector] = {}
        self._register_default_detectors()

    def _register_default_detectors(self) -> None:
        detectors: list[BaseDetector] = [
            PropagationFailureDetector(),
            ConflictAnalyzer(),
            BehaviorAnomalyDetector(),
            DelegationLoopDetector(),
            RetryStormDetector(),
            DeadlockDetector(),
            StaleMemoryMonitor(),
            AgentDivergenceDetector(),
            EventStormDetector(),
            SyncDelayMonitor(),
            PropagationStormDetector(),
            RecursiveAmplificationDetector(),
            DAGTraversalPitfallDetector(),
            HungConsensusDetector(),
            CascadingDelayDetector(),
            QuorumInstabilityDetector(),
            CircuitBreakerRetryStormDetector(),
            CascadingFailureDetector(),
            RecoveryInstabilityDetector(),
            DegradedAgentDetector(),
            HallucinationDetector(),
            SlowAgentDetector(),
        ]
        for d in detectors:
            self._detectors[d.name] = d

    # ── Event ingestion ──────────────────────────────────────────

    def record_event(self, event: DiagnosticEvent) -> None:
        """Ingest a diagnostic event into the stream."""
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]
        self.metrics.record_event(event)
        self.lineage.record(event)

    def make_event(
        self,
        event_type: str,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        trace_id: str | None = None,
        scope: str = "global",
        source: str = "",
        payload: dict | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
    ) -> DiagnosticEvent:
        event = DiagnosticEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            trace_id=trace_id,
            scope=scope,
            source=source,
            payload=payload or {},
            duration_ms=duration_ms,
            error=error,
        )
        self.record_event(event)
        return event

    # ── Event Query ───────────────────────────────────────────────

    def get_recent_events(
        self,
        *,
        event_type_prefix: str | None = None,
        scope: str | None = None,
        limit: int = 50,
    ) -> list[DiagnosticEvent]:
        """Return recent events, optionally filtered."""
        with self._lock:
            events = list(self._events)
        if event_type_prefix:
            events = [e for e in events if e.event_type.startswith(event_type_prefix)]
        if scope:
            events = [e for e in events if e.scope == scope or e.scope == "global"]
        return events[-limit:]

    # ── Vote / Consensus helpers ─────────────────────────────────

    def record_vote(
        self,
        voter_name: str,
        decision: str,
        confidence: float,
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        trace_id: str | None = None,
        duration_ms: float | None = None,
    ) -> DiagnosticEvent:
        scope = _scope(student_id, module_id)
        return self.make_event(
            event_type=f"vote:{decision}",
            correlation_id=trace_id,
            trace_id=trace_id,
            scope=scope,
            source=voter_name,
            payload={"decision": decision, "confidence": confidence},
            duration_ms=duration_ms,
        )

    def record_consensus(
        self,
        decision: str,
        confidence: float,
        votes: list[dict],
        *,
        student_id: str | None = None,
        module_id: str | None = None,
        trace_id: str | None = None,
        duration_ms: float | None = None,
    ) -> DiagnosticEvent:
        scope = _scope(student_id, module_id)
        return self.make_event(
            event_type=f"consensus:{decision}",
            correlation_id=trace_id,
            trace_id=trace_id,
            scope=scope,
            source="consensus_engine",
            payload={
                "decision": decision,
                "confidence": confidence,
                "num_voters": len(votes),
                "votes": votes,
            },
            duration_ms=duration_ms,
        )

    def record_memory_op(
        self,
        op: str,
        *,
        voter_name: str | None = None,
        student_id: str | None = None,
        module_id: str | None = None,
        key: str | None = None,
        trace_id: str | None = None,
        duration_ms: float | None = None,
        error: str | None = None,
    ) -> DiagnosticEvent:
        scope = _scope(student_id, module_id)
        return self.make_event(
            event_type=f"memory:{op}",
            correlation_id=trace_id,
            trace_id=trace_id,
            scope=scope,
            source=voter_name or "memory_store",
            payload={"key": key, "voter": voter_name},
            duration_ms=duration_ms,
            error=error,
        )

    def record_execution(
        self,
        node_name: str,
        agent_name: str,
        status: str,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        trace_id: str | None = None,
        scope: str = "global",
        duration_ms: float | None = None,
        error: str | None = None,
        payload: dict | None = None,
    ) -> DiagnosticEvent:
        return self.make_event(
            event_type=f"execution:{node_name}:{status}",
            correlation_id=correlation_id,
            causation_id=causation_id,
            trace_id=trace_id,
            scope=scope,
            source=agent_name,
            payload=payload or {},
            duration_ms=duration_ms,
            error=error,
        )

    # ── Detector orchestration ───────────────────────────────────

    def run_detectors(
        self,
        scope: str | None = None,
        time_window_seconds: float = 300.0,
    ) -> list[AnomalySignal]:
        now = datetime.now(timezone.utc)
        window_events = [e for e in self._events if (now - e.created_at).total_seconds() <= time_window_seconds]
        if scope:
            window_events = [e for e in window_events if e.scope == scope or e.scope == "global"]

        signals: list[AnomalySignal] = []
        for detector in self._detectors.values():
            try:
                result = detector.analyze(window_events, metrics=self.metrics)
                signals.extend(result)
            except Exception:
                pass

        with self._lock:
            self._anomalies.extend(signals)
            if len(self._anomalies) > self._max_anomalies:
                self._anomalies = self._anomalies[-self._max_anomalies:]

        return signals

    def get_active_anomalies(
        self,
        scope: str | None = None,
        severity: Severity | None = None,
        max_age_seconds: float = 3600.0,
    ) -> list[AnomalySignal]:
        now = datetime.now(timezone.utc)
        result: list[AnomalySignal] = []
        for a in self._anomalies:
            if (now - a.created_at).total_seconds() > max_age_seconds:
                continue
            if scope and a.scope != scope and a.scope != "global":
                continue
            if severity and a.severity != severity:
                continue
            result.append(a)
        return result

    def get_detector(self, name: str) -> BaseDetector | None:
        return self._detectors.get(name)

    def register_detector(self, detector: BaseDetector) -> None:
        self._detectors[detector.name] = detector

    # ── Health report ────────────────────────────────────────────

    def health_report(
        self,
        scope: str = "global",
        time_window_seconds: float = 300.0,
    ) -> HealthSnapshot:
        signals = self.run_detectors(scope=scope, time_window_seconds=time_window_seconds)
        active = self.get_active_anomalies(scope=scope)

        critical_count = sum(1 for a in active if a.severity == Severity.CRITICAL)
        warning_count = sum(1 for a in active if a.severity == Severity.WARNING)

        if critical_count > 0:
            status = "critical"
        elif warning_count > 0:
            status = "degraded"
        else:
            status = "healthy"

        scope_metrics = self.metrics.get_scope_metrics(scope)

        return HealthSnapshot(
            snapshot_id=str(uuid.uuid4()),
            scope=scope,
            status=status,
            active_anomalies=active,
            metrics=scope_metrics,
            summary=_build_summary(status, len(signals), active),
        )

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
            self._anomalies.clear()
        self.metrics.reset()
        self.lineage.reset()
        for d in self._detectors.values():
            d.reset()


def _scope(student_id: str | None, module_id: str | None) -> str:
    if student_id and module_id:
        return f"student:{student_id}:module:{module_id}"
    if student_id:
        return f"student:{student_id}"
    if module_id:
        return f"module:{module_id}"
    return "global"


def _build_summary(status: str, new_signals: int, active: list[AnomalySignal]) -> str:
    parts = [f"Swarm health: {status}"]
    if new_signals:
        parts.append(f"{new_signals} new signal(s) detected")
    if active:
        by_severity = defaultdict(int)
        for a in active:
            by_severity[a.severity.value] += 1
        parts.append("Active: " + ", ".join(f"{k}={v}" for k, v in sorted(by_severity.items())))
    return " | ".join(parts)
