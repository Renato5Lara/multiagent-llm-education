"""
Observability package — metrics export, real-time streaming.

Public API:
    exporter — MetricsExporter singleton (Prometheus + JSON)
    stream   — MetricsStream singleton (SSE fan-out)

Usage:
    from app.observability import exporter, stream
    exporter.inc_counter("my_event")
    stream.push("my_event", {"key": "value"})
"""

from app.observability.metrics_exporter import MetricsExporter, exporter
from app.observability.stream import MetricsStream, stream

__all__ = [
    "MetricsExporter", "exporter",
    "MetricsStream", "stream",
]
