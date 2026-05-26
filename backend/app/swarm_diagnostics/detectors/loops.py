"""
DelegationLoopDetector — Detects cycles in agent delegation chains by
analyzing causation_id references in the event lineage.

Signals:
    - delegation_cycle: events form a cycle in the causation graph
    - deep_delegation: chain depth exceeds threshold
"""

from __future__ import annotations

import uuid
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class DelegationLoopDetector(BaseDetector):
    name = "delegation_loop"

    def __init__(self, max_depth: int = 10):
        self.max_depth = max_depth

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []

        causation_map: dict[str, list[str]] = {}
        event_map: dict[str, DiagnosticEvent] = {}
        for e in events:
            event_map[e.event_id] = e
            if e.causation_id:
                causation_map.setdefault(e.causation_id, []).append(e.event_id)

        visited: set[str] = set()
        path: list[str] = []
        cycles: list[list[str]] = []

        def dfs(eid: str) -> None:
            if eid in path:
                cycle_start = path.index(eid)
                cycles.append(path[cycle_start:] + [eid])
                return
            if eid in visited:
                return
            visited.add(eid)
            path.append(eid)
            for child_id in causation_map.get(eid, []):
                dfs(child_id)
            path.pop()

        for eid in list(event_map.keys()):
            dfs(eid)

        for cycle in cycles:
            cycle_events = [event_map.get(eid) for eid in cycle if event_map.get(eid)]
            scope = cycle_events[0].scope if cycle_events else "global"
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.DELEGATION_LOOP,
                severity=Severity.CRITICAL,
                scope=scope,
                title="Delegation cycle detected",
                description=f"Causation cycle of length {len(cycle)}: {' -> '.join(eid[:8] for eid in cycle)}",
                metric_value=float(len(cycle)),
                threshold=3.0,
                evidence={"cycle": cycle, "event_types": [event_map[e].event_type for e in cycle if event_map.get(e)]},
                recommendation="Break the cycle by removing circular causation links in agent orchestration.",
            ))

        for e in events:
            if e.causation_id:
                depth = 1
                current = e
                seen: set[str] = set()
                while current.causation_id and depth <= self.max_depth + 5:
                    if current.event_id in seen:
                        break
                    seen.add(current.event_id)
                    parent = event_map.get(current.causation_id)
                    if parent:
                        depth += 1
                        current = parent
                    else:
                        break
                if depth > self.max_depth:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.DELEGATION_LOOP,
                        severity=Severity.WARNING,
                        scope=e.scope,
                        title="Deep delegation chain",
                        description=f"Chain depth {depth} exceeds threshold {self.max_depth}",
                        metric_value=float(depth),
                        threshold=float(self.max_depth),
                        evidence={"event_id": e.event_id, "depth": depth},
                        recommendation="Flatten agent orchestration or introduce aggregation nodes.",
                    ))

        return signals
