"""
StaleMemoryMonitor — Monitors shared memory freshness and detects
elevated stale ratios.

Signals:
    - high_stale_ratio: proportion of stale records exceeds threshold
    - memory_scope_decay: specific student/module scope has excessive stale memory
    - orphaned_memory: records with no reads since creation
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class StaleMemoryMonitor(BaseDetector):
    name = "stale_memory_monitor"

    def __init__(self, stale_ratio_threshold: float = 0.3):
        self.stale_ratio_threshold = stale_ratio_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        memory_events = [e for e in events if e.event_type.startswith("memory:")]

        read_events = [e for e in memory_events if "read" in e.event_type or "query" in e.event_type]
        write_events = [e for e in memory_events if "publish" in e.event_type or "write" in e.event_type]

        scope_writes: dict[str, int] = defaultdict(int)
        scope_reads: dict[str, int] = defaultdict(int)
        for e in write_events:
            scope_writes[e.scope] += 1
        for e in read_events:
            scope_reads[e.scope] += 1

        for scope in set(list(scope_writes.keys()) + list(scope_reads.keys())):
            writes = scope_writes.get(scope, 0)
            reads = scope_reads.get(scope, 0)
            if writes == 0:
                continue
            read_ratio = reads / writes
            if read_ratio < self.stale_ratio_threshold and writes >= 5:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.STALE_MEMORY,
                    severity=Severity.WARNING,
                    scope=scope,
                    title="Low memory read ratio",
                    description=f"Scope {scope}: {reads} reads vs {writes} writes (ratio={read_ratio:.2f})",
                    metric_value=read_ratio,
                    threshold=self.stale_ratio_threshold,
                    evidence={"scope": scope, "reads": reads, "writes": writes},
                    recommendation="Consumers may not be querying shared memory — review agent context enrichment.",
                ))

        orphaned = [e for e in write_events if "memory:publish" in e.event_type]
        if len(orphaned) > 50 and metrics:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.STALE_MEMORY,
                severity=Severity.INFO,
                scope="global",
                title="High memory publication volume",
                description=f"{len(orphaned)} publish events in window — verify TTL policies",
                metric_value=float(len(orphaned)),
                threshold=50.0,
                evidence={"publish_count": len(orphaned)},
                recommendation="Review TTL configuration and consider pruning aggressive publishers.",
            ))

        return signals
