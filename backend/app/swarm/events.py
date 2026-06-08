"""
Swarm Event Propagation with causation chains.

Each SwarmEvent carries:
- correlation_id: identifies the overall activation session
- causation_id: links to the event that caused this one
- parent_event_id: for building the causal DAG

The SwarmEventBus ensures:
1. Causality: every event (except root) references its parent
2. Ordering: in-phase events are ordered by sequence
3. Traceability: full causation chain can be reconstructed
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

from app.swarm.lifecycle import SwarmPhase

logger = logging.getLogger(__name__)


class SwarmEventType(str, Enum):
    ACTIVATION_REQUESTED = "swarm.activation.requested"
    ACTIVATION_STARTED = "swarm.activation.started"

    CONTEXT_LOAD_STARTED = "swarm.context.load.started"
    CONTEXT_LOAD_COMPLETED = "swarm.context.load.completed"
    CONTEXT_LOAD_FAILED = "swarm.context.load.failed"

    MEMORY_INIT_STARTED = "swarm.memory.init.started"
    MEMORY_INIT_COMPLETED = "swarm.memory.init.completed"
    MEMORY_INIT_FAILED = "swarm.memory.init.failed"

    PEDAGOGICAL_ANALYSIS_STARTED = "swarm.pedagogical.started"
    PEDAGOGICAL_ANALYSIS_COMPLETED = "swarm.pedagogical.completed"
    PEDAGOGICAL_ANALYSIS_FAILED = "swarm.pedagogical.failed"

    ADAPTIVE_ADJUSTMENT_STARTED = "swarm.adaptive.started"
    ADAPTIVE_ADJUSTMENT_COMPLETED = "swarm.adaptive.completed"
    ADAPTIVE_ADJUSTMENT_FAILED = "swarm.adaptive.failed"

    RISK_ASSESSMENT_STARTED = "swarm.risk.started"
    RISK_ASSESSMENT_COMPLETED = "swarm.risk.completed"
    RISK_ASSESSMENT_FAILED = "swarm.risk.failed"

    CONSENSUS_STARTED = "swarm.consensus.started"
    CONSENSUS_COMPLETED = "swarm.consensus.completed"
    CONSENSUS_FAILED = "swarm.consensus.failed"

    INFERENCE_STARTED = "swarm.inference.started"
    INFERENCE_COMPLETED = "swarm.inference.completed"
    INFERENCE_FAILED = "swarm.inference.failed"

    CONTENT_PRODUCTION_STARTED = "swarm.content.started"
    CONTENT_PRODUCTION_COMPLETED = "swarm.content.completed"
    CONTENT_PRODUCTION_FAILED = "swarm.content.failed"

    ACTIVATION_COMPLETED = "swarm.activation.completed"
    ACTIVATION_FAILED = "swarm.activation.failed"

    PHASE_TIMEOUT = "swarm.phase.timeout"
    PHASE_RETRY = "swarm.phase.retry"
    PHASE_ROLLBACK = "swarm.phase.rollback"

    CONTEXT_INCONSISTENCY_DETECTED = "swarm.context.inconsistency"
    PROPAGATION_FAILURE_DETECTED = "swarm.propagation.failure"
    BOTTLENECK_DETECTED = "swarm.bottleneck.detected"
    RACE_CONDITION_DETECTED = "swarm.race_condition.detected"

    SWARM_SYNCHRONIZED = "swarm.synchronized"
    SWARM_DEGRADED = "swarm.degraded"
    SWARM_RECOVERED = "swarm.recovered"


PHASE_EVENT_MAP: dict[SwarmPhase, tuple[str, str, str]] = {
    SwarmPhase.ENTERING: ("", "", ""),
    SwarmPhase.CONTEXT_LOADING: (
        SwarmEventType.CONTEXT_LOAD_STARTED,
        SwarmEventType.CONTEXT_LOAD_COMPLETED,
        SwarmEventType.CONTEXT_LOAD_FAILED,
    ),
    SwarmPhase.MEMORY_INIT: (
        SwarmEventType.MEMORY_INIT_STARTED,
        SwarmEventType.MEMORY_INIT_COMPLETED,
        SwarmEventType.MEMORY_INIT_FAILED,
    ),
    SwarmPhase.PEDAGOGICAL_ANALYSIS: (
        SwarmEventType.PEDAGOGICAL_ANALYSIS_STARTED,
        SwarmEventType.PEDAGOGICAL_ANALYSIS_COMPLETED,
        SwarmEventType.PEDAGOGICAL_ANALYSIS_FAILED,
    ),
    SwarmPhase.ADAPTIVE_ADJUSTMENT: (
        SwarmEventType.ADAPTIVE_ADJUSTMENT_STARTED,
        SwarmEventType.ADAPTIVE_ADJUSTMENT_COMPLETED,
        SwarmEventType.ADAPTIVE_ADJUSTMENT_FAILED,
    ),
    SwarmPhase.RISK_ASSESSMENT: (
        SwarmEventType.RISK_ASSESSMENT_STARTED,
        SwarmEventType.RISK_ASSESSMENT_COMPLETED,
        SwarmEventType.RISK_ASSESSMENT_FAILED,
    ),
    SwarmPhase.CONSENSUS: (
        SwarmEventType.CONSENSUS_STARTED,
        SwarmEventType.CONSENSUS_COMPLETED,
        SwarmEventType.CONSENSUS_FAILED,
    ),
    SwarmPhase.INFERENCE: (
        SwarmEventType.INFERENCE_STARTED,
        SwarmEventType.INFERENCE_COMPLETED,
        SwarmEventType.INFERENCE_FAILED,
    ),
    SwarmPhase.CONTENT_PRODUCTION: (
        SwarmEventType.CONTENT_PRODUCTION_STARTED,
        SwarmEventType.CONTENT_PRODUCTION_COMPLETED,
        SwarmEventType.CONTENT_PRODUCTION_FAILED,
    ),
    SwarmPhase.ACTIVE: (
        SwarmEventType.ACTIVATION_COMPLETED,
        SwarmEventType.ACTIVATION_COMPLETED,
        SwarmEventType.ACTIVATION_FAILED,
    ),
}


@dataclass
class SwarmEvent:
    event_id: str
    event_type: SwarmEventType
    correlation_id: str
    causation_id: str | None
    parent_event_id: str | None
    context_key: str
    student_id: str
    course_id: str
    phase: str
    payload: dict[str, Any]
    sequence: int
    created_at: str
    duration_ms: float = 0.0
    propagated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "parent_event_id": self.parent_event_id,
            "context_key": self.context_key,
            "phase": self.phase,
            "payload": self.payload,
            "sequence": self.sequence,
            "created_at": self.created_at,
            "duration_ms": self.duration_ms,
            "propagated": self.propagated,
        }


class SwarmEventBus:
    """In-process event bus with causation tracking and propagation failure detection.

    Features:
    - Causal chains: every event links to its parent via causation_id
    - Phase scoping: events are tagged with the originating phase
    - Propagation tracking: tracks which events were delivered to handlers
    - Max depth guard: prevents runaway propagation (MAX_CAUSATION_DEPTH)
    """

    MAX_CAUSATION_DEPTH = 100

    def __init__(self):
        self._lock = threading.Lock()
        self._handlers: dict[SwarmEventType, list[Callable]] = {}
        self._events: list[SwarmEvent] = []
        self._sequence: dict[str, int] = {}
        self._propagation_counts: dict[str, int] = {}

    def publish(
        self,
        event_type: SwarmEventType,
        context_key: str,
        student_id: str,
        course_id: str,
        phase: str,
        payload: dict[str, Any] | None = None,
        causation_id: str | None = None,
        parent_event_id: str | None = None,
    ) -> SwarmEvent:
        correlation_id = self._get_or_create_correlation(context_key)
        seq = self._next_sequence(correlation_id)

        event = SwarmEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            correlation_id=correlation_id,
            causation_id=causation_id,
            parent_event_id=parent_event_id,
            context_key=context_key,
            student_id=student_id,
            course_id=course_id,
            phase=phase,
            payload=payload or {},
            sequence=seq,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self._events.append(event)
            self._propagation_counts[event.event_id] = 0

        self._deliver(event)

        if self._propagation_counts.get(event.event_id, 0) == 0:
            event.propagated = False
            logger.warning(
                "SwarmEvent[%s] %s: no handlers — possible propagation failure",
                event.event_id[:8], event_type.value,
            )

        # Check causation depth
        if causation_id:
            depth = self._calculate_depth(event)
            if depth > self.MAX_CAUSATION_DEPTH:
                logger.error(
                    "Causation depth %d exceeded max %d for event %s. "
                    "Possible propagation storm.",
                    depth, self.MAX_CAUSATION_DEPTH, event.event_id[:8],
                )

        return event

    def subscribe(self, event_type: SwarmEventType, handler: Callable) -> None:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Callable) -> None:
        for et in SwarmEventType:
            self.subscribe(et, handler)

    def unsubscribe(self, event_type: SwarmEventType, handler: Callable) -> None:
        with self._lock:
            handlers = self._handlers.get(event_type, [])
            if handler in handlers:
                handlers.remove(handler)

    def get_events(
        self,
        context_key: str | None = None,
        event_type: SwarmEventType | None = None,
        phase: str | None = None,
        limit: int = 100,
    ) -> list[SwarmEvent]:
        with self._lock:
            result = list(self._events)
        if context_key:
            result = [e for e in result if e.context_key == context_key]
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if phase:
            result = [e for e in result if e.phase == phase]
        return sorted(result, key=lambda e: e.sequence)[-limit:]

    def get_causation_chain(self, event_id: str) -> list[SwarmEvent]:
        chain = []
        current_id = event_id
        seen: set[str] = set()
        while current_id and current_id not in seen:
            seen.add(current_id)
            with self._lock:
                event = next((e for e in self._events if e.event_id == current_id), None)
            if event is None:
                break
            chain.append(event)
            current_id = event.causation_id
        return chain

    def detect_propagation_failures(
        self, context_key: str, grace_period_ms: float = 5000,
    ) -> list[dict[str, Any]]:
        failures = []
        now = time.time() * 1000
        for event in self._events:
            if event.context_key != context_key:
                continue
            if event.propagated:
                continue
            event_time = self._parse_time(event.created_at)
            if now - event_time > grace_period_ms:
                failures.append({
                    "event_id": event.event_id,
                    "event_type": event.event_type.value,
                    "sequence": event.sequence,
                    "phase": event.phase,
                    "created_at": event.created_at,
                    "age_ms": now - event_time,
                    "reason": "event_not_propagated",
                })
        return failures

    def detect_event_storm(
        self, context_key: str, window_ms: float = 5000, threshold: int = 50,
    ) -> list[dict[str, Any]]:
        now = time.time() * 1000
        cutoff = now - window_ms
        recent = [
            e for e in self._events
            if e.context_key == context_key and self._parse_time(e.created_at) > cutoff
        ]
        if len(recent) > threshold:
            return [{
                "event_count": len(recent),
                "window_ms": window_ms,
                "threshold": threshold,
                "events": [{"id": e.event_id[:8], "type": e.event_type.value} for e in recent[:20]],
            }]
        return []

    def _deliver(self, event: SwarmEvent) -> None:
        with self._lock:
            handlers = list(self._handlers.get(event.event_type, []))
            all_handlers = list(self._handlers.get(None, []))
        delivered = 0
        for handler in handlers + all_handlers:
            try:
                handler(event)
                delivered += 1
            except Exception as e:
                logger.error("Handler failed for %s: %s", event.event_type.value, e)
        if delivered > 0:
            event.propagated = True
            with self._lock:
                self._propagation_counts[event.event_id] = delivered

    def _get_or_create_correlation(self, context_key: str) -> str:
        with self._lock:
            for event in reversed(self._events):
                if event.context_key == context_key:
                    return event.correlation_id
        return str(uuid.uuid4())

    def _next_sequence(self, correlation_id: str) -> int:
        with self._lock:
            self._sequence[correlation_id] = self._sequence.get(correlation_id, 0) + 1
            return self._sequence[correlation_id]

    def _calculate_depth(self, event: SwarmEvent) -> int:
        return len(self.get_causation_chain(event.event_id))

    @staticmethod
    def _parse_time(iso_str: str) -> float:
        try:
            return datetime.fromisoformat(iso_str).timestamp() * 1000
        except Exception:
            return 0.0


# Module-level singleton
swarm_event_bus = SwarmEventBus()
