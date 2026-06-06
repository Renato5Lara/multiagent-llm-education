"""
Swarm Circuit Breaker System — Failure isolation, degraded agent handling,
retry thresholds, cascading failure prevention, adaptive recovery, and
swarm-safe degradation for the multi-agent consensus swarm.

Architecture:
    CircuitState                     — CLOSED / OPEN / HALF_OPEN / ISOLATED
    CircuitBreakerConfig             — Per-breaker tuning parameters
    SwarmCircuitBreaker              — Per-agent state machine
    AdaptiveRecoveryStrategy         — Extends recovery timeout for repeat offenders
    SwarmBreakerIsolationStrategy    — Ensures failures don't cascade across agents
    CircuitBreakerRegistry           — Manages all breakers by agent name
    BreakerAwareVoter                — Wraps BaseVoter with breaker checks
    FallbackStrategy                 — Delegation decisions when breaker is open
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────

DEFAULT_FAILURE_THRESHOLD = 5
DEFAULT_RECOVERY_TIMEOUT_MS = 30_000.0
DEFAULT_HALF_OPEN_MAX_CALLS = 3
DEFAULT_CONSECUTIVE_SUCCESSES_TO_CLOSE = 2
DEFAULT_MAX_ISOLATION_STRIKES = 3
DEFAULT_ISOLATION_TIMEOUT_MS = 300_000.0  # 5min

# ── State ─────────────────────────────────────────────────────────────


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    ISOLATED = "isolated"


# ── Config ────────────────────────────────────────────────────────────


@dataclass
class CircuitBreakerConfig:
    """Tunable parameters for a single agent circuit breaker."""

    failure_threshold: int = DEFAULT_FAILURE_THRESHOLD
    """Consecutive failures before the circuit opens."""

    recovery_timeout_ms: float = DEFAULT_RECOVERY_TIMEOUT_MS
    """Time in OPEN state before transitioning to HALF_OPEN."""

    half_open_max_calls: int = DEFAULT_HALF_OPEN_MAX_CALLS
    """Max probe calls allowed in HALF_OPEN state."""

    consecutive_successes_to_close: int = DEFAULT_CONSECUTIVE_SUCCESSES_TO_CLOSE
    """Successful probe calls needed to transition HALF_OPEN -> CLOSED."""

    max_isolation_strikes: int = DEFAULT_MAX_ISOLATION_STRIKES
    """Number of open cycles before the agent is permanently isolated."""

    isolation_timeout_ms: float = DEFAULT_ISOLATION_TIMEOUT_MS
    """How long an isolated agent stays isolated before auto-transition."""

    fallback_on_open: bool = True
    """If True, generate a degraded vote instead of raising an error."""

    fallback_confidence: float = 0.0
    """Confidence for fallback vote when circuit is open."""

    fallback_reason_prefix: str = "Circuit breaker open"
    """Prefix for the fallback vote reason."""

    def __post_init__(self):
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout_ms <= 0:
            raise ValueError("recovery_timeout_ms must be > 0")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be >= 1")
        if self.consecutive_successes_to_close < 1:
            raise ValueError("consecutive_successes_to_close must be >= 1")
        if self.max_isolation_strikes < 1:
            raise ValueError("max_isolation_strikes must be >= 1")


# ── Per-agent Circuit Breaker ─────────────────────────────────────────


@dataclass
class BreakerHealth:
    """Immutable snapshot of a breaker's state for reporting."""

    agent_name: str
    state: CircuitState
    failure_count: int
    success_count: int
    consecutive_failures: int
    consecutive_successes: int
    total_open_count: int
    last_failure_time_ms: float | None
    last_success_time_ms: float | None
    recovery_remaining_ms: float
    half_open_calls_remaining: int
    is_isolated: bool
    degradation_reason: str = ""


