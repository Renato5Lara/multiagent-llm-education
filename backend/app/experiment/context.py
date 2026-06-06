"""
Experiment Context — isolated, reproducible, non-contaminating experiment execution.

Design philosophy:
    Instead of save/restore (which is fragile with threading.Lock objects),
    we provide FRESH isolated instances for every experiment.  The caller
    injects these into the swarm subsystem instead of the global singletons.

    For callers that CANNOT inject (tightly coupled legacy code), the
    unified reset_all_global_state() protocol destructively clears every
    global singleton.

Two isolation modes:
    1. FRESH MODE (default) — async context manager yields an ExperimentState
       with brand-new TrustSystem, ConsensusMetrics, MetricsExporter, and
       SwarmDiagnosticsEngine instances.  No global state is touched.

    2. RESET MODE (reset_globals=True) — on enter, calls reset_all_global_state()
       to destructively clear every global singleton.  On exit, calls it again
       so the caller leaves a clean slate.

Usage (fresh mode — RECOMMENDED):
    async with ExperimentContext(label="ablation:no-specialization") as exp:
        result = await engine.async_run(
            ctx,
            trust_system=exp.trust_system,
            shared_memory_store=store,
        )
        exp.record_result(result)

Usage (reset mode — for legacy code):
    async with ExperimentContext(label="legacy-test", reset_globals=True):
        result = await engine.async_run(ctx)

Thread-safety:
    ExperimentContext is NOT thread-safe.  Create one per experiment.
    The fresh instances it provides ARE thread-safe.
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.trust import TrustSystem
from app.observability.consensus_metrics import ConsensusMetrics
from app.observability.metrics_exporter import MetricsExporter
from app.swarm_diagnostics.core import SwarmDiagnosticsEngine

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════
# Experiment state
# ═══════════════════════════════════════════════════════════════════


@dataclass
class ExperimentSnapshot:
    """Serializable snapshot of global state AT A POINT IN TIME.

    Used to compare pre/post experiment state and verify isolation.
    """

    experiment_id: str
    label: str
    timestamp: str
    trust_system: dict[str, Any]
    consensus_metrics: dict[str, Any]
    diagnostics_events_count: int
    diagnostics_anomalies_count: int
    exporter_counters: dict[str, int]
    exporter_anomaly_count: int
    exporter_recovery_attempts: int
    hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "label": self.label,
            "timestamp": self.timestamp,
            "trust_system": self.trust_system,
            "consensus_metrics": self.consensus_metrics,
            "diagnostics_events_count": self.diagnostics_events_count,
            "diagnostics_anomalies_count": self.diagnostics_anomalies_count,
            "exporter_counters": self.exporter_counters,
            "exporter_anomaly_count": self.exporter_anomaly_count,
            "exporter_recovery_attempts": self.exporter_recovery_attempts,
            "hash": self.hash,
        }


@dataclass
class ExperimentState:
    """Isolated state bundle provided by ExperimentContext.

    Every instance is FRESH — zero accumulated state from prior runs.
    """

    experiment_id: str
    label: str
    trust_system: TrustSystem
    consensus_metrics: ConsensusMetrics
    exporter: MetricsExporter
    diagnostics_engine: SwarmDiagnosticsEngine
    created_at: datetime

    # Optional: the caller can attach the final ConsensusResult
    result: Any = None

    # Internal timing
    _start_wall: float = field(default_factory=time.time)

    def elapsed_ms(self) -> float:
        return (time.time() - self._start_wall) * 1000.0

    def record_result(self, result: Any) -> None:
        self.result = result

    def _state_hash(self) -> str:
        """Deterministic hash of BEHAVIORAL state only (no timestamps)."""
        raw = json.dumps(
            {
                "trust_system": self.trust_system.get_snapshot(),
                "consensus_metrics": self.consensus_metrics.get_snapshot(),
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_snapshot(self) -> ExperimentSnapshot:
        content_hash = self._state_hash()
        metrics_snap = self.consensus_metrics.get_snapshot()

        return ExperimentSnapshot(
            experiment_id=self.experiment_id,
            label=self.label,
            timestamp=datetime.now(timezone.utc).isoformat(),
            trust_system=self.trust_system.get_snapshot(),
            consensus_metrics=metrics_snap,
            diagnostics_events_count=len(self.diagnostics_engine._events),
            diagnostics_anomalies_count=len(self.diagnostics_engine._anomalies),
            exporter_counters=dict(self.exporter._custom_counters),
            exporter_anomaly_count=self.exporter._anomaly_total_count,
            exporter_recovery_attempts=self.exporter._recovery_attempts,
            hash=content_hash,
        )


# ═══════════════════════════════════════════════════════════════════
# Experiment Registry (singleton-like)
# ═══════════════════════════════════════════════════════════════════


class ExperimentRegistry:
    """Tracks all experiments for reproducibility and comparison.

    Singleton shared across the process.  Thread-safe.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._experiments: dict[str, ExperimentState] = {}
        self._snapshots: dict[str, ExperimentSnapshot] = {}
        self._max_snapshots = 500

    # ── Registration ──────────────────────────────────────────────

    def register(self, state: ExperimentState) -> None:
        with self._lock:
            self._experiments[state.experiment_id] = state

    def archive(self, snapshot: ExperimentSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.experiment_id] = snapshot
            if len(self._snapshots) > self._max_snapshots:
                keys = sorted(self._snapshots.keys())[:-self._max_snapshots]
                for k in keys:
                    del self._snapshots[k]

    def unregister(self, experiment_id: str) -> None:
        with self._lock:
            self._experiments.pop(experiment_id, None)

    # ── Query ─────────────────────────────────────────────────────

    def get(self, experiment_id: str) -> ExperimentState | None:
        with self._lock:
            return self._experiments.get(experiment_id)

    def get_snapshot(self, experiment_id: str) -> ExperimentSnapshot | None:
        with self._lock:
            return self._snapshots.get(experiment_id)

    def list_experiments(self) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {
                    "experiment_id": eid,
                    "label": s.label,
                    "created_at": s.created_at.isoformat(),
                    "elapsed_ms": round(s.elapsed_ms(), 2),
                    "has_result": s.result is not None,
                }
                for eid, s in sorted(self._experiments.items())
            ]

    def get_by_hash(self, content_hash: str) -> list[ExperimentSnapshot]:
        with self._lock:
            return [
                s for s in self._snapshots.values() if s.hash == content_hash
            ]

    def compare(
        self,
        id_a: str,
        id_b: str,
    ) -> dict[str, Any]:
        snap_a = self.get_snapshot(id_a)
        snap_b = self.get_snapshot(id_b)
        if snap_a is None or snap_b is None:
            raise ValueError(f"Unknown experiment(s): {id_a} / {id_b}")

        return {
            "same_hash": snap_a.hash == snap_b.hash,
            "hash_a": snap_a.hash,
            "hash_b": snap_b.hash,
            "trust_system_equal": snap_a.trust_system == snap_b.trust_system,
            "consensus_metrics_equal": (
                snap_a.consensus_metrics == snap_b.consensus_metrics
            ),
            "diagnostics_events_delta": (
                snap_b.diagnostics_events_count - snap_a.diagnostics_events_count
            ),
            "diagnostics_anomalies_delta": (
                snap_b.diagnostics_anomalies_count
                - snap_a.diagnostics_anomalies_count
            ),
            "exporter_counters_equal": (
                snap_a.exporter_counters == snap_b.exporter_counters
            ),
        }

    def reset(self) -> None:
        with self._lock:
            self._experiments.clear()
            self._snapshots.clear()


