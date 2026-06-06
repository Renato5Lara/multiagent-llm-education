"""
Observability package — metrics export, real-time streaming, dashboard.

Public API:
    exporter          — MetricsExporter singleton (Prometheus + JSON)
    stream            — MetricsStream singleton (SSE fan-out)
    diagnostics       — SwarmDiagnostics singleton (decision timeline + event chains)
    consensus_metrics — ConsensusMetrics singleton (in-process counters)
    swarm_diagnostics — SwarmDiagnostics timeline/chain module

Usage:
    from app.observability import exporter, stream
    exporter.inc_counter("my_event")
    stream.push("my_event", {"key": "value"})
"""

from app.observability.metrics_exporter import MetricsExporter, exporter
from app.observability.stream import MetricsStream, stream
from app.observability.swarm_diagnostics import SwarmDiagnostics, diagnostics
from app.observability.consensus_metrics import ConsensusMetrics, metrics as consensus_metrics

__all__ = [
    "MetricsExporter", "exporter",
    "MetricsStream", "stream",
    "SwarmDiagnostics", "diagnostics",
    "ConsensusMetrics", "consensus_metrics",
]
