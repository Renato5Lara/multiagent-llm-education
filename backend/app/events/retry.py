"""
Retry-safe event processing with exponential backoff and circuit breaker.

Provides:
  - Exponential backoff with random jitter
  - Configurable max retries per event type
  - Circuit breaker for repeated failures
  - Integration with IdempotencyService (retry-safe → same key, same result)
"""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    idempotency_service as _global_idem,
)
from app.models.event_outbox import EventOutbox

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY_MS = 100
DEFAULT_MAX_DELAY_MS = 30_000
DEFAULT_JITTER_FACTOR = 0.2

# ── Circuit Breaker ────────────────────────────────────────────────


class CircuitState:
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing — reject fast
    HALF_OPEN = "half_open" # testing if recovered


class CircuitBreaker:
    """Circuit breaker for retry operations.

    After `failure_threshold` consecutive failures, the circuit opens
    and rejects calls for `recovery_timeout` seconds.  After that,
    one test call is allowed (half-open).  If it succeeds, the circuit
    closes.  If it fails, the circuit re-opens.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 1,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    def call(self, fn: Callable[[], Any]) -> Any:
        """Execute fn with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._last_failure_time is None:
                self.state = CircuitState.HALF_OPEN
            elif time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                logger.info("Circuit %s: open → half-open", self.name)
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                raise CircuitBreakerOpenError(self.name, self.recovery_timeout)

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError(self.name, self.recovery_timeout)
            self._half_open_calls += 1

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info("Circuit %s: closed (recovered)", self.name)

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "Circuit %s: closed → open (%d failures)",
                self.name, self._failure_count,
            )

    def reset(self) -> None:
        self.state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN


class CircuitBreakerOpenError(RuntimeError):
    """Raised when the circuit breaker is open."""

    def __init__(self, name: str, retry_after: float):
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{name}' is open — "
            f"retry after {retry_after:.0f}s"
        )


# ── Retry Handler ──────────────────────────────────────────────────


class RetryHandler:
    """Retry-safe event processing with exponential backoff.

    Idempotency guarantee: same event + same handler = same result.
    The idempotency key locks the result after first successful execution.
    """

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay_ms: int = DEFAULT_BASE_DELAY_MS,
        max_delay_ms: int = DEFAULT_MAX_DELAY_MS,
        jitter_factor: float = DEFAULT_JITTER_FACTOR,
    ):
        self._idem = idempotency_service or _global_idem
        self._max_retries = max_retries
        self._base_delay_ms = base_delay_ms
        self._max_delay_ms = max_delay_ms
        self._jitter_factor = jitter_factor
        self._circuits: dict[str, CircuitBreaker] = {}

    def execute(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None,
        handler: Callable[[], Any],
        *,
        idempotency_key: str | None = None,
        circuit_name: str | None = None,
    ) -> Any:
        """Execute a handler with retry-safe idempotency.

        The handler is wrapped with:
          1. Idempotency key acquisition (first-call or replay)
          2. Circuit breaker (if circuit_name is provided)
          3. Exponential backoff on failure

        Returns:
            Handler result on first execution or replay.
        """
        key = idempotency_key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )

        start = time.perf_counter()
        record = self._idem.acquire(
            db, key,
            event_type=event_type,
            aggregate_id=aggregate_id,
        )

        if record.status == "completed":
            logger.info("Retry replay: %s[%s]", event_type, aggregate_id)
            retry_stats.record(
                success=True, replayed=True,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
            return self._deserialize(record.response_body)

        circuit = self._get_circuit(circuit_name or event_type)
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                result = circuit.call(handler)
                self._idem.complete(db, key, response_body=result)
                retry_stats.record(
                    success=True,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
                return result
            except CircuitBreakerOpenError:
                logger.warning(
                    "Circuit open for %s (attempt %d/%d)",
                    event_type, attempt, self._max_retries,
                )
                retry_stats.record(
                    success=False, circuit_open=True,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
                last_error = CircuitBreakerOpenError(
                    circuit.name, circuit.recovery_timeout,
                )
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Retry %d/%d for %s[%s] failed: %s",
                    attempt, self._max_retries,
                    event_type, aggregate_id, exc,
                )
                if attempt < self._max_retries:
                    self._backoff(attempt)

        self._idem.fail(db, key, reason=str(last_error))
        retry_stats.record(
            success=False,
            duration_ms=(time.perf_counter() - start) * 1000,
        )
        raise RetryExhaustedError(
            event_type, aggregate_id, self._max_retries, last_error,
        )

    def _backoff(self, attempt: int) -> None:
        delay_ms = min(
            self._base_delay_ms * (2 ** (attempt - 1)),
            self._max_delay_ms,
        )
        jitter = delay_ms * self._jitter_factor * random.random()
        total_s = (delay_ms + jitter) / 1000.0
        time.sleep(total_s)

    def _get_circuit(self, name: str) -> CircuitBreaker:
        if name not in self._circuits:
            self._circuits[name] = CircuitBreaker(name=name)
        return self._circuits[name]

    def reset_circuit(self, name: str) -> None:
        cb = self._circuits.get(name)
        if cb:
            cb.reset()

    def reset_all_circuits(self) -> None:
        for cb in self._circuits.values():
            cb.reset()

    def circuit_state(self, name: str) -> str | None:
        cb = self._circuits.get(name)
        return cb.state if cb else None

    @staticmethod
    def _deserialize(body: str | None) -> Any:
        if body is None:
            return None
        try:
            import json
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return body


class RetryExhaustedError(RuntimeError):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, event_type: str, aggregate_id: str, max_retries: int, cause: Exception | None):
        self.event_type = event_type
        self.aggregate_id = aggregate_id
        self.max_retries = max_retries
        self.cause = cause
        msg = f"Retry exhausted for {event_type}[{aggregate_id}] after {max_retries} attempts"
        if cause:
            msg += f": {cause}"
        super().__init__(msg)


# ── Retry Stats ────────────────────────────────────────────────────


class RetryStats:
    """Collects retry execution statistics."""

    def __init__(self) -> None:
        self.total_attempts = 0
        self.successful = 0
        self.failed = 0
        self.replayed = 0
        self.circuit_open = 0
        self.total_time_ms = 0.0

    def record(
        self,
        success: bool,
        replayed: bool = False,
        circuit_open: bool = False,
        duration_ms: float = 0.0,
    ) -> None:
        self.total_attempts += 1
        self.total_time_ms += duration_ms
        if replayed:
            self.replayed += 1
        elif circuit_open:
            self.circuit_open += 1
        elif success:
            self.successful += 1
        else:
            self.failed += 1

    @property
    def avg_duration_ms(self) -> float:
        if self.total_attempts == 0:
            return 0.0
        return self.total_time_ms / self.total_attempts

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_attempts": self.total_attempts,
            "successful": self.successful,
            "failed": self.failed,
            "replayed": self.replayed,
            "circuit_open": self.circuit_open,
            "avg_duration_ms": round(self.avg_duration_ms, 2),
        }


retry_stats = RetryStats()