# Module-level singleton
registry: ExperimentRegistry = ExperimentRegistry()


# ═══════════════════════════════════════════════════════════════════
# ExperimentContext
# ═══════════════════════════════════════════════════════════════════


class ExperimentContext:
    """Async context manager that provides fully isolated experiment state.

    Two modes:
        fresh (default)  — creates new TrustSystem, ConsensusMetrics,
                           MetricsExporter, SwarmDiagnosticsEngine.
                           Global singletons are NEVER touched.

        reset_globals=True — calls reset_all_global_state() on enter
                             and exit.  Useful for legacy integration
                             where injection is not possible.

    Args:
        label: Optional human-readable label for the experiment.
        reset_globals: If True, destructively reset all global singletons
                       instead of providing fresh instances.
    """

    def __init__(
        self,
        label: str = "",
        reset_globals: bool = False,
    ) -> None:
        self.label = label
        self.reset_globals = reset_globals
        self.state: ExperimentState | None = None
        self._pre_snapshot: ExperimentSnapshot | None = None

    # ── Lifecycle ─────────────────────────────────────────────────

    async def __aenter__(self) -> ExperimentState:
        experiment_id = str(uuid.uuid4())

        if self.reset_globals:
            from app.experiment.reset import reset_all_global_state

            reset_all_global_state()
            # In reset mode we DON'T create fresh instances — the
            # caller uses globals which have been cleared.
            self.state = ExperimentState(
                experiment_id=experiment_id,
                label=self.label,
                trust_system=TrustSystem(),
                consensus_metrics=ConsensusMetrics(),
                exporter=MetricsExporter(),
                diagnostics_engine=SwarmDiagnosticsEngine(),
                created_at=datetime.now(timezone.utc),
            )
        else:
            # FRESH MODE: brand-new instances, zero accumulated state
            self.state = ExperimentState(
                experiment_id=experiment_id,
                label=self.label,
                trust_system=TrustSystem(),
                consensus_metrics=ConsensusMetrics(),
                exporter=MetricsExporter(),
                diagnostics_engine=SwarmDiagnosticsEngine(),
                created_at=datetime.now(timezone.utc),
            )
            logger.debug(
                "ExperimentContext[%s]: fresh instances created "
                "(trust=%s, metrics=%s, exporter=%s, diagnostics=%s)",
                experiment_id[:8],
                id(self.state.trust_system),
                id(self.state.consensus_metrics),
                id(self.state.exporter),
                id(self.state.diagnostics_engine),
            )

        # Snapshot pre-experiment state for reproducibility
        self._pre_snapshot = self.state.to_snapshot()
        registry.register(self.state)

        return self.state

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: Any = None,
    ) -> None:
        if self.state is None:
            return

        # Archive post-experiment snapshot
        post_snapshot = self.state.to_snapshot()
        registry.archive(post_snapshot)

        if self.reset_globals:
            from app.experiment.reset import reset_all_global_state

            reset_all_global_state()

        logger.info(
            "ExperimentContext[%s]: done (label=%s, elapsed=%.0fms, "
            "hash=%s, reset_globals=%s)",
            self.state.experiment_id[:8],
            self.label or "unlabeled",
            self.state.elapsed_ms(),
            post_snapshot.hash,
            self.reset_globals,
        )

        self.state = None


# Shorthand: run a function inside an isolated experiment
async def run_experiment(
    fn,
    label: str = "",
    reset_globals: bool = False,
    **kwargs: Any,
) -> tuple[ExperimentState, Any]:
    """Execute a callable inside an ExperimentContext.

    Returns (state, result) where result is the return value of fn(state).

    Example:
        async def my_experiment(exp):
            return await engine.async_run(ctx, trust_system=exp.trust_system)

        state, result = await run_experiment(my_experiment, label="test-1")
    """
    async with ExperimentContext(label=label, reset_globals=reset_globals) as state:
        result = await fn(state, **kwargs)
        state.record_result(result)
    return state, result