class SwarmCircuitBreaker:
    """State machine for a single swarm agent's circuit.

    Thread-safe.  Each agent in the swarm gets its own instance.

    State transitions:
        CLOSED --[failure >= threshold]--> OPEN
        OPEN   --[recovery_timeout elapsed]--> HALF_OPEN
        HALF_OPEN --[success >= threshold]--> CLOSED
        HALF_OPEN --[failure]--> OPEN
        OPEN   --[isolation_strikes exceeded]--> ISOLATED
        ISOLATED --[isolation_timeout elapsed]--> OPEN (auto-recovery)
    """

    def __init__(
        self,
        agent_name: str,
        config: CircuitBreakerConfig | None = None,
    ):
        self._agent = agent_name
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        self._total_open_count = 0
        self._last_failure_time_ms: float | None = None
        self._last_success_time_ms: float | None = None
        self._state_change_time_ms = time.monotonic_ns() / 1_000_000
        self._half_open_calls = 0
        self._half_open_successes = 0
        self._isolation_strikes = 0
        self._lock = Lock()

    @property
    def config(self) -> CircuitBreakerConfig:
        return self._config

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._state

    # ── Diagnostics instrumentation ────────────────────────────

    def _emit_event(self, event_type: str, payload: dict | None = None) -> None:
        """Emit a circuit-breaker event to the diagnostics engine (fail-soft)."""
        try:
            from app.swarm_diagnostics import diagnostics_engine
            diagnostics_engine.make_event(
                event_type=event_type,
                scope=f"circuit_breaker:{self._agent}",
                source=f"circuit_breaker/{self._agent}",
                payload={
                    "agent": self._agent,
                    "state": self._state.value,
                    "failure_count": self._failure_count,
                    "consecutive_failures": self._consecutive_failures,
                    "total_open_count": self._total_open_count,
                    **(payload or {}),
                },
            )
        except Exception:
            logger.debug("Diagnostics unavailable for circuit breaker", exc_info=True)

    # ── Core decision ───────────────────────────────────────────

    def allow_request(self) -> bool:
        """Check if the circuit allows a request through.

        Side effect: transitions OPEN -> HALF_OPEN if recovery timeout
        has elapsed, caps HALF_OPEN probes.
        """
        with self._lock:
            now_ms = time.monotonic_ns() / 1_000_000

            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.ISOLATED:
                elapsed = now_ms - self._state_change_time_ms
                if elapsed >= self._config.isolation_timeout_ms:
                    logger.info(
                        "Breaker[%s]: isolated -> open (isolation timeout %.0fms elapsed)",
                        self._agent, elapsed,
                    )
                    self._state = CircuitState.OPEN
                    self._state_change_time_ms = now_ms
                    self._isolation_strikes = 0
                    self._emit_event("circuit_breaker:auto_recover", {"elapsed_ms": elapsed})
                    return True
                return False  # still isolated

            if self._state == CircuitState.OPEN:
                elapsed = now_ms - self._state_change_time_ms
                if elapsed >= self._config.recovery_timeout_ms:
                    logger.info(
                        "Breaker[%s]: open -> half-open (recovery timeout %.0fms elapsed)",
                        self._agent, elapsed,
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._state_change_time_ms = now_ms
                    self._half_open_calls = 0
                    self._half_open_successes = 0
                    self._emit_event("circuit_breaker:half_open", {"elapsed_ms": elapsed})
                    return True
                return False  # still open

            # HALF_OPEN: allow probe calls up to limit
            if self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self._config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False  # probe limit reached

            return False

    # ── Outcome recording ───────────────────────────────────────

    def record_success(self) -> None:
        """Record a successful execution.

        In HALF_OPEN state, tracks consecutive successes to close.
        In CLOSED state, resets failure count.
        """
        with self._lock:
            now_ms = time.monotonic_ns() / 1_000_000
            self._success_count += 1
            self._consecutive_failures = 0
            self._consecutive_successes += 1
            self._last_success_time_ms = now_ms

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._config.consecutive_successes_to_close:
                    logger.info(
                        "Breaker[%s]: half-open -> closed (%d consecutive successes)",
                        self._agent, self._half_open_successes,
                    )
                    successes = self._half_open_successes
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._consecutive_failures = 0
                    self._half_open_calls = 0
                    self._half_open_successes = 0
                    self._emit_event("circuit_breaker:close", {"half_open_successes": successes})

    def record_failure(self) -> None:
        """Record a failed execution.

        CLOSED -> OPEN when failure threshold reached.
        HALF_OPEN -> OPEN on any failure.
        OPEN increments isolation strike count.
        """
        with self._lock:
            now_ms = time.monotonic_ns() / 1_000_000
            self._failure_count += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            self._last_failure_time_ms = now_ms

            if self._state == CircuitState.CLOSED:
                if self._consecutive_failures >= self._config.failure_threshold:
                    logger.warning(
                        "Breaker[%s]: closed -> open (%d consecutive failures)",
                        self._agent, self._consecutive_failures,
                    )
                    self._state = CircuitState.OPEN
                    self._state_change_time_ms = now_ms
                    self._total_open_count += 1
                    self._emit_event("circuit_breaker:open", {"consecutive_failures": self._consecutive_failures})

            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "Breaker[%s]: half-open -> open (probe call failed)",
                    self._agent,
                )
                self._state = CircuitState.OPEN
                self._state_change_time_ms = now_ms
                self._total_open_count += 1
                self._emit_event("circuit_breaker:reopen", {"phase": "half_open_probe_failed"})

            # Check isolation strikes after state transition
            if self._state == CircuitState.OPEN:
                if self._total_open_count >= self._config.max_isolation_strikes:
                    logger.warning(
                        "Breaker[%s]: open -> isolated (%d open cycles)",
                        self._agent, self._total_open_count,
                    )
                    self._state = CircuitState.ISOLATED
                    self._state_change_time_ms = now_ms
                    self._emit_event("circuit_breaker:isolate", {"total_open_count": self._total_open_count})

    # ── Fallback vote ───────────────────────────────────────────

    def build_fallback_vote(self) -> dict[str, Any]:
        """Build a degraded fallback vote payload.

        Returns:
            Dict with decision, confidence, reason, and evidence
            suitable for constructing a ConsensusVote.
        """
        from app.core.consensus import VoteDecision

        reason = (
            f"{self._config.fallback_reason_prefix}: "
            f"state={self._state.value}, "
            f"consecutive_failures={self._consecutive_failures}, "
            f"total_open_count={self._total_open_count}"
        )
        return {
            "decision": VoteDecision.ABSTAIN,
            "confidence": self._config.fallback_confidence,
            "reason": reason,
            "evidence": {
                "circuit_breaker": True,
                "state": self._state.value,
                "agent": self._agent,
                "failure_count": self._failure_count,
                "consecutive_failures": self._consecutive_failures,
                "total_open_count": self._total_open_count,
            },
        }

    # ── State transitions (external) ────────────────────────────

    def force_open(self, reason: str = "") -> None:
        """Force the circuit open (e.g., from administrative action)."""
        with self._lock:
            self._state = CircuitState.OPEN
            self._state_change_time_ms = time.monotonic_ns() / 1_000_000
            logger.info("Breaker[%s]: forced open (%s)", self._agent, reason)
            self._emit_event("circuit_breaker:force_open", {"reason": reason})

    def force_close(self) -> None:
        """Force the circuit closed (e.g., from administrative action)."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._state_change_time_ms = time.monotonic_ns() / 1_000_000
            logger.info("Breaker[%s]: forced closed", self._agent)
            self._emit_event("circuit_breaker:force_close")

    def force_isolate(self, reason: str = "") -> None:
        """Force the circuit into isolated state."""
        with self._lock:
            self._state = CircuitState.ISOLATED
            self._state_change_time_ms = time.monotonic_ns() / 1_000_000
            logger.warning("Breaker[%s]: forced isolated (%s)", self._agent, reason)
            self._emit_event("circuit_breaker:force_isolate", {"reason": reason})

    # ── Health inspection ───────────────────────────────────────

    def health(self) -> BreakerHealth:
        """Produce an immutable health snapshot."""
        with self._lock:
            now_ms = time.monotonic_ns() / 1_000_000
            recovery_remaining = 0.0
            if self._state == CircuitState.OPEN:
                elapsed = now_ms - self._state_change_time_ms
                recovery_remaining = max(0.0, self._config.recovery_timeout_ms - elapsed)
            half_open_remaining = 0
            if self._state == CircuitState.HALF_OPEN:
                half_open_remaining = self._config.half_open_max_calls - self._half_open_calls

            return BreakerHealth(
                agent_name=self._agent,
                state=self._state,
                failure_count=self._failure_count,
                success_count=self._success_count,
                consecutive_failures=self._consecutive_failures,
                consecutive_successes=self._consecutive_successes,
                total_open_count=self._total_open_count,
                last_failure_time_ms=self._last_failure_time_ms,
                last_success_time_ms=self._last_success_time_ms,
                recovery_remaining_ms=recovery_remaining,
                half_open_calls_remaining=half_open_remaining,
                is_isolated=self._state == CircuitState.ISOLATED,
                degradation_reason=(
                    f"{self._total_open_count} open cycles"
                    if self._total_open_count > 0
                    else ""
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        h = self.health()
        return {
            "agent": h.agent_name,
            "state": h.state.value,
            "failure_count": h.failure_count,
            "success_count": h.success_count,
            "consecutive_failures": h.consecutive_failures,
            "consecutive_successes": h.consecutive_successes,
            "total_open_count": h.total_open_count,
            "last_failure_time_ms": h.last_failure_time_ms,
            "last_success_time_ms": h.last_success_time_ms,
            "recovery_remaining_ms": round(h.recovery_remaining_ms, 1),
            "half_open_calls_remaining": h.half_open_calls_remaining,
            "is_isolated": h.is_isolated,
            "degradation_reason": h.degradation_reason,
        }

    def reset(self) -> None:
        """Reset breaker to initial CLOSED state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._total_open_count = 0
            self._last_failure_time_ms = None
            self._last_success_time_ms = None
            self._half_open_calls = 0
            self._half_open_successes = 0
            self._isolation_strikes = 0
            self._state_change_time_ms = time.monotonic_ns() / 1_000_000


