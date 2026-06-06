"""
Experiment Reset Protocol — unified destructive reset of all global singletons.

Each subsystem that accumulates mutable state exposes a `reset()` method.
This module provides a single entrypoint that resets EVERYTHING at once,
guaranteeing zero cross-experiment contamination.

Targets:
    - TrustSystem (app.core.trust)
    - ConsensusMetrics (app.observability.consensus_metrics)
    - SwarmDiagnosticsEngine (app.swarm_diagnostics)
    - MetricsExporter (app.observability.metrics_exporter)
    - SharedMemoryStore (app.memory.shared_memory) — no in-memory state,
      included as a no-op for interface consistency
"""

from __future__ import annotations

import logging

from app.observability.consensus_metrics import metrics as consensus_metrics
from app.observability.metrics_exporter import exporter as obs_exporter

logger = logging.getLogger(__name__)


def reset_all_global_state() -> dict[str, bool]:
    """Destructively reset EVERY global singleton to its initial state.

    Returns a dict mapping subsystem name → whether reset was successful.

    After calling this, ALL accumulated state is gone:
        - Trust scores / voter records
        - Consensus counters (runs, approvals, rejections, …)
        - Diagnostics events, anomalies, metrics, lineage
        - Exporter counters, histograms, activations, sessions, …
        - Experiment metrics / groups

    Caller MUST ensure no concurrent operations are in-flight.
    """
    results: dict[str, bool] = {}

    # 1. Trust system
    try:
        from app.core.trust import reset_trust_system as _reset_trust
        _reset_trust()
        results["trust_system"] = True
    except Exception as exc:
        logger.warning("Failed to reset TrustSystem: %s", exc)
        results["trust_system"] = False

    # 2. Consensus metrics
    try:
        consensus_metrics.reset()
        results["consensus_metrics"] = True
    except Exception as exc:
        logger.warning("Failed to reset ConsensusMetrics: %s", exc)
        results["consensus_metrics"] = False

    # 3. Swarm diagnostics engine
    try:
        from app.swarm_diagnostics import diagnostics_engine as _diag
        _diag.reset()
        results["diagnostics_engine"] = True
    except Exception as exc:
        logger.warning("Failed to reset SwarmDiagnosticsEngine: %s", exc)
        results["diagnostics_engine"] = False

    # 4. Metrics exporter
    try:
        obs_exporter.reset()
        results["metrics_exporter"] = True
    except Exception as exc:
        logger.warning("Failed to reset MetricsExporter: %s", exc)
        results["metrics_exporter"] = False

    # 5. Shared memory store (no-op — in-memory state is zero)
    results["shared_memory_store"] = True

    logger.info(
        "Global state reset: %s",
        {k: "ok" if v else "FAILED" for k, v in results.items()},
    )
    return results
