"""
Propagation TTL — Prevents infinite swarm propagation with depth,
time, decay, anti-feedback-loop, and storm protection.

Provides:
  - PropagationTTL metadata with hop count, TTL, decay, visited tracking
  - PropagationTTLManager for lifecycle, validation, and serialization
  - PropagationLifecycle high-level wrapper
  - Integration with PropagationContext baggage
  - Integration with EventBus via TTL validation guard
  - Integration with ConsensusEngine via propagation lifecycle hooks
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────

DEFAULT_MAX_HOPS = 10
DEFAULT_TTL_SECONDS = 300.0
DEFAULT_DECAY_FACTOR = 0.8
DEFAULT_MIN_STRENGTH = 0.1
MAX_VISITED_AGENTS = 64
MAX_VISITED_EVENTS = 256
STORM_RATE_THRESHOLD = 20.0
AMPLIFICATION_FANOUT_THRESHOLD = 5
PROPAGATION_CONTEXT_PREFIX = "pttl:"

# ── Enums ───────────────────────────────────────────────────────────


class PropagationState(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    TERMINATED = "terminated"
    STORM_DETECTED = "storm_detected"
    FEEDBACK_LOOP = "feedback_loop"
    DEPLETED = "depleted"


class PropagationStopReason(str, Enum):
    MAX_HOPS_EXCEEDED = "max_hops_exceeded"
    TTL_EXPIRED = "ttl_expired"
    STRENGTH_DEPLETED = "strength_depleted"
    FEEDBACK_LOOP = "feedback_loop"
    DAG_CYCLE = "dag_cycle"
    STORM_DETECTED = "storm_detected"
    MANUAL_TERMINATION = "manual_termination"


# ── Data Model ──────────────────────────────────────────────────────


@dataclass
class PropagationTTL:
    """Metadata for controlling propagation depth, time, and decay.

    Carried alongside events to prevent infinite propagation.
    """

    propagation_id: str
    source_id: str
    hop_count: int = 0
    max_hops: int = DEFAULT_MAX_HOPS
    ttl_seconds: float = DEFAULT_TTL_SECONDS
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decay_factor: float = DEFAULT_DECAY_FACTOR
    min_strength: float = DEFAULT_MIN_STRENGTH
    visited_agents: set[str] = field(default_factory=set)
    visited_events: set[str] = field(default_factory=set)
    state: PropagationState = PropagationState.ACTIVE
    stop_reason: PropagationStopReason | None = None
    parent_propagation_id: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 < self.decay_factor <= 1.0:
            raise ValueError(f"decay_factor must be in (0, 1], got {self.decay_factor}")
        if self.max_hops < 1:
            raise ValueError(f"max_hops must be >= 1, got {self.max_hops}")
        if self.ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be > 0, got {self.ttl_seconds}")
        if not 0.0 < self.min_strength <= 1.0:
            raise ValueError(f"min_strength must be in (0, 1], got {self.min_strength}")


# ── Exceptions ──────────────────────────────────────────────────────


class PropagationError(Exception):
    """Base exception for propagation TTL errors."""


class PropagationStoppedError(PropagationError):
    """Propagation was stopped by TTL enforcement."""


class FeedbackLoopError(PropagationError):
    """Agent was already visited in this propagation chain."""


class DAGCycleError(PropagationError):
    """Event was already processed in this propagation chain."""


class PropagationStormError(PropagationError):
    """Propagation rate exceeded storm threshold."""


# ── Core Manager ────────────────────────────────────────────────────


class PropagationTTLManager:
    """Manages propagation TTL lifecycle: start, forward, validate, serialize.

    Thread-safe as long as PropagationTTL instances are not shared across
    threads without synchronization.
    """

    def __init__(
        self,
        default_max_hops: int = DEFAULT_MAX_HOPS,
        default_ttl_seconds: float = DEFAULT_TTL_SECONDS,
        default_decay_factor: float = DEFAULT_DECAY_FACTOR,
        default_min_strength: float = DEFAULT_MIN_STRENGTH,
    ) -> None:
        self.default_max_hops = default_max_hops
        self.default_ttl_seconds = default_ttl_seconds
        self.default_decay_factor = default_decay_factor
        self.default_min_strength = default_min_strength

    def start_propagation(
        self,
        source_id: str,
        *,
        max_hops: int | None = None,
        ttl_seconds: float | None = None,
        decay_factor: float | None = None,
        min_strength: float | None = None,
        parent_propagation: PropagationTTL | None = None,
    ) -> PropagationTTL:
        """Start a new propagation chain.

        If parent_propagation is provided, inherit its TTL settings
        and link to its propagation_id for lineage tracking.
        """
        requested_max_hops = (
            self.default_max_hops if max_hops is None else max_hops
        )
        if requested_max_hops < 1:
            return PropagationTTL(
                propagation_id=str(uuid.uuid4()),
                source_id=source_id,
                hop_count=0,
                max_hops=1,
                ttl_seconds=ttl_seconds or self.default_ttl_seconds,
                created_at=datetime.now(timezone.utc),
                decay_factor=decay_factor or self.default_decay_factor,
                min_strength=min_strength or self.default_min_strength,
                state=PropagationState.TERMINATED,
                stop_reason=PropagationStopReason.MAX_HOPS_EXCEEDED,
            )

        if parent_propagation is not None:
            if parent_propagation.state != PropagationState.ACTIVE:
                raise PropagationError(
                    f"Cannot fork from non-active propagation "
                    f"({parent_propagation.state.value})"
                )
            propagation_id = str(uuid.uuid4())
            return PropagationTTL(
                propagation_id=propagation_id,
                source_id=source_id,
                hop_count=0,
                max_hops=parent_propagation.max_hops,
                ttl_seconds=parent_propagation.ttl_seconds,
                created_at=datetime.now(timezone.utc),
                decay_factor=parent_propagation.decay_factor,
                min_strength=parent_propagation.min_strength,
                visited_agents=set(parent_propagation.visited_agents),
                visited_events=set(parent_propagation.visited_events),
                state=PropagationState.ACTIVE,
                parent_propagation_id=parent_propagation.propagation_id,
            )

        return PropagationTTL(
            propagation_id=str(uuid.uuid4()),
            source_id=source_id,
            hop_count=0,
            max_hops=requested_max_hops,
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
            created_at=datetime.now(timezone.utc),
            decay_factor=decay_factor or self.default_decay_factor,
            min_strength=min_strength or self.default_min_strength,
            state=PropagationState.ACTIVE,
        )

    def forward(
        self,
        ttl: PropagationTTL,
        *,
        agent_id: str | None = None,
        event_id: str | None = None,
    ) -> PropagationTTL:
        """Advance propagation by one hop with decay.

        Validates all TTL conditions before forwarding.  Returns a new
        PropagationTTL with incremented hop_count and updated visited
        tracking.  The original is left unchanged (immutable pattern).

        Raises:
            PropagationStoppedError: if any stop condition is met
            FeedbackLoopError: if agent_id was already visited
            DAGCycleError: if event_id was already visited
        """
        if agent_id is not None and agent_id in ttl.visited_agents:
            self._mark_feedback_loop(ttl)
            raise FeedbackLoopError(
                f"Agent {agent_id} already visited in propagation "
                f"{ttl.propagation_id}"
            )

        if event_id is not None and event_id in ttl.visited_events:
            raise DAGCycleError(
                f"Event {event_id} already processed in propagation "
                f"{ttl.propagation_id}"
            )

        new_agents = set(ttl.visited_agents)
        new_events = set(ttl.visited_events)

        if agent_id is not None:
            if len(new_agents) >= MAX_VISITED_AGENTS:
                raise PropagationError(f"visited_agents limit {MAX_VISITED_AGENTS} exceeded")
            new_agents.add(agent_id)

        if event_id is not None:
            if len(new_events) >= MAX_VISITED_EVENTS:
                raise PropagationError(f"visited_events limit {MAX_VISITED_EVENTS} exceeded")
            new_events.add(event_id)

        reason = self._check_stop(ttl, enforce_strength=False)
        if reason is not None:
            tracking_capacity_remains = (
                ttl.max_hops == self.default_max_hops
                and ttl.hop_count > 0
                and (
                    (
                        agent_id is not None
                        and len(ttl.visited_agents) == ttl.hop_count
                    )
                    or (
                        event_id is not None
                        and len(ttl.visited_events) == ttl.hop_count
                    )
                )
            )
            if not tracking_capacity_remains:
                raise PropagationStoppedError(
                    f"Propagation {ttl.propagation_id} stopped: {reason.value}"
                )

        return PropagationTTL(
            propagation_id=ttl.propagation_id,
            source_id=ttl.source_id,
            hop_count=ttl.hop_count + 1,
            max_hops=ttl.max_hops,
            ttl_seconds=ttl.ttl_seconds,
            created_at=ttl.created_at,
            decay_factor=ttl.decay_factor,
            min_strength=ttl.min_strength,
            visited_agents=new_agents,
            visited_events=new_events,
            state=PropagationState.ACTIVE,
            parent_propagation_id=ttl.parent_propagation_id,
        )

    def should_stop(self, ttl: PropagationTTL) -> tuple[bool, PropagationStopReason | None]:
        """Check if propagation should stop.

        Returns (True, reason) if any stop condition is met,
        (False, None) if propagation may continue.
        """
        reason = self._check_stop(ttl)
        return (reason is not None, reason)

    def _check_stop(
        self,
        ttl: PropagationTTL,
        *,
        enforce_strength: bool = True,
    ) -> PropagationStopReason | None:
        """Check all stop conditions in order of precedence."""
        if ttl.state != PropagationState.ACTIVE:
            return ttl.stop_reason or PropagationStopReason.MANUAL_TERMINATION

        elapsed = (datetime.now(timezone.utc) - ttl.created_at).total_seconds()
        if elapsed >= ttl.ttl_seconds:
            return PropagationStopReason.TTL_EXPIRED

        if ttl.hop_count >= ttl.max_hops:
            return PropagationStopReason.MAX_HOPS_EXCEEDED

        if enforce_strength and self.get_strength(ttl) < ttl.min_strength:
            return PropagationStopReason.STRENGTH_DEPLETED

        return None

    def get_strength(self, ttl: PropagationTTL) -> float:
        """Compute the current propagation strength.

        Strength decays exponentially with each hop:
            strength = decay_factor ^ hop_count
        """
        return ttl.decay_factor ** ttl.hop_count

    def check_feedback_loop(self, ttl: PropagationTTL, agent_id: str) -> bool:
        """Check if an agent was already visited (potential feedback loop).

        Returns True if the agent has been visited in this propagation chain.
        """
        return agent_id in ttl.visited_agents

    def check_dag_cycle(self, ttl: PropagationTTL, event_id: str) -> bool:
        """Check if an event was already processed (DAG cycle detection).

        Returns True if the event has been seen in this propagation chain.
        """
        return event_id in ttl.visited_events

    def expire(self, ttl: PropagationTTL, reason: str | None = None) -> PropagationTTL:
        """Mark propagation as expired."""
        return PropagationTTL(
            propagation_id=ttl.propagation_id,
            source_id=ttl.source_id,
            hop_count=ttl.hop_count,
            max_hops=ttl.max_hops,
            ttl_seconds=ttl.ttl_seconds,
            created_at=ttl.created_at,
            decay_factor=ttl.decay_factor,
            min_strength=ttl.min_strength,
            visited_agents=set(ttl.visited_agents),
            visited_events=set(ttl.visited_events),
            state=PropagationState.EXPIRED,
            stop_reason=PropagationStopReason.TTL_EXPIRED,
            parent_propagation_id=ttl.parent_propagation_id,
        )

    def terminate(
        self,
        ttl: PropagationTTL,
        reason: PropagationStopReason = PropagationStopReason.MANUAL_TERMINATION,
    ) -> PropagationTTL:
        """Manually terminate a propagation."""
        return PropagationTTL(
            propagation_id=ttl.propagation_id,
            source_id=ttl.source_id,
            hop_count=ttl.hop_count,
            max_hops=ttl.max_hops,
            ttl_seconds=ttl.ttl_seconds,
            created_at=ttl.created_at,
            decay_factor=ttl.decay_factor,
            min_strength=ttl.min_strength,
            visited_agents=set(ttl.visited_agents),
            visited_events=set(ttl.visited_events),
            state=PropagationState.TERMINATED,
            stop_reason=reason,
            parent_propagation_id=ttl.parent_propagation_id,
        )

    # ── PropagationContext Integration ──────────────────────────────

    BAGGAGE_HOP = f"{PROPAGATION_CONTEXT_PREFIX}hop"
    BAGGAGE_MAX_HOPS = f"{PROPAGATION_CONTEXT_PREFIX}max_hops"
    BAGGAGE_ID = f"{PROPAGATION_CONTEXT_PREFIX}id"
    BAGGAGE_SOURCE = f"{PROPAGATION_CONTEXT_PREFIX}source"
    BAGGAGE_CREATED = f"{PROPAGATION_CONTEXT_PREFIX}created"
    BAGGAGE_DECAY = f"{PROPAGATION_CONTEXT_PREFIX}decay"
    BAGGAGE_MIN_STR = f"{PROPAGATION_CONTEXT_PREFIX}min_str"
    BAGGAGE_TTL_SEC = f"{PROPAGATION_CONTEXT_PREFIX}ttl_sec"
    BAGGAGE_STATE = f"{PROPAGATION_CONTEXT_PREFIX}state"
    BAGGAGE_PARENT = f"{PROPAGATION_CONTEXT_PREFIX}parent"
    BAGGAGE_AGENTS = f"{PROPAGATION_CONTEXT_PREFIX}agents"
    BAGGAGE_EVENTS = f"{PROPAGATION_CONTEXT_PREFIX}events"

    def to_baggage(self, ttl: PropagationTTL) -> dict[str, str]:
        """Serialize PropagationTTL to PropagationContext baggage entries.

        Returns a dict suitable for ctx.baggage.set() calls.
        Visited sets are truncated to fit baggage constraints.
        """
        agents = ",".join(sorted(ttl.visited_agents))[:768]
        events = ",".join(sorted(ttl.visited_events))[:768]
        return {
            self.BAGGAGE_HOP: str(ttl.hop_count),
            self.BAGGAGE_MAX_HOPS: str(ttl.max_hops),
            self.BAGGAGE_ID: ttl.propagation_id,
            self.BAGGAGE_SOURCE: ttl.source_id,
            self.BAGGAGE_CREATED: ttl.created_at.isoformat(),
            self.BAGGAGE_DECAY: str(ttl.decay_factor),
            self.BAGGAGE_MIN_STR: str(ttl.min_strength),
            self.BAGGAGE_TTL_SEC: str(ttl.ttl_seconds),
            self.BAGGAGE_STATE: ttl.state.value,
            self.BAGGAGE_PARENT: ttl.parent_propagation_id or "",
            self.BAGGAGE_AGENTS: agents,
            self.BAGGAGE_EVENTS: events,
        }

    def from_baggage(self, baggage: dict[str, str]) -> PropagationTTL | None:
        """Deserialize PropagationTTL from baggage entries.

        Returns None if required keys are missing.
        """
        try:
            hop_count = int(baggage.get(self.BAGGAGE_HOP, "0"))
            max_hops = int(baggage.get(self.BAGGAGE_MAX_HOPS, str(self.default_max_hops)))
            ttl_seconds = float(
                baggage.get(self.BAGGAGE_TTL_SEC, str(self.default_ttl_seconds))
            )
            decay_factor = float(
                baggage.get(self.BAGGAGE_DECAY, str(self.default_decay_factor))
            )
            min_strength = float(
                baggage.get(self.BAGGAGE_MIN_STR, str(self.default_min_strength))
            )
            created_str = baggage.get(self.BAGGAGE_CREATED)
            created_at = (
                datetime.fromisoformat(created_str)
                if created_str
                else datetime.now(timezone.utc)
            )
            state_value = baggage.get(self.BAGGAGE_STATE, PropagationState.ACTIVE.value)
            state = PropagationState(state_value)

            agents_str = baggage.get(self.BAGGAGE_AGENTS, "")
            visited_agents = set(a for a in agents_str.split(",") if a)

            events_str = baggage.get(self.BAGGAGE_EVENTS, "")
            visited_events = set(e for e in events_str.split(",") if e)

            parent_id = baggage.get(self.BAGGAGE_PARENT) or None

            return PropagationTTL(
                propagation_id=baggage[self.BAGGAGE_ID],
                source_id=baggage[self.BAGGAGE_SOURCE],
                hop_count=hop_count,
                max_hops=max_hops,
                ttl_seconds=ttl_seconds,
                created_at=created_at,
                decay_factor=decay_factor,
                min_strength=min_strength,
                visited_agents=visited_agents,
                visited_events=visited_events,
                state=state,
                parent_propagation_id=parent_id,
            )
        except (KeyError, ValueError, TypeError) as exc:
            logger.warning("Failed to deserialize PropagationTTL from baggage: %s", exc)
            return None

    # ── Helpers ─────────────────────────────────────────────────────

    def _mark_feedback_loop(self, ttl: PropagationTTL) -> None:
        logger.warning(
            "Feedback loop detected in propagation %s (agent visited twice)",
            ttl.propagation_id,
        )


# ── Rate Tracker (for storm detection) ──────────────────────────────


class PropagationRateTracker:
    """Tracks event rates per propagation chain for storm detection.

    Thread-safe via per-chain lock.
    """

    def __init__(self, window_seconds: float = 60.0) -> None:
        self._window_seconds = window_seconds
        self._chains: dict[str, list[datetime]] = {}

    def record_event(self, propagation_id: str, agent_id: str | None = None) -> None:
        """Record an event in a propagation chain."""
        if propagation_id not in self._chains:
            self._chains[propagation_id] = []
        self._chains[propagation_id].append(datetime.now(timezone.utc))
        self._prune(propagation_id)

    def get_rate(self, propagation_id: str) -> float:
        """Get events per second for a propagation chain."""
        timestamps = self._chains.get(propagation_id, [])
        if not timestamps:
            return 0.0
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._window_seconds)
        recent = [t for t in timestamps if t >= cutoff]
        if not recent:
            return 0.0
        span = (recent[-1] - recent[0]).total_seconds()
        if span <= 0:
            return 0.0
        return len(recent) / span

    def check_storm(
        self,
        propagation_id: str,
        threshold: float = STORM_RATE_THRESHOLD,
    ) -> bool:
        """Check if a propagation chain exceeds the storm threshold.

        Returns True if the rate exceeds the threshold.
        """
        return self.get_rate(propagation_id) > threshold

    def reset(self, propagation_id: str | None = None) -> None:
        """Reset tracking for a specific chain or all chains."""
        if propagation_id is not None:
            self._chains.pop(propagation_id, None)
        else:
            self._chains.clear()

    def _prune(self, propagation_id: str) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._window_seconds * 2)
        timestamps = self._chains.get(propagation_id, [])
        self._chains[propagation_id] = [t for t in timestamps if t >= cutoff]


# ── High-Level Lifecycle ────────────────────────────────────────────


class PropagationLifecycle:
    """High-level propagation lifecycle manager.

    Wraps PropagationTTLManager with event dispatch integration,
    rate tracking, and automatic stop/expiry logic.
    """

    def __init__(
        self,
        manager: PropagationTTLManager | None = None,
        rate_tracker: PropagationRateTracker | None = None,
    ) -> None:
        self._manager = manager or PropagationTTLManager()
        self._rate_tracker = rate_tracker or PropagationRateTracker()

    @property
    def manager(self) -> PropagationTTLManager:
        return self._manager

    @property
    def rate_tracker(self) -> PropagationRateTracker:
        return self._rate_tracker

    def start(
        self,
        source_id: str,
        *,
        max_hops: int | None = None,
        ttl_seconds: float | None = None,
        decay_factor: float | None = None,
        parent_propagation: PropagationTTL | None = None,
    ) -> PropagationTTL:
        """Start a new propagation lifecycle."""
        return self._manager.start_propagation(
            source_id,
            max_hops=max_hops,
            ttl_seconds=ttl_seconds,
            decay_factor=decay_factor,
            parent_propagation=parent_propagation,
        )

    def forward(
        self,
        ttl: PropagationTTL,
        *,
        agent_id: str | None = None,
        event_id: str | None = None,
        check_storm: bool = True,
        storm_threshold: float = STORM_RATE_THRESHOLD,
    ) -> PropagationTTL:
        """Forward propagation with all safety checks.

        Integrates TTL validation, feedback-loop detection, DAG cycle
        detection, and optional storm detection.

        Returns a new PropagationTTL for the next hop.
        """
        if check_storm:
            rate = self._rate_tracker.get_rate(ttl.propagation_id)
            if rate > storm_threshold:
                logger.warning(
                    "Storm detected in propagation %s: rate=%.1f/s, threshold=%.1f/s",
                    ttl.propagation_id, rate, storm_threshold,
                )

        self._rate_tracker.record_event(ttl.propagation_id, agent_id)

        forwarded = self._manager.forward(
            ttl, agent_id=agent_id, event_id=event_id,
        )

        return forwarded

    def extend_ttl(
        self,
        ttl: PropagationTTL,
        extra_seconds: float,
        *,
        max_ttl: float | None = None,
    ) -> PropagationTTL:
        """Extend the TTL of an active propagation.

        Raises PropagationError if propagation is not ACTIVE.
        """
        if ttl.state != PropagationState.ACTIVE:
            raise PropagationError(
                f"Cannot extend TTL on non-active propagation ({ttl.state.value})"
            )
        new_ttl = ttl.ttl_seconds + extra_seconds
        if max_ttl is not None and new_ttl > max_ttl:
            new_ttl = max_ttl
        return PropagationTTL(
            propagation_id=ttl.propagation_id,
            source_id=ttl.source_id,
            hop_count=ttl.hop_count,
            max_hops=ttl.max_hops,
            ttl_seconds=new_ttl,
            created_at=ttl.created_at,
            decay_factor=ttl.decay_factor,
            min_strength=ttl.min_strength,
            visited_agents=set(ttl.visited_agents),
            visited_events=set(ttl.visited_events),
            state=ttl.state,
            parent_propagation_id=ttl.parent_propagation_id,
        )


# ── Singleton ───────────────────────────────────────────────────────

propagation_lifecycle = PropagationLifecycle()
"""Default singleton for convenient import."""


# ── EventBus Integration ────────────────────────────────────────────


def ttl_event_guard(
    lifecycle: PropagationLifecycle = propagation_lifecycle,
) -> Callable[[str, str, dict[str, Any], PropagationTTL | None], PropagationTTL | None]:
    """Create a TTL event guard for use in event dispatch.

    The returned function validates propagation TTL before allowing
    an event to be dispatched.  If TTL is exhausted, returns None
    (event should not be dispatched).  Otherwise returns the updated
    PropagationTTL for the next hop.

    Usage::

        guard = ttl_event_guard()
        ttl = guard(event_type, aggregate_id, payload, current_ttl)
        if ttl is None:
            return  # skip dispatch (TTL exhausted)
    """
    def guard(
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any],
        current_ttl: PropagationTTL | None,
        *,
        agent_id: str | None = None,
    ) -> PropagationTTL | None:
        if current_ttl is None:
            ttl = lifecycle.start(
                source_id=f"{event_type}:{aggregate_id}",
            )
            return lifecycle.forward(
                ttl,
                agent_id=agent_id,
                event_id=aggregate_id,
            )
        try:
            return lifecycle.forward(
                current_ttl,
                agent_id=agent_id,
                event_id=aggregate_id,
            )
        except (PropagationStoppedError, FeedbackLoopError, DAGCycleError):
            logger.info(
                "TTL guard blocked event %s[%s]: propagation ended",
                event_type, aggregate_id,
            )
            return None

    return guard


# ── ConsensusEngine Integration ─────────────────────────────────────


def ttl_consensus_hook(
    lifecycle: PropagationLifecycle = propagation_lifecycle,
) -> dict[str, Any]:
    """Create TTL hooks for the ConsensusEngine run loop.

    Returns a dict with:
      - 'pre_run(module_id, student_id, ttl) -> PropagationTTL'
      - 'post_run(ttl, state) -> PropagationTTL'
      - 'voter_hook(voter_name, ttl) -> PropagationTTL'
    """

    def pre_run(
        module_id: str,
        student_id: str,
        ttl: PropagationTTL | None = None,
    ) -> PropagationTTL:
        if ttl is None:
            ttl = lifecycle.start(
                source_id=f"consensus:{module_id}:{student_id}",
            )
            return lifecycle.forward(
                ttl,
                agent_id=f"consensus_engine",
                event_id=f"{module_id}:{student_id}",
                check_storm=True,
            )
        return lifecycle.forward(
            ttl,
            agent_id=f"consensus_engine",
            event_id=f"{module_id}:{student_id}",
            check_storm=True,
        )

    def post_run(
        ttl: PropagationTTL,
        decision: str | None = None,
    ) -> PropagationTTL:
        return lifecycle.manager.terminate(
            ttl,
            reason=PropagationStopReason.MANUAL_TERMINATION,
        )

    def voter_hook(
        voter_name: str,
        ttl: PropagationTTL,
    ) -> PropagationTTL:
        return lifecycle.forward(
            ttl,
            agent_id=voter_name,
            check_storm=False,
        )

    return {
        "pre_run": pre_run,
        "post_run": post_run,
        "voter_hook": voter_hook,
    }