# ── Adaptive Recovery Strategy ────────────────────────────────────────


class AdaptiveRecoveryStrategy:
    """Extends recovery timeout based on consecutive open cycles.

    Uses exponential backoff: base_timeout * (backoff_factor ^ open_count).
    Clamped to max_timeout_ms.

    Usage:
        strategy = AdaptiveRecoveryStrategy(base_timeout_ms=30_000)
        timeout = strategy.get_recovery_timeout(agent_name, open_count=2)
        # → 30_000 * (2^2) = 120_000ms
        strategy.record_recovery_failure(agent_name)
        # Increments strike count
    """

    def __init__(
        self,
        base_timeout_ms: float = DEFAULT_RECOVERY_TIMEOUT_MS,
        backoff_factor: float = 2.0,
        max_timeout_ms: float = 600_000.0,  # 10min
        max_strikes: int = 5,
    ):
        self._base_timeout_ms = base_timeout_ms
        self._backoff_factor = backoff_factor
        self._max_timeout_ms = max_timeout_ms
        self._max_strikes = max_strikes
        self._strikes: dict[str, int] = {}
        self._lock = Lock()

    def get_recovery_timeout(self, agent_name: str, open_count: int = 0) -> float:
        """Compute adaptive recovery timeout for an agent.

        Args:
            agent_name: The agent name.
            open_count: Number of times this breaker has opened globally.
                        If 0, uses the internal strike count for the agent.

        Returns:
            Timeout in milliseconds.
        """
        with self._lock:
            strikes = self._strikes.get(agent_name, 0)
            effective = max(open_count, strikes)
            timeout = self._base_timeout_ms * (self._backoff_factor ** effective)
            return min(timeout, self._max_timeout_ms)

    def record_recovery_failure(self, agent_name: str) -> int:
        """Record that a recovery attempt failed (breaker re-opened).

        Returns:
            New strike count for the agent.
        """
        with self._lock:
            current = self._strikes.get(agent_name, 0) + 1
            self._strikes[agent_name] = min(current, self._max_strikes)
            return self._strikes[agent_name]

    def record_recovery_success(self, agent_name: str) -> None:
        """Record that a recovery succeeded (breaker stayed closed).

        Reduces strikes to encourage gentler timeouts next time.
        """
        with self._lock:
            current = self._strikes.get(agent_name, 0)
            if current > 0:
                self._strikes[agent_name] = max(0, current - 1)

    def get_strikes(self, agent_name: str) -> int:
        with self._lock:
            return self._strikes.get(agent_name, 0)

    def reset(self) -> None:
        with self._lock:
            self._strikes.clear()


