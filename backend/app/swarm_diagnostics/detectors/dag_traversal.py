"""
DAGTraversalPitfallDetector — Detects common DAG traversal pitfalls
in the event propagation graph.

Signals:
    - repeated_visits: same node processed multiple times in a chain
    - dag_cycle: causation chain forms a cycle
    - dead_end_traversal: chain terminates without completing processing
    - fanout_imbalance: uneven downstream distribution
    - traversal_depth_violation: chain depth exceeds expected bounds
"""

from __future__ import annotations

import uuid
from collections import defaultdict, Counter
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class DAGTraversalPitfallDetector(BaseDetector):
    name = "dag_traversal_pitfall"

    def __init__(
        self,
        max_depth: int = 10,
        repeated_visit_threshold: int = 2,
        min_events_for_detection: int = 5,
    ):
        self.max_depth = max_depth
        self.repeated_visit_threshold = repeated_visit_threshold
        self.min_events_for_detection = min_events_for_detection

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        if len(events) < self.min_events_for_detection:
            return signals

        event_map: dict[str, DiagnosticEvent] = {}
        for e in events:
            event_map[e.event_id] = e

        causation_graph: dict[str, list[str]] = defaultdict(list)
        for e in events:
            parent = e.causation_id or "root"
            causation_graph[parent].append(e.event_id)

        for e in events:
            depth = self._compute_depth(e.event_id, event_map, causation_graph)
            if depth > self.max_depth:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.DAG_TRAVERSAL_PITFALL,
                    severity=Severity.WARNING,
                    scope=e.scope,
                    title=f"Excessive traversal depth: {depth}",
                    description=(
                        f"Event {e.event_id[:16]} at depth {depth} "
                        f"exceeds max {self.max_depth}"
                    ),
                    metric_value=float(depth),
                    threshold=float(self.max_depth),
                    evidence={
                        "event_id": e.event_id,
                        "depth": depth,
                        "chain_start": self._find_root(e.event_id, causation_graph)[:16],
                    },
                    recommendation=(
                        "Deep DAG traversal may indicate missing termination. "
                        "Verify PropagationTTL max_hops and DAG-cycle detection."
                    ),
                ))

            visit_count = self._count_visits_in_chain(e.event_id, event_map)
            if visit_count > self.repeated_visit_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.DAG_TRAVERSAL_PITFALL,
                    severity=Severity.WARNING,
                    scope=e.scope,
                    title=f"Repeated node visit ({visit_count}x)",
                    description=(
                        f"Event {e.event_id[:16]} visited {visit_count} times "
                        f"in its causation chain (threshold: {self.repeated_visit_threshold})"
                    ),
                    metric_value=float(visit_count),
                    threshold=float(self.repeated_visit_threshold),
                    evidence={
                        "event_id": e.event_id,
                        "visit_count": visit_count,
                    },
                    recommendation=(
                        "Same event/node visited multiple times in a DAG traversal. "
                        "Verify visited_events tracking in PropagationTTL. "
                        "This may indicate a cycle or routing misconfiguration."
                    ),
                ))

        cycles = self._detect_cycles(causation_graph, event_map)
        for cycle in cycles:
            scope = "unknown"
            for eid in cycle:
                if eid in event_map:
                    scope = event_map[eid].scope
                    break
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.DAG_TRAVERSAL_PITFALL,
                severity=Severity.CRITICAL,
                scope=scope,
                title="DAG cycle detected in causation graph",
                description=f"Causation cycle of length {len(cycle)}: {' → '.join(e[:8] for e in cycle)}",
                metric_value=float(len(cycle)),
                threshold=2.0,
                evidence={
                    "cycle": cycle,
                    "cycle_length": len(cycle),
                },
                recommendation=(
                    "A DAG cycle was detected in the event causation graph. "
                    "This indicates a feedback loop where event A causes B "
                    "which causes A again. Verify anti-feedback-loop protection "
                    "and ensure visited_agents/events are properly tracked."
                ),
            ))

        fanout_data = self._analyze_fanout_balance(causation_graph, event_map)
        for item in fanout_data:
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.DAG_TRAVERSAL_PITFALL,
                severity=Severity.INFO,
                scope=item["scope"],
                title="Fanout imbalance in DAG traversal",
                description=(
                    f"Node {item['parent_id'][:16]} has {item['children_count']} children, "
                    f"variance {item['variance']:.1f}"
                ),
                metric_value=item["variance"],
                threshold=item["children_count"],
                evidence=item,
                recommendation=(
                    "Uneven fan-out distribution may indicate a bottleneck "
                    "or star topology. Consider load balancing or DAG rebalancing."
                ),
            ))

        return signals

    def _compute_depth(
        self,
        event_id: str,
        event_map: dict[str, DiagnosticEvent],
        graph: dict[str, list[str]],
    ) -> int:
        depth = 0
        current = event_id
        visited: set[str] = set()
        while current in graph and current != "root":
            if current in visited:
                break
            visited.add(current)
            parents = graph.get(current, [])
            if not parents:
                break
            current = parents[0]
            depth += 1
            if depth > 100:
                break
        return depth

    def _find_root(self, event_id: str, graph: dict[str, list[str]]) -> str:
        current = event_id
        visited: set[str] = set()
        while current in graph and current != "root":
            if current in visited:
                break
            visited.add(current)
            parents = graph.get(current, [])
            if not parents:
                break
            current = parents[0]
        return current

    def _count_visits_in_chain(
        self,
        event_id: str,
        event_map: dict[str, DiagnosticEvent],
    ) -> int:
        seen: Counter = Counter()
        current = event_id
        visited: set[str] = set()
        while current in event_map and current != "root":
            if current in visited:
                seen[current] += 1
                break
            visited.add(current)
            seen[current] += 1
            event = event_map[current]
            if event.causation_id and event.causation_id in event_map:
                current = event.causation_id
            else:
                break
        return seen[event_id]

    def _detect_cycles(
        self,
        graph: dict[str, list[str]],
        event_map: dict[str, DiagnosticEvent],
    ) -> list[list[str]]:
        cycles: list[list[str]] = []
        visited_global: set[str] = set()

        def dfs(node: str, path: list[str], path_set: set[str]) -> None:
            if node in path_set:
                cycle_start = path.index(node)
                cycle = path[cycle_start:]
                if len(cycle) >= 2:
                    cycles.append(list(cycle))
                return
            if node in visited_global or node not in graph:
                return
            visited_global.add(node)
            path.append(node)
            path_set.add(node)
            for child in graph.get(node, []):
                dfs(child, path, path_set)
            path.pop()
            path_set.discard(node)

        for e in list(event_map.keys()):
            if e not in visited_global:
                dfs(e, [], set())

        return cycles

    def _analyze_fanout_balance(
        self,
        graph: dict[str, list[str]],
        event_map: dict[str, DiagnosticEvent],
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for parent, children in graph.items():
            if len(children) < 4:
                continue
            if parent == "root" or parent not in event_map:
                continue
            parent_event = event_map.get(parent)
            scope = parent_event.scope if parent_event else "unknown"

            if children:
                child_counts = []
                for child_id in children:
                    grand_children = graph.get(child_id, [])
                    child_counts.append(len(grand_children))
                if child_counts:
                    avg = sum(child_counts) / len(child_counts)
                    variance = sum((c - avg) ** 2 for c in child_counts) / len(child_counts)
                    if variance > avg * 2:
                        results.append({
                            "parent_id": parent,
                            "scope": scope,
                            "children_count": len(children),
                            "avg": round(avg, 2),
                            "variance": round(variance, 2),
                        })
        return results
