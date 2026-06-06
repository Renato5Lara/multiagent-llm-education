"""Rate limiter + Circuit Breaker for Tavily Search API with sliding window and degraded mode."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable

from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)

DEFAULT_MAX_REQUESTS_PER_MINUTE = 20
DEFAULT_CIRCUIT_BREAKER_THRESHOLD = 5
DEFAULT_CIRCUIT_BREAKER_RESET_SECONDS = 60.0
DEFAULT_DEGRADED_COOLDOWN_SECONDS = 30.0


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TavilyRateLimiter:
    """Sliding-window rate limiter for Tavily API requests.

    Tracks request timestamps per minute window and rejects
    requests that exceed the configured limit.
    """

    def __init__(self, max_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE):
        self._max_per_minute = max_per_minute
        self._lock = threading.Lock()
        self._timestamps: list[float] = []

    def acquire(self) -> bool:
        """Try to acquire a request slot. Returns True if allowed."""
        now = time.time()
        cutoff = now - 60.0

        with self._lock:
            self._timestamps = [t for t in self._timestamps if t > cutoff]

            if len(self._timestamps) >= self._max_per_minute:
                exporter.inc_counter("tavily_rate_limited")
                return False

            self._timestamps.append(now)
            return True

    async def acquire_async(self) -> bool:
        """Async variant of acquire()."""
        return self.acquire()

    @property
    def remaining(self) -> int:
        with self._lock:
            now = time.time()
            cutoff = now - 60.0
            active = sum(1 for t in self._timestamps if t > cutoff)
            return max(0, self._max_per_minute - active)

    @property
    def is_limited(self) -> bool:
        return self.remaining <= 0

    def reset(self) -> None:
        with self._lock:
            self._timestamps.clear()


class TavilyCircuitBreaker:
    """Circuit breaker for Tavily API with automatic recovery.

    States:
    - CLOSED: normal operation, requests pass through
    - OPEN: failures exceed threshold, fast-fail
    - HALF_OPEN: probing for recovery

    After reset_seconds in OPEN state, transitions to HALF_OPEN.
    If the probe request succeeds, transitions back to CLOSED.
    """

    def __init__(
        self,
        failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        reset_seconds: float = DEFAULT_CIRCUIT_BREAKER_RESET_SECONDS,
        name: str = "tavily",
    ):
        self._failure_threshold = failure_threshold
        self._reset_seconds = reset_seconds
        self._name = name
        self._lock = threading.Lock()

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._last_state_change: float = time.time()

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def record_success(self) -> None:
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker %s: HALF_OPEN → CLOSED (probe succeeded)", self._name)
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._last_state_change = time.time()
                exporter.set_gauge(f"circuit_breaker_{self._name}", 0.0)
                exporter.inc_counter(f"circuit_breaker_{self._name}_recovery")
            elif self._state == CircuitState.CLOSED:
                self._failure_count = 0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if (
                self._state == CircuitState.CLOSED
                and self._failure_count >= self._failure_threshold
            ):
                logger.warning(
                    "Circuit breaker %s: CLOSED → OPEN (%d failures)",
                    self._name, self._failure_count,
                )
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
                exporter.set_gauge(f"circuit_breaker_{self._name}", 1.0)
                exporter.inc_counter(f"circuit_breaker_{self._name}_open")

            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(
                    "Circuit breaker %s: HALF_OPEN → OPEN (probe failed)",
                    self._name,
                )
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()
                exporter.set_gauge(f"circuit_breaker_{self._name}", 1.0)

    def allow_request(self) -> bool:
        """Check if a request is allowed through the circuit breaker."""
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True

            if self._state == CircuitState.OPEN:
                if time.time() - self._last_state_change >= self._reset_seconds:
                    logger.info(
                        "Circuit breaker %s: OPEN → HALF_OPEN (reset timeout elapsed)",
                        self._name,
                    )
                    self._state = CircuitState.HALF_OPEN
                    self._last_state_change = time.time()
                    exporter.set_gauge(f"circuit_breaker_{self._name}", 0.5)
                    return True
                return False

            if self._state == CircuitState.HALF_OPEN:
                return True

            return False

    def degraded_mode(self) -> bool:
        """Return True if the circuit breaker is OPEN."""
        return self._state == CircuitState.OPEN

    def reset(self) -> None:
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_state_change = time.time()
            exporter.set_gauge(f"circuit_breaker_{self._name}", 0.0)


class TavilyRateLimiterChain:
    """Combines rate limiter + circuit breaker for complete request gating.

    Usage:
        chain = TavilyRateLimiterChain()
        if await chain.can_proceed():
            result = await client.search(query)
            chain.record_success()
        else:
            # degraded path
            chain.record_failure()
    """

    def __init__(
        self,
        max_per_minute: int = DEFAULT_MAX_REQUESTS_PER_MINUTE,
        failure_threshold: int = DEFAULT_CIRCUIT_BREAKER_THRESHOLD,
        reset_seconds: float = DEFAULT_CIRCUIT_BREAKER_RESET_SECONDS,
    ):
        self.rate_limiter = TavilyRateLimiter(max_per_minute=max_per_minute)
        self.circuit_breaker = TavilyCircuitBreaker(
            failure_threshold=failure_threshold,
            reset_seconds=reset_seconds,
        )

    async def can_proceed(self) -> bool:
        """Check if request can proceed through rate limiter + circuit breaker."""
        if self.circuit_breaker.is_open:
            logger.warning("Tavily circuit breaker OPEN — degraded mode")
            return False

        if not self.rate_limiter.acquire():
            logger.warning("Tavily rate limit reached — degraded mode")
            return False

        return True

    def record_success(self) -> None:
        self.circuit_breaker.record_success()

    def record_failure(self) -> None:
        self.circuit_breaker.record_failure()

    @property
    def degraded(self) -> bool:
        return self.circuit_breaker.degraded_mode() or self.rate_limiter.is_limited

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "circuit_state": self.circuit_breaker.state.value,
            "rate_remaining": self.rate_limiter.remaining,
            "rate_limited": self.rate_limiter.is_limited,
            "degraded": self.degraded,
        }


# Singleton
_chain_instance: TavilyRateLimiterChain | None = None


def get_rate_limiter_chain() -> TavilyRateLimiterChain:
    global _chain_instance
    if _chain_instance is None:
        _chain_instance = TavilyRateLimiterChain()
    return _chain_instance