# ── Isolation Strategy ────────────────────────────────────────────────


class SwarmBreakerIsolationStrategy:
    """Ensures that one agent's circuit breaker state does not affect
    other agents' decisions.

    This is primarily an isolation-of-concern: each agent has its own
    independent breaker in the registry.  This strategy also detects
    cascading patterns where multiple agents open in sequence.
    """

    def __init__(self, cascade_window_ms: float = 10_000.0):
        self._cascade_window_ms = cascade_window_ms
        self._open_events: list[tuple[str, float]] = []
        self._lock = Lock()

    def record_open(self, agent_name: str) -> None:
        """Record that an agent's circuit opened."""
        with self._lock:
            now_ms = time.monotonic_ns() / 1_000_000
            self._open_events.append((agent_name, now_ms))
            # Prune old events
            cutoff = now_ms - self._cascade_window_ms
            self._open_events = [(a, t) for a, t in self._open_events if t >= cutoff]

    def detect_cascade(self, threshold: int = 3) -> list[tuple[str, float]]:
        """Detect if multiple agents opened in quick succession.

        Args:
            threshold: Minimum number of distinct agents opening within
                       the cascade window to flag as a cascade.

        Returns:
            List of (agent_name, timestamp_ms) for the cascade events,
            or empty list if no cascade detected.
        """
        with self._lock:
            if len(self._open_events) < threshold:
                return []
            # Check distinct agents
            distinct = set(a for a, _ in self._open_events)
            if len(distinct) >= threshold:
                return list(self._open_events)
            return []

    def reset(self) -> None:
        with self._lock:
            self._open_events.clear()


