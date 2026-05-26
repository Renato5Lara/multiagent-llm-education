"""
EventLineageTracker — Builds and queries causal chains from the event stream.

Links events by correlation_id and causation_id to reconstruct:
    - full causal chains (causation_id parent links)
    - correlation groups (all events sharing a correlation_id)
    - depth and breadth of propagation
    - cycles in agent delegation
"""

from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import Any

from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent


class EventLineageTracker:
    """Thread-safe causal chain tracker."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._by_correlation: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        self._by_causation: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        self._by_id: dict[str, DiagnosticEvent] = {}

    def record(self, event: DiagnosticEvent) -> None:
        with self._lock:
            self._by_id[event.event_id] = event
            if event.correlation_id:
                self._by_correlation[event.correlation_id].append(event)
            if event.causation_id:
                self._by_causation[event.causation_id].append(event)

    # ── Queries ──────────────────────────────────────────────────

    def get_chain(self, correlation_id: str) -> list[DiagnosticEvent]:
        with self._lock:
            return list(self._by_correlation.get(correlation_id, []))

    def get_children(self, causation_id: str) -> list[DiagnosticEvent]:
        with self._lock:
            return list(self._by_causation.get(causation_id, []))

    def get_event(self, event_id: str) -> DiagnosticEvent | None:
        with self._lock:
            return self._by_id.get(event_id)

    def get_all_correlation_ids(self) -> list[str]:
        with self._lock:
            return list(self._by_correlation.keys())

    def get_chain_depth(self, correlation_id: str) -> int:
        chain = self.get_chain(correlation_id)
        if not chain:
            return 0
        depth = 1
        for event in chain:
            if event.causation_id and event.causation_id != event.correlation_id:
                parent = self.get_event(event.causation_id)
                if parent:
                    depth += 1
        return depth

    def detect_cycle(self) -> list[list[str]]:
        with self._lock:
            visited: set[str] = set()
            cycles: list[list[str]] = []
            path: list[str] = []

            def dfs(event_id: str) -> None:
                if event_id in path:
                    cycle_start = path.index(event_id)
                    cycles.append(path[cycle_start:] + [event_id])
                    return
                if event_id in visited:
                    return
                visited.add(event_id)
                path.append(event_id)
                event = self._by_id.get(event_id)
                if event and event.causation_id:
                    parent = self._by_id.get(event.causation_id)
                    if parent:
                        dfs(parent.causation_id) if parent.causation_id else None
                path.pop()

            for eid in list(self._by_id.keys()):
                dfs(eid)
            return cycles

    def reset(self) -> None:
        with self._lock:
            self._by_correlation.clear()
            self._by_causation.clear()
            self._by_id.clear()
