"""
Swarm Synchronization Primitives.

PhaseGate: blocks phase execution until all preconditions are met
SwarmFence: synchronization barrier with timeout for phase transitions
ContextLock: distributed-safe per-context lock preventing concurrent activation

ContextLock uses two-phase locking:
    1. In-process threading.Lock (fast path for same-process contention)
    2. PostgreSQL advisory lock (distributed safety across workers/pods)

Always acquire in the same order: thread → advisory (deadlock prevention).
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class PhaseGate:
    """Synchronization gate that blocks until all preconditions are met.

    Each precondition is a named condition that must be marked as satisfied
    before any phase waiting on this gate can proceed.

    Use case: PedagogicalAnalysis phase waits on both
    'cognitive_stage_detected' and 'concepts_mastered_identified'.
    """

    def __init__(self, name: str, preconditions: list[str], timeout_ms: float = 30000):
        self.name = name
        self._preconditions = set(preconditions)
        self._satisfied: set[str] = set()
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._timeout_ms = timeout_ms
        self._failed: list[str] = []

    def satisfy(self, condition: str) -> None:
        with self._cond:
            self._satisfied.add(condition)
            self._cond.notify_all()

    def fail(self, condition: str, reason: str = "") -> None:
        with self._cond:
            self._failed.append(f"{condition}:{reason}")
            self._cond.notify_all()

    def wait(self) -> tuple[bool, str]:
        deadline = time.monotonic() + self._timeout_ms / 1000.0
        with self._cond:
            while not self._satisfied.issuperset(self._preconditions):
                if self._failed:
                    return False, f"Gate {self.name} failed: {', '.join(self._failed)}"
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    missing = self._preconditions - self._satisfied
                    return False, f"Gate {self.name} timed out. Missing: {', '.join(sorted(missing))}"
                self._cond.wait(timeout=remaining)
            return True, ""

    @property
    def is_open(self) -> bool:
        with self._lock:
            return self._satisfied.issuperset(self._preconditions)

    @property
    def missing(self) -> list[str]:
        with self._lock:
            return sorted(self._preconditions - self._satisfied)

    def reset(self) -> None:
        with self._cond:
            self._satisfied.clear()
            self._failed.clear()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "preconditions": list(self._preconditions),
                "satisfied": list(self._satisfied),
                "missing": sorted(self._preconditions - self._satisfied),
                "open": self.is_open,
                "failed": self._failed,
            }


class SwarmFence:
    """Synchronization barrier for phase transitions.

    Ensures ALL agents/workers in a phase complete before the phase
    can transition to the next state.

    Use case: Consensus phase must collect votes from ALL voters
    before inference can proceed.
    """

    def __init__(self, name: str, expected_parties: list[str], timeout_ms: float = 30000):
        self.name = name
        self._expected = set(expected_parties)
        self._arrived: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._timeout_ms = timeout_ms
        self._tripped = False

    def arrive(self, party: str, payload: dict[str, Any] | None = None) -> tuple[bool, str]:
        with self._cond:
            if self._tripped:
                return False, "Fence already tripped"
            self._arrived[party] = {
                "arrived_at": datetime.now(timezone.utc).isoformat(),
                "payload": payload or {},
            }
            remaining = self._expected - set(self._arrived.keys())
            if not remaining:
                self._tripped = True
                self._cond.notify_all()
                return True, "All parties arrived"
            return True, f"Waiting for: {', '.join(sorted(remaining))}"

    def wait(self) -> tuple[bool, dict[str, Any]]:
        deadline = time.monotonic() + self._timeout_ms / 1000.0
        with self._cond:
            while not self._tripped:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    missing = self._expected - set(self._arrived.keys())
                    return False, {
                        "error": f"Fence {self.name} timed out",
                        "missing": list(missing),
                        "arrived": list(self._arrived.keys()),
                    }
                self._cond.wait(timeout=remaining)
            return True, {
                "arrived": {k: v["arrived_at"] for k, v in self._arrived.items()},
            }

    def reset(self) -> None:
        with self._cond:
            self._arrived.clear()
            self._tripped = False

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "name": self.name,
                "expected": list(self._expected),
                "arrived": list(self._arrived.keys()),
                "missing": sorted(self._expected - set(self._arrived.keys())),
                "tripped": self._tripped,
            }


class ContextLock:
    """Distributed-safe per-context lock.

    Two-phase locking:
      1. In-process threading.Lock (fast path, same-process contention)
      2. PostgreSQL advisory lock (distributed safety, cross-worker)

    Always acquire in the same order: thread → advisory.
    Both must succeed for the lock to be considered acquired.

    Async-safe: the acquire() coroutine never blocks the event loop.
    Thread-safe: all internal state is protected by threading.Lock.
    Distributed-safe: advisory lock is cluster-wide via PostgreSQL.
    Timeout-safe: both phases have configurable timeouts.
    Deadlock-safe: single acquisition order, no nested lock attempts.
    """

    def __init__(self):
        self._locks: dict[str, threading.Lock] = {}
        self._owners: dict[str, str] = {}
        self._lock = threading.Lock()
        self._metrics_context_locks: int = 0
        self._metrics_contention: int = 0
        self._metrics_timeouts: int = 0

    @asynccontextmanager
    async def acquire(
        self,
        context_key: str,
        owner: str,
        db: AsyncSession | None = None,
        timeout_ms: float = 10000,
    ) -> AsyncGenerator[bool, None]:
        """Acquire the context lock.

        Args:
            context_key: Unique identifier for the context being locked.
            owner: Who is requesting the lock (for diagnostics).
            db: AsyncSession for PostgreSQL advisory lock. If None, only
                in-process thread locking is used (single-worker/test mode).
            timeout_ms: Total timeout for both lock phases combined.

        Yields:
            True if both locks acquired, False on timeout.
        """
        start = time.monotonic()

        # ── Phase 1: In-process thread lock (fast path) ──────────
        inner_lock = self._get_lock(context_key)
        loop = asyncio.get_running_loop()

        # Run blocking acquire in executor to avoid event-loop stall
        acquired_local = await loop.run_in_executor(
            None, inner_lock.acquire, timeout_ms / 1000.0,
        )
        if not acquired_local:
            self._metrics_timeouts += 1
            _emit_context_event("lock:context:timeout", context_key, owner,
                                error="in-process timeout")
            _inc_obs_counter("context_lock_timeout")
            yield False
            return

        try:
            # ── Phase 2: Distributed advisory lock ─────────────────
            if db is not None:
                elapsed = (time.monotonic() - start) * 1000
                remaining = max(0.0, timeout_ms - elapsed)

                from app.db.locks import advisory_lock_async
                async with advisory_lock_async(
                    db, context_key, timeout_ms=remaining,
                ) as acquired_dist:
                    if not acquired_dist:
                        self._metrics_timeouts += 1
                        _emit_context_event("lock:context:timeout", context_key, owner,
                                            error="distributed timeout")
                        _inc_obs_counter("context_lock_timeout")
                        yield False
                        return

                    # Both locks acquired
                    with self._lock:
                        self._owners[context_key] = owner
                        self._metrics_context_locks += 1
                    _inc_obs_counter("context_lock_acquire")
                    try:
                        yield True
                    finally:
                        with self._lock:
                            self._owners.pop(context_key, None)
                            self._metrics_context_locks -= 1
                        _inc_obs_counter("context_lock_release")
            else:
                # No DB — thread-level lock only (tests / single-worker)
                with self._lock:
                    self._owners[context_key] = owner
                    self._metrics_context_locks += 1
                _inc_obs_counter("context_lock_acquire")
                try:
                    yield True
                finally:
                    with self._lock:
                        self._owners.pop(context_key, None)
                        self._metrics_context_locks -= 1
                    _inc_obs_counter("context_lock_release")
        finally:
            inner_lock.release()

    def is_locked(self, context_key: str) -> bool:
        """Check if the context lock is currently held (in-process only).

        Note: this only checks the local thread lock.  For distributed
        checking, use the advisory lock's pg_try_advisory_xact_lock.
        """
        with self._lock:
            lock = self._locks.get(context_key)
            if lock is None:
                return False
            acquired = lock.acquire(blocking=False)
            if acquired:
                lock.release()
                return False
            self._metrics_contention += 1
            _inc_obs_counter("context_lock_contention")
            return True

    def owner(self, context_key: str) -> str | None:
        """Return the owner string for a locked context, or None."""
        with self._lock:
            return self._owners.get(context_key)

    def _get_lock(self, context_key: str) -> threading.Lock:
        with self._lock:
            if context_key not in self._locks:
                self._locks[context_key] = threading.Lock()
            return self._locks[context_key]

    def snapshot(self) -> dict[str, Any]:
        """Return a diagnostics snapshot of all active context locks."""
        with self._lock:
            return {
                "active_locks": {
                    k: v for k, v in self._owners.items()
                },
                "total_locks": len(self._locks),
                "metrics": {
                    "context_locks": self._metrics_context_locks,
                    "contention": self._metrics_contention,
                    "timeouts": self._metrics_timeouts,
                },
            }


def _emit_context_event(event_type: str, context_key: str, owner: str,
                        *, error: str | None = None) -> None:
    """Emit a context-lock diagnostics event (fail-soft)."""
    try:
        from app.swarm_diagnostics import diagnostics_engine
        diagnostics_engine.make_event(
            event_type=event_type,
            scope=f"context_lock:{context_key}",
            source=f"context_lock",
            payload={"context_key": context_key, "owner": owner},
            error=error,
        )
    except Exception:
        logger.debug("ContextLock diagnostics unavailable", exc_info=True)


def _inc_obs_counter(name: str) -> None:
    """Increment an observability counter (fail-soft)."""
    try:
        from app.observability.metrics_exporter import exporter as obs_exporter
        obs_exporter.inc_counter(name, 1)
    except Exception:
        pass


# Module-level singleton
context_lock = ContextLock()
