"""
RecursiveAmplificationDetector — Detects events that multiply through
recursive propagation, causing exponential fan-out and resource exhaustion.

Signals:
    - amplification_chain: single source produces many downstream events
    - fanout_explosion: hop count expands faster than expected
    - echo_pattern: same event type appears in a feedback loop
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class RecursiveAmplificationDetector(BaseDetector):
    name = "recursive_amplification"

    def __init__(
        self,
        fanout_threshold: int = 5,
        amplification_ratio: float = 3.0,
        echo_window_seconds: float = 300.0,
        min_events_for_detection: int = 8,
    ):
        self.fanout_threshold = fanout_threshold
        self.amplification_ratio = amplification_ratio
        self.echo_window_seconds = echo_window_seconds
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

        causation_tree: dict[str, list[str]] = defaultdict(list)
        event_map: dict[str, DiagnosticEvent] = {}
        for e in events:
            event_map[e.event_id] = e
            parent = e.causation_id or "root"
            causation_tree[parent].append(e.event_id)

        source_counts: dict[str, int] = {}
        for parent, children in causation_tree.items():
            children_count = len(children)
            if children_count > self.fanout_threshold:
                source_counts[parent] = children_count

        for parent_id, children_count in source_counts.items():
            parent_event = event_map.get(parent_id)
            scope = parent_event.scope if parent_event else "unknown"

            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.RECURSIVE_AMPLIFICATION,
                severity=Severity.WARNING if children_count < self.fanout_threshold * 3 else Severity.CRITICAL,
                scope=scope,
                title=f"Fanout amplification: {children_count} children",
                description=(
                    f"Event {parent_id[:16]} produced {children_count} downstream events "
                    f"(threshold: {self.fanout_threshold})"
                ),
                metric_value=float(children_count),
                threshold=float(self.fanout_threshold),
                evidence={
                    "parent_event_id": parent_id,
                    "children_count": children_count,
                    "child_event_ids": causation_tree[parent_id][:20],
                },
                recommendation=(
                    "High fan-out indicates recursive amplification. "
                    "Review event handlers for unintended re-triggering. "
                    "Consider reducing PropagationTTL max_hops or increasing decay_factor."
                ),
            ))


        type_chain_counts: dict[str, int] = defaultdict(int)
        type_events: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        for e in events:
            type_chain_counts[e.event_type] += 1
            type_events[e.event_type].append(e)

        for event_type, count in type_chain_counts.items():
            if count < self.fanout_threshold:
                continue
            chain_events = sorted(type_events[event_type], key=lambda x: x.created_at)
            if len(chain_events) < 3:
                continue

            total_span = (
                chain_events[-1].created_at - chain_events[0].created_at
            ).total_seconds()
            if total_span > self.echo_window_seconds:
                continue

            self_count = 0
            for e in chain_events:
                if e.causation_id and e.causation_id in event_map:
                    parent = event_map[e.causation_id]
                    if parent.event_type == event_type:
                        self_count += 1

            if self_count > self.fanout_threshold:
                first_event = chain_events[0]
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.RECURSIVE_AMPLIFICATION,
                    severity=Severity.CRITICAL,
                    scope=first_event.scope,
                    title=f"Echo pattern detected: {event_type}",
                    description=(
                        f"Event type {event_type} appears {count} times "
                        f"in {total_span:.0f}s with {self_count} self-triggered events"
                    ),
                    metric_value=float(self_count),
                    threshold=float(self.fanout_threshold),
                    evidence={
                        "event_type": event_type,
                        "total_count": count,
                        "self_triggered": self_count,
                        "time_window_sec": round(total_span, 1),
                    },
                    recommendation=(
                        "Self-triggering echo pattern detected. "
                        "The same event type is re-emitting itself through handlers. "
                        "Verify anti-feedback-loop protection and add circuit breakers."
                    ),
                ))

        return signals