# ── Registry ──────────────────────────────────────────────────────────


class CircuitBreakerRegistry:
    """Manages all circuit breakers for the swarm.

    Thread-safe.  Each agent gets its own SwarmCircuitBreaker instance.
    """

    def __init__(
        self,
        default_config: CircuitBreakerConfig | None = None,
        adaptive_recovery: AdaptiveRecoveryStrategy | None = None,
        isolation_strategy: SwarmBreakerIsolationStrategy | None = None,
    ):
        self._default_config = default_config or CircuitBreakerConfig()
        self._adaptive = adaptive_recovery or AdaptiveRecoveryStrategy()
        self._isolation = isolation_strategy or SwarmBreakerIsolationStrategy()
        self._breakers: dict[str, SwarmCircuitBreaker] = {}
        self._lock = Lock()

    @property
    def adaptive_recovery(self) -> AdaptiveRecoveryStrategy:
        return self._adaptive

    @property
    def isolation_strategy(self) -> SwarmBreakerIsolationStrategy:
        return self._isolation

    def get_or_create(
        self,
        agent_name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> SwarmCircuitBreaker:
        """Get an existing breaker for an agent, or create a new one."""
        with self._lock:
            if agent_name not in self._breakers:
                merged_config = self._merge_config(config)
                self._breakers[agent_name] = SwarmCircuitBreaker(
                    agent_name=agent_name,
                    config=merged_config,
                )
            return self._breakers[agent_name]

    def get(self, agent_name: str) -> SwarmCircuitBreaker | None:
        with self._lock:
            return self._breakers.get(agent_name)

    def _merge_config(self, override: CircuitBreakerConfig | None) -> CircuitBreakerConfig:
        """Merge default config with per-agent override."""
        if override is None:
            return self._default_config
        merged = CircuitBreakerConfig(
            failure_threshold=override.failure_threshold or self._default_config.failure_threshold,
            recovery_timeout_ms=override.recovery_timeout_ms or self._default_config.recovery_timeout_ms,
            half_open_max_calls=override.half_open_max_calls or self._default_config.half_open_max_calls,
            consecutive_successes_to_close=(
                override.consecutive_successes_to_close
                or self._default_config.consecutive_successes_to_close
            ),
            max_isolation_strikes=override.max_isolation_strikes or self._default_config.max_isolation_strikes,
            isolation_timeout_ms=override.isolation_timeout_ms or self._default_config.isolation_timeout_ms,
            fallback_on_open=override.fallback_on_open,
            fallback_confidence=override.fallback_confidence or self._default_config.fallback_confidence,
            fallback_reason_prefix=override.fallback_reason_prefix or self._default_config.fallback_reason_prefix,
        )
        return merged

    def record_failure(self, agent_name: str) -> SwarmCircuitBreaker | None:
        """Record a failure and return the breaker (or None)."""
        breaker = self.get_or_create(agent_name)
        breaker.record_failure()
        if breaker.state == CircuitState.OPEN:
            self._isolation.record_open(agent_name)
            self._adaptive.record_recovery_failure(agent_name)
        return breaker

    def record_success(self, agent_name: str) -> SwarmCircuitBreaker | None:
        """Record a success and return the breaker (or None)."""
        breaker = self.get_or_create(agent_name)
        breaker.record_success()
        self._adaptive.record_recovery_success(agent_name)
        return breaker

    def allow_request(self, agent_name: str) -> bool:
        """Check if the circuit allows a request for the agent."""
        breaker = self.get_or_create(agent_name)
        return breaker.allow_request()

    def all_health(self) -> dict[str, dict[str, Any]]:
        """Get health snapshots for all registered breakers."""
        with self._lock:
            return {
                name: breaker.to_dict()
                for name, breaker in self._breakers.items()
            }

    def health_summary(self) -> dict[str, Any]:
        """Aggregated health summary across all breakers."""
        with self._lock:
            total = len(self._breakers)
            closed = sum(1 for b in self._breakers.values() if b.state == CircuitState.CLOSED)
            open_b = sum(1 for b in self._breakers.values() if b.state == CircuitState.OPEN)
            half = sum(1 for b in self._breakers.values() if b.state == CircuitState.HALF_OPEN)
            isolated = sum(1 for b in self._breakers.values() if b.state == CircuitState.ISOLATED)
            return {
                "total_breakers": total,
                "closed": closed,
                "open": open_b,
                "half_open": half,
                "isolated": isolated,
                "healthy_ratio": closed / total if total > 0 else 1.0,
            }

    def health_by_state(self, state: CircuitState) -> list[dict[str, Any]]:
        """Get health dicts for all breakers in a given state."""
        with self._lock:
            return [
                b.to_dict()
                for b in self._breakers.values()
                if b.state == state
            ]

    def reset_all(self) -> None:
        """Reset all breakers and strategies."""
        with self._lock:
            for breaker in self._breakers.values():
                breaker.reset()
            self._adaptive.reset()
            self._isolation.reset()

    def reset_agent(self, agent_name: str) -> None:
        """Reset a specific agent's breaker."""
        with self._lock:
            breaker = self._breakers.get(agent_name)
            if breaker:
                breaker.reset()


# ── Voter Proxy ───────────────────────────────────────────────────────


class BreakerAwareVoter:
    """Wraps a BaseVoter with circuit breaker protection.

    Before calling the voter's vote(), checks the circuit breaker.
    If the circuit is open/isolated, returns a degraded fallback vote.
    Records success/failure outcomes.

    Usage:
        proxy = BreakerAwareVoter(voter, registry)
        vote = proxy.vote(ctx)
    """

    def __init__(
        self,
        voter: Any,
        registry: CircuitBreakerRegistry,
        config: CircuitBreakerConfig | None = None,
    ):
        self._voter = voter
        self._registry = registry
        self._config = config

    @property
    def voter_name(self) -> str:
        return self._voter.voter_name

    @property
    def inner_voter(self) -> Any:
        return self._voter

    def vote(self, ctx: Any) -> Any:
        """Vote with circuit breaker protection.

        Returns:
            A ConsensusVote (either the real vote or a degraded fallback).
        """
        from app.core.consensus import ConsensusVote

        agent_name = self._voter.voter_name
        breaker = self._registry.get_or_create(agent_name, config=self._config)

        if not breaker.allow_request():
            fb = breaker.build_fallback_vote()
            return ConsensusVote(
                voter_name=agent_name,
                decision=fb["decision"],
                confidence=fb["confidence"],
                reason=fb["reason"],
                evidence=fb["evidence"],
            )

        try:
            result = self._voter.vote(ctx)
            self._registry.record_success(agent_name)
            return result
        except Exception as exc:
            self._registry.record_failure(agent_name)
            raise  # let caller handle


def wrap_voters_with_breakers(
    voters: list[Any],
    registry: CircuitBreakerRegistry,
) -> list[BreakerAwareVoter]:
    """Utility: wrap a list of BaseVoter instances with BreakerAwareVoter."""
    return [BreakerAwareVoter(v, registry) for v in voters]
