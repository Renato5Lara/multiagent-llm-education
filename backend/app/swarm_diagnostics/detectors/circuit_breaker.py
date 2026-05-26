"""
Circuit Breaker Detectors — Swarm-level anomaly detection for the
circuit breaker system.

Detectors:
    - CircuitBreakerRetryStormDetector
      Detects rapid open/close cycling or excessive failures in a single
      agent's breaker within a time window (retry storm per agent).

    - CascadingFailureDetector
      Detects when one agent's circuit opening correlates with downstream
      agent circuit openings (cascading failure across agents).

    - RecoveryInstabilityDetector
      Detects breaker state oscillation: rapid open → half-open → open
      cycles within a short window (recovery instability).

Integration:
    Each detector follows the BaseDetector ABC and can be registered
    in the SwarmDiagnosticsEngine alongside the other 16 detectors.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


# ── Circuit Breaker Retry Storm Detector ──────────────────────────────


class CircuitBreakerRetryStormDetector(BaseDetector):
    """Detects retry storms at the circuit breaker level.

    A retry storm occurs when a single agent's circuit breaker records
    an elevated number of failures or state transitions within a time
    window, indicating the agent is stuck in a failure loop.

    Signals:
        - circuit_breaker_storm: rapid open/close cycling or excessive
          failure count for a single agent
    """

    name = "circuit_breaker_retry_storm"

    def __init__(
        self,
        max_failures_per_window: int = 10,
        window_seconds: float = 60.0,
        min_transitions_for_storm: int = 5,
    ):
        self.max_failures_per_window = max_failures_per_window
        self.window_seconds = window_seconds
        self.min_transitions_for_storm = min_transitions_for_storm

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.window_seconds)

        # Filter to circuit-breaker-related events
        cb_events = [
            e for e in events
            if e.created_at and e.created_at >= cutoff
            and (
                "circuit_breaker" in e.event_type.lower()
                or "breaker" in e.event_type.lower()
                or e.source == "circuit_breaker"
            )
        ]
        if not cb_events:
            return signals

        # Group by agent source
        agent_failures: dict[str, int] = defaultdict(int)
        agent_transitions: dict[str, list[DiagnosticEvent]] = defaultdict(list)

        for e in cb_events:
            # Extract agent name from payload or source
            agent = (
                (e.payload or {}).get("agent")
                or e.source
                or "unknown"
            )
            if e.error is not None or (e.payload or {}).get("state") in ("open", "isolated"):
                agent_failures[agent] += 1
            agent_transitions[agent].append(e)

        # Check each agent for storm conditions
        for agent, failure_count in agent_failures.items():
            if failure_count >= self.max_failures_per_window:
                transitions = agent_transitions.get(agent, [])
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.RETRY_STORM_AGENT,
                    severity=Severity.CRITICAL,
                    scope=f"agent:{agent}",
                    title=f"Circuit breaker retry storm: {agent}",
                    description=(
                        f"Agent '{agent}' recorded {failure_count} circuit breaker "
                        f"failures in the last {self.window_seconds:.0f}s "
                        f"(threshold={self.max_failures_per_window})"
                    ),
                    metric_value=float(failure_count),
                    threshold=float(self.max_failures_per_window),
                    evidence={
                        "agent": agent,
                        "failure_count": failure_count,
                        "window_seconds": self.window_seconds,
                        "transition_events": [
                            {
                                "event_type": t.event_type,
                                "state": (t.payload or {}).get("state"),
                                "error": t.error,
                                "created_at": t.created_at.isoformat() if t.created_at else None,
                            }
                            for t in transitions[-10:]  # last 10
                        ],
                    },
                    recommendation=(
                        f"Investigate agent '{agent}' for recurring failures. "
                        "Consider increasing failure threshold, extending recovery "
                        "timeout, or manually isolating the agent."
                    ),
                ))

        # Detect state transition storms (rapid open/close cycling)
        for agent, transitions in agent_transitions.items():
            if len(transitions) >= self.min_transitions_for_storm:
                states = [
                    (t.payload or {}).get("state", "unknown")
                    for t in transitions
                ]
                # Count state changes
                changes = sum(
                    1 for i in range(1, len(states)) if states[i] != states[i - 1]
                )
                if changes >= self.min_transitions_for_storm:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.RECOVERY_INSTABILITY,
                        severity=Severity.WARNING,
                        scope=f"agent:{agent}",
                        title=f"Rapid circuit breaker cycling: {agent}",
                        description=(
                            f"Agent '{agent}' had {len(transitions)} state transitions "
                            f"({changes} changes) in the last {self.window_seconds:.0f}s. "
                            "This indicates recovery instability."
                        ),
                        metric_value=float(changes),
                        threshold=float(self.min_transitions_for_storm),
                        evidence={
                            "agent": agent,
                            "total_transitions": len(transitions),
                            "state_changes": changes,
                            "state_sequence": states[-20:],
                        },
                        recommendation=(
                            f"Circuit breaker for '{agent}' is oscillating. "
                            "Consider increasing consecutive_successes_to_close "
                            "or extending half_open_max_calls."
                        ),
                    ))

        return signals


# ── Cascading Failure Detector ────────────────────────────────────────


class CascadingFailureDetector(BaseDetector):
    """Detects cascading circuit breaker failures across agents.

    A cascading failure occurs when one agent's circuit opening triggers
    a chain reaction causing other agents' circuits to open in sequence.

    Detection strategy:
        1. Collect breaker_open events in the window
        2. Sort by timestamp
        3. Check for sequences where opens cluster within a time window
        4. Flag when 2+ distinct agents open within a short window

    Signals:
        - cascading_failure: multiple agents' circuits opening in sequence
    """

    name = "cascading_failure"

    def __init__(
        self,
        cascade_window_seconds: float = 30.0,
        min_agents_for_cascade: int = 2,
        max_agent_gap_seconds: float = 5.0,
    ):
        self.cascade_window_seconds = cascade_window_seconds
        self.min_agents_for_cascade = min_agents_for_cascade
        self.max_agent_gap_seconds = max_agent_gap_seconds

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.cascade_window_seconds)

        # Collect breaker open events
        open_events: list[tuple[datetime, str, str, dict]] = []
        for e in events:
            if not e.created_at or e.created_at < cutoff:
                continue
            is_open = (
                (e.payload or {}).get("state") == "open"
                and (e.payload or {}).get("circuit_breaker") is True
            )
            if not is_open:
                continue
            agent = (
                (e.payload or {}).get("agent")
                or e.source
                or "unknown"
            )
            open_events.append((e.created_at, agent, e.event_type, e.payload or {}))

        if len(open_events) < self.min_agents_for_cascade:
            return signals

        # Sort by timestamp
        open_events.sort(key=lambda x: x[0])

        # Look for cascading clusters
        cascade_groups: list[list[tuple]] = []
        current_group: list[tuple] = [open_events[0]]

        for i in range(1, len(open_events)):
            gap = (open_events[i][0] - open_events[i - 1][0]).total_seconds()
            if gap <= self.max_agent_gap_seconds:
                current_group.append(open_events[i])
            else:
                if len(current_group) >= self.min_agents_for_cascade:
                    cascade_groups.append(current_group)
                current_group = [open_events[i]]

        if len(current_group) >= self.min_agents_for_cascade:
            cascade_groups.append(current_group)

        for group in cascade_groups:
            agents_in_group = list(set(a for _, a, _, _ in group))
            if len(agents_in_group) < self.min_agents_for_cascade:
                continue

            span = (group[-1][0] - group[0][0]).total_seconds()
            signals.append(AnomalySignal(
                anomaly_id=str(uuid.uuid4()),
                detector_name=self.name,
                anomaly_type=AnomalyType.CASCADING_FAILURE,
                severity=Severity.CRITICAL,
                scope="global",
                title=f"Cascading circuit breaker failure: {len(agents_in_group)} agents",
                description=(
                    f"{len(agents_in_group)} agents' circuits opened within "
                    f"{span:.1f}s: {', '.join(agents_in_group)}. "
                    "This indicates a cascading failure pattern."
                ),
                metric_value=float(len(agents_in_group)),
                threshold=float(self.min_agents_for_cascade),
                evidence={
                    "agents": agents_in_group,
                    "cascade_span_seconds": span,
                    "opening_events": [
                        {
                            "agent": a,
                            "timestamp": t.isoformat() if t else None,
                            "event_type": et,
                        }
                        for t, a, et, _ in group
                    ],
                },
                recommendation=(
                    "Cascading circuit breaker failures detected. "
                    "Investigate shared dependencies, upstream agent health, "
                    "and consider implementing bulkhead isolation between agents."
                ),
            ))

        return signals


# ── Recovery Instability Detector ─────────────────────────────────────


class RecoveryInstabilityDetector(BaseDetector):
    """Detects breaker state oscillation suggesting recovery instability.

    A breaker that rapidly transitions open -> half-open -> open
    (within a short window) is unstable.  This detector identifies
    agents whose breakers are stuck in recovery loops.

    Signals:
        - recovery_instability: breaker toggling between open/half-open
        - repeated_isolation: agent repeatedly reaching isolation state
    """

    name = "recovery_instability"

    def __init__(
        self,
        instability_window_seconds: float = 120.0,
        min_open_half_open_cycles: int = 3,
        consecutively_isolated_threshold: int = 2,
    ):
        self.instability_window_seconds = instability_window_seconds
        self.min_open_half_open_cycles = min_open_half_open_cycles
        self.consecutively_isolated_threshold = consecutively_isolated_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=self.instability_window_seconds)

        # Collect breaker state transitions
        transitions_by_agent: dict[str, list[dict]] = defaultdict(list)
        for e in events:
            if not e.created_at or e.created_at < cutoff:
                continue
            payload = e.payload or {}
            if not payload.get("circuit_breaker") and "breaker" not in e.source.lower():
                continue
            state = payload.get("state")
            if state not in ("open", "half_open", "closed", "isolated"):
                # Try to infer from event type
                if "open" in e.event_type.lower():
                    state = "open"
                elif "close" in e.event_type.lower():
                    state = "closed"
                elif "half" in e.event_type.lower():
                    state = "half_open"
                elif "isolat" in e.event_type.lower():
                    state = "isolated"
                else:
                    continue
            agent = payload.get("agent") or e.source or "unknown"
            transitions_by_agent[agent].append({
                "state": state,
                "timestamp": e.created_at,
                "event_type": e.event_type,
                "error": e.error,
            })

        for agent, transitions in transitions_by_agent.items():
            if len(transitions) < self.min_open_half_open_cycles:
                continue

            # Sort by timestamp
            transitions.sort(key=lambda x: x["timestamp"])

            # Count open-half_open cycles
            open_half_open_cycles = 0
            isolated_count = 0
            prev_state = None
            for t in transitions:
                if t["state"] == "open" and prev_state == "half_open":
                    open_half_open_cycles += 1
                if t["state"] == "half_open" and prev_state == "open":
                    open_half_open_cycles += 1
                if t["state"] == "isolated":
                    isolated_count += 1
                prev_state = t["state"]

            # Detect oscillation
            if open_half_open_cycles >= self.min_open_half_open_cycles:
                span = (
                    transitions[-1]["timestamp"] - transitions[0]["timestamp"]
                ).total_seconds()
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.RECOVERY_INSTABILITY,
                    severity=Severity.WARNING,
                    scope=f"agent:{agent}",
                    title=f"Recovery instability: {agent}",
                    description=(
                        f"Agent '{agent}' has {open_half_open_cycles} open/half-open "
                        f"cycles in {span:.0f}s ({len(transitions)} total transitions). "
                        "The circuit breaker cannot stabilize."
                    ),
                    metric_value=float(open_half_open_cycles),
                    threshold=float(self.min_open_half_open_cycles),
                    evidence={
                        "agent": agent,
                        "open_half_open_cycles": open_half_open_cycles,
                        "total_transitions": len(transitions),
                        "span_seconds": span,
                        "state_sequence": [t["state"] for t in transitions[-30:]],
                    },
                    recommendation=(
                        f"Circuit breaker for '{agent}' shows recovery instability. "
                        "Increase recovery_timeout_ms, half_open_max_calls, or "
                        "consecutive_successes_to_close. Consider manual intervention."
                    ),
                ))

            # Detect repeated isolation
            if isolated_count >= self.consecutively_isolated_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.RECOVERY_INSTABILITY,
                    severity=Severity.CRITICAL,
                    scope=f"agent:{agent}",
                    title=f"Repeated agent isolation: {agent}",
                    description=(
                        f"Agent '{agent}' has been isolated {isolated_count} times. "
                        "The agent may be permanently degraded."
                    ),
                    metric_value=float(isolated_count),
                    threshold=float(self.consecutively_isolated_threshold),
                    evidence={
                        "agent": agent,
                        "isolated_count": isolated_count,
                        "transitions": [
                            {"state": t["state"], "timestamp": t["timestamp"].isoformat() if t["timestamp"] else None}
                            for t in transitions[-20:]
                        ],
                    },
                    recommendation=(
                        f"Agent '{agent}' repeatedly reaches isolation state. "
                        "Investigate root cause of persistent failures. "
                        "Consider removing the agent from the swarm for manual debugging."
                    ),
                ))

        return signals
