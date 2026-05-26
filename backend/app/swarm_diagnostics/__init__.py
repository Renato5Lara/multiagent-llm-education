"""
Swarm Diagnostics — Enterprise-grade observability for multi-agent consensus swarms.

Provides:
    - Specialized anomaly detectors for 10 distinct failure modes
    - Metrics pipeline with async-safe collection
    - Tracing pipeline for distributed trace propagation
    - Event lineage tracking with full causal chains
    - Alert rules engine with severity classification
    - FastAPI middleware for automatic instrumentation

Usage:
    from app.swarm_diagnostics import diagnostics_engine
    diagnostics_engine.record_vote(ctx, vote)
    diagnostics_engine.record_event(event)
    report = diagnostics_engine.health_report(scope="student:stu-1")
"""

from app.swarm_diagnostics.core import SwarmDiagnosticsEngine

diagnostics_engine = SwarmDiagnosticsEngine()

__all__ = [
    "SwarmDiagnosticsEngine",
    "diagnostics_engine",
]
