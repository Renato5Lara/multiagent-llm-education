"""
Swarm Anomaly Detectors.

BottleneckDetector: measures phase duration, identifies slowdowns
RaceConditionDetector: detects concurrent modifications to same context
ContextInconsistencyDetector: verifies context state across layers
PropagationFailureDetector: detects dropped/corrupted events in causation chains
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.swarm.lifecycle import PHASE_CONFIG, PHASE_ORDER, SwarmPhase
from app.swarm.events import SwarmEvent, SwarmEventBus, SwarmEventType

logger = logging.getLogger(__name__)


class BottleneckDetector:
    """Detects phase bottlenecks by measuring execution duration against baselines.

    Signals:
    - Phase duration > 2x baseline → WARNING
    - Phase duration > 3x baseline → CRITICAL
    - Non-linear scaling: phase N takes longer than phase N-1 + phase N-2 combined → chain slowdown
    """

    def __init__(self, baseline_p99_ms: dict[str, float] | None = None):
        self._baselines: dict[str, float] = baseline_p99_ms or {
            "entering": 2000,
            "context_loading": 5000,
            "memory_init": 2000,
            "pedagogical_analysis": 8000,
            "adaptive_adjustment": 5000,
            "risk_assessment": 4000,
            "consensus": 10000,
            "inference": 5000,
            "content_production": 8000,
            "active": 2000,
        }
        self._phase_durations: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_duration(self, phase: str, duration_ms: float) -> None:
        with self._lock:
            self._phase_durations[phase].append(duration_ms)

    def detect(self, lifecycle_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        signals = []
        phase_history = lifecycle_snapshot.get("phase_history", [])

        for i, entry in enumerate(phase_history):
            phase = entry["phase"]
            status = entry.get("status", "")
            if status != "completed":
                continue

            started = entry.get("started_at")
            completed = entry.get("completed_at")
            if not started or not completed:
                continue

            try:
                start = datetime.fromisoformat(started)
                end = datetime.fromisoformat(completed)
                duration_ms = (end - start).total_seconds() * 1000
            except (ValueError, TypeError):
                continue

            self.record_duration(phase, duration_ms)

            baseline = self._baselines.get(phase, 5000)

            if duration_ms > baseline * 3:
                signals.append({
                    "detector": "bottleneck",
                    "severity": "critical",
                    "phase": phase,
                    "duration_ms": duration_ms,
                    "baseline_ms": baseline,
                    "ratio": round(duration_ms / baseline, 2),
                    "message": f"Phase '{phase}' took {duration_ms:.0f}ms ({duration_ms/baseline:.1f}x baseline)",
                    "recommendation": f"Investigate {phase} phase: consider parallelizing or optimizing",
                })
            elif duration_ms > baseline * 2:
                signals.append({
                    "detector": "bottleneck",
                    "severity": "warning",
                    "phase": phase,
                    "duration_ms": duration_ms,
                    "baseline_ms": baseline,
                    "ratio": round(duration_ms / baseline, 2),
                    "message": f"Phase '{phase}' took {duration_ms:.0f}ms (2x baseline)",
                    "recommendation": f"Monitor {phase} phase for degradation",
                })

        # Chain slowdown: phase N slower than (N-1 + N-2) combined
        for i in range(2, len(phase_history)):
            n = phase_history[i]
            n1 = phase_history[i - 1]
            n2 = phase_history[i - 2]
            if n.get("status") != "completed":
                continue
            try:
                dn = self._parse_duration(n)
                dn1 = self._parse_duration(n1)
                dn2 = self._parse_duration(n2)
                if dn is not None and dn1 is not None and dn2 is not None and dn > (dn1 + dn2) * 1.5:
                    signals.append({
                        "detector": "bottleneck",
                        "severity": "warning",
                        "phase": n["phase"],
                        "duration_ms": dn,
                        "message": f"Phase '{n['phase']}' ({dn:.0f}ms) slower than N-1 ({dn1:.0f}ms) + N-2 ({dn2:.0f}ms) combined",
                        "recommendation": "Check for cascading delay pattern",
                    })
            except (ValueError, TypeError):
                continue

        return signals

    def get_phase_stats(self, phase: str) -> dict[str, float]:
        with self._lock:
            durations = self._phase_durations.get(phase, [])
            if not durations:
                return {"min": 0, "max": 0, "avg": 0, "p50": 0, "p99": 0, "count": 0}
            sorted_d = sorted(durations)
            return {
                "min": sorted_d[0],
                "max": sorted_d[-1],
                "avg": sum(sorted_d) / len(sorted_d),
                "p50": sorted_d[len(sorted_d) // 2],
                "p99": sorted_d[int(len(sorted_d) * 0.99)],
                "count": len(sorted_d),
            }

    @staticmethod
    def _parse_duration(entry: dict) -> float | None:
        started = entry.get("started_at")
        completed = entry.get("completed_at")
        if started and completed:
            try:
                return (datetime.fromisoformat(completed) - datetime.fromisoformat(started)).total_seconds() * 1000
            except Exception:
                return None
        return None


class RaceConditionDetector:
    """Detects race conditions by analyzing event ordering and concurrent access.

    Signals:
    - Two events with same correlation_id processed in overlapping time windows
    - Out-of-order events: sequence numbers don't match expected order
    - Concurrent phase transitions for same context
    """

    def __init__(self):
        self._event_windows: dict[str, list[tuple[float, float]]] = defaultdict(list)
        self._lock = threading.Lock()

    def detect(self, events: list[SwarmEvent]) -> list[dict[str, Any]]:
        signals = []

        # Group by correlation_id
        by_correlation: dict[str, list[SwarmEvent]] = defaultdict(list)
        for e in events:
            by_correlation[e.correlation_id].append(e)

        for corr_id, corr_events in by_correlation.items():
            corr_events.sort(key=lambda e: e.sequence)

            # 1. Check sequence gaps and reversals
            for i in range(1, len(corr_events)):
                if corr_events[i].sequence <= corr_events[i - 1].sequence:
                    signals.append({
                        "detector": "race_condition",
                        "severity": "critical",
                        "correlation_id": corr_id[:12],
                        "message": (
                            f"Sequence reversal: event {corr_events[i].event_id[:8]} "
                            f"(seq={corr_events[i].sequence}) after "
                            f"{corr_events[i-1].event_id[:8]} (seq={corr_events[i-1].sequence})"
                        ),
                        "events": [corr_events[i - 1].event_id[:8], corr_events[i].event_id[:8]],
                        "recommendation": "Check for concurrent event publishers on same context",
                    })

            # 2. Check overlapping phase transitions
            phase_transitions = [
                e for e in corr_events
                if e.event_type in (
                    SwarmEventType.CONTEXT_LOAD_STARTED,
                    SwarmEventType.PEDAGOGICAL_ANALYSIS_STARTED,
                    SwarmEventType.ADAPTIVE_ADJUSTMENT_STARTED,
                    SwarmEventType.CONSENSUS_STARTED,
                )
            ]
            for i in range(len(phase_transitions)):
                for j in range(i + 1, min(i + 3, len(phase_transitions))):
                    t_i = self._parse_ms(phase_transitions[i].created_at)
                    t_j = self._parse_ms(phase_transitions[j].created_at)
                    if abs(t_j - t_i) < 100 and phase_transitions[i].phase != phase_transitions[j].phase:
                        signals.append({
                            "detector": "race_condition",
                            "severity": "warning",
                            "correlation_id": corr_id[:12],
                            "message": (
                                f"Near-simultaneous phase transitions: "
                                f"{phase_transitions[i].phase} and {phase_transitions[j].phase} "
                                f"within {abs(t_j - t_i):.0f}ms"
                            ),
                            "events": [phase_transitions[i].event_id[:8], phase_transitions[j].event_id[:8]],
                            "recommendation": "Ensure phase gating is working correctly",
                        })

        return signals

    @staticmethod
    def _parse_ms(iso_str: str) -> float:
        try:
            return datetime.fromisoformat(iso_str).timestamp() * 1000
        except Exception:
            return 0.0


class ContextInconsistencyDetector:
    """Detects inconsistencies between layers of the educational context.

    Checks:
    - EducationalContext DB state vs lifecycle state
    - SharedMemory baseline vs actual context parameters
    - swarm_config in context vs agents that actually ran
    - Phase preconditions vs achieved postconditions
    """

    def detect_from_lifecycle(self, lifecycle_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
        signals = []
        phases = lifecycle_snapshot.get("phases", {})
        phase_history = lifecycle_snapshot.get("phase_history", [])
        achieved = lifecycle_snapshot.get("metadata", {}).get("achieved_postconditions", [])

        # 1. Phase status consistency
        for phase_name, status in phases.items():
            if status not in ("pending", "in_progress", "completed", "failed", "timed_out", "rolled_back", "skipped"):
                signals.append({
                    "detector": "context_inconsistency",
                    "severity": "warning",
                    "message": f"Phase '{phase_name}' has unknown status '{status}'",
                    "recommendation": "Check lifecycle state machine integrity",
                })

        # 2. Completed phases should have history entries
        for phase_name, status in phases.items():
            if status == "completed":
                has_history = any(
                    h["phase"] == phase_name and h.get("status") == "completed"
                    for h in phase_history
                )
                if not has_history:
                    signals.append({
                        "detector": "context_inconsistency",
                        "severity": "critical",
                        "message": f"Phase '{phase_name}' marked completed but no history entry",
                        "recommendation": "Lifecycle state may be corrupted",
                    })

        # 3. Phase ordering consistency
        prev_completed = False
        for phase in PHASE_ORDER:
            status = phases.get(phase.value, "pending")
            if status == "completed" and not prev_completed:
                if phase != SwarmPhase.ENTERING:
                    signals.append({
                        "detector": "context_inconsistency",
                        "severity": "critical",
                        "phase": phase.value,
                        "message": f"Phase '{phase.value}' completed but previous phase not completed",
                        "recommendation": "Possible race condition in state machine",
                    })
            if status == "completed":
                prev_completed = True
            elif status == "failed":
                prev_completed = False

        # 4. Postcondition completeness
        for phase in PHASE_ORDER:
            config = PHASE_CONFIG.get(phase, {})
            expected = config.get("postconditions", [])
            if phases.get(phase.value) == "completed":
                missing = [p for p in expected if p not in achieved]
                if missing:
                    signals.append({
                        "detector": "context_inconsistency",
                        "severity": "warning",
                        "phase": phase.value,
                        "message": f"Phase '{phase.value}' completed but missing postconditions: {missing}",
                        "recommendation": "Phase completion may be premature",
                    })

        return signals

    def detect_from_db(
        self,
        db_context: dict[str, Any],
        lifecycle_snapshot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        signals = []

        # 1. Status mismatch: DB vs lifecycle
        db_status = db_context.get("status", "")
        lifecycle_active = lifecycle_snapshot.get("active", False)

        if db_status == "active" and not lifecycle_active:
            signals.append({
                "detector": "context_inconsistency",
                "severity": "critical",
                "message": f"DB context is 'active' but lifecycle not active",
                "recommendation": "Lifecycle may have been interrupted without DB rollback",
            })

        # 2. swarm_config vs lifecycle phase
        swarm_agents = db_context.get("swarm_config", {}).get("agents", [])
        if "pseudocode_analyzer" in swarm_agents:
            ped_phase = lifecycle_snapshot.get("phases", {}).get("pedagogical_analysis", "")
            if ped_phase not in ("completed", "in_progress"):
                signals.append({
                    "detector": "context_inconsistency",
                    "severity": "warning",
                    "message": "Programming swarm configured but pedagogical phase not started",
                    "recommendation": "Programming courses should trigger pedagogical analysis",
                })

        return signals


class PropagationFailureDetector:
    """Detects failures in event propagation across the swarm.

    Signals:
    - Events not delivered to any handler (orphaned events)
    - Causation chain broken (missing intermediate events)
    - Event ordering violations (sequence gaps)
    - Handler exceptions during delivery
    """

    def __init__(self):
        self._handler_errors: dict[str, list[dict]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_handler_error(self, event_type: str, handler: str, error: str) -> None:
        with self._lock:
            self._handler_errors[event_type].append({
                "handler": handler,
                "error": error,
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            })

    def detect(self, events: list[SwarmEvent]) -> list[dict[str, Any]]:
        signals = []

        # 1. Orphaned events (not propagated)
        orphaned = [e for e in events if not e.propagated]
        if len(orphaned) > 3:
            signals.append({
                "detector": "propagation_failure",
                "severity": "warning",
                "message": f"{len(orphaned)} events not propagated to any handler",
                "orphaned_events": [{"id": e.event_id[:8], "type": e.event_type.value, "phase": e.phase} for e in orphaned[:10]],
                "recommendation": "Check event bus subscriptions",
            })

        # 2. Causation chain breaks
        by_correlation: dict[str, list[SwarmEvent]] = defaultdict(list)
        for e in events:
            by_correlation[e.correlation_id].append(e)

        for corr_id, corr_events in by_correlation.items():
            corr_events.sort(key=lambda e: e.sequence)

            # Check for missing causation links
            for i in range(1, len(corr_events)):
                expected_cause = corr_events[i - 1].event_id
                actual_cause = corr_events[i].causation_id
                if actual_cause is not None and actual_cause != expected_cause:
                    # Check if the actual_cause exists
                    exists = any(e.event_id == actual_cause for e in corr_events)
                    if not exists:
                        signals.append({
                            "detector": "propagation_failure",
                            "severity": "critical",
                            "correlation_id": corr_id[:12],
                            "message": (
                                f"Causation chain broken: event {corr_events[i].event_id[:8]} "
                                f"references non-existent parent {actual_cause[:8]}"
                            ),
                            "events": [corr_events[i].event_id[:8]],
                            "recommendation": "Event may have been lost during transmission",
                        })

            # Check for sequence gaps
            for i in range(1, len(corr_events)):
                expected_seq = corr_events[i - 1].sequence + 1
                actual_seq = corr_events[i].sequence
                if actual_seq > expected_seq + 1:
                    signals.append({
                        "detector": "propagation_failure",
                        "severity": "warning",
                        "correlation_id": corr_id[:12],
                        "message": (
                            f"Sequence gap: events {corr_events[i-1].sequence} → {actual_seq} "
                            f"(expected {expected_seq})"
                        ),
                        "gap_size": actual_seq - expected_seq,
                        "recommendation": "Events may have been dropped",
                    })

        # 3. Handler errors
        with self._lock:
            for event_type, errors in self._handler_errors.items():
                if len(errors) > 5:
                    signals.append({
                        "detector": "propagation_failure",
                        "severity": "critical",
                        "event_type": event_type,
                        "message": f"{len(errors)} handler errors for {event_type}",
                        "samples": errors[:5],
                        "recommendation": "Check event handlers for exceptions",
                    })

        return signals


# Module-level singletons
bottleneck_detector = BottleneckDetector()
race_condition_detector = RaceConditionDetector()
context_inconsistency_detector = ContextInconsistencyDetector()
propagation_failure_detector = PropagationFailureDetector()
