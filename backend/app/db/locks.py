"""
Advisory locking primitives.

PostgreSQL: pg_advisory_xact_lock (transaction-scoped, auto-released).
SQLite: threading.Lock para cobertura en tests.

Sync usage:
    with advisory_lock(db, "memory:user:preference:modality"):
        ...

Async usage:
    async with advisory_lock_async(db, "my:lock:key", timeout_ms=5000):
        ...
"""

import asyncio
import hashlib
import logging
import threading
import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ADVISORY_LOCK_TIMEOUT = 30.0
ADVISORY_LOCK_POLL_INTERVAL = 0.2  # seconds between retry attempts


def _emit_lock_event(event_type: str, key: str, *, error: str | None = None) -> None:
    """Emit a lock event to the diagnostics engine (fail-soft)."""
    try:
        from app.swarm_diagnostics import diagnostics_engine
        diagnostics_engine.make_event(
            event_type=event_type,
            scope="locks",
            source=f"db/locks",
            payload={"key": key},
            error=error,
        )
    except Exception:
        logger.debug("Diagnostics unavailable for lock event", exc_info=True)

_local_locks: dict[str, threading.Lock] = {}
_local_locks_mutex = threading.Lock()


def _get_local_lock(name: str) -> threading.Lock:
    with _local_locks_mutex:
        if name not in _local_locks:
            _local_locks[name] = threading.Lock()
        return _local_locks[name]


def lock_key(name: str) -> int:
    """Hash a string key to a 64-bit signed integer for pg_advisory_lock."""
    digest = hashlib.sha256(name.encode()).hexdigest()
    return int(digest[:16], 16) & 0x7FFFFFFFFFFFFFFF


def _pg_advisory_lock(db: Session, key: str) -> None:
    db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key(key)})


def _pg_try_advisory_lock(db: Session, key: str) -> bool:
    result = db.execute(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key(key)}
    )
    return bool(result.scalar())


@contextmanager
def advisory_lock(db: Session, key: str) -> Generator[None, None, None]:
    """Context manager that acquires an advisory lock.

    PostgreSQL: pg_advisory_xact_lock — auto-released on TX commit/rollback.
    SQLite:     threading.Lock with 30s timeout.
    """
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        _pg_advisory_lock(db, key)
        _emit_lock_event("lock:acquire", key)
        try:
            yield
        finally:
            _emit_lock_event("lock:release", key)
    else:
        lock = _get_local_lock(key)
        acquired = lock.acquire(timeout=ADVISORY_LOCK_TIMEOUT)
        if not acquired:
            _emit_lock_event("lock:timeout", key, error="timeout")
            raise TimeoutError(
                f"Could not acquire advisory lock within {ADVISORY_LOCK_TIMEOUT}s: {key}"
            )
        _emit_lock_event("lock:acquire", key)
        try:
            yield
        finally:
            lock.release()
            _emit_lock_event("lock:release", key)


@contextmanager
def try_advisory_lock(db: Session, key: str) -> Generator[bool, None, None]:
    """Non-blocking advisory lock.

    Yields True if lock was acquired, False otherwise.
    """
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        acquired = _pg_try_advisory_lock(db, key)
        if acquired:
            _emit_lock_event("lock:acquire", key)
        else:
            _emit_lock_event("lock:contended", key)
        try:
            yield acquired
        finally:
            if acquired:
                _emit_lock_event("lock:release", key)
    else:
        lock = _get_local_lock(key)
        acquired = lock.acquire(timeout=0)
        if acquired:
            _emit_lock_event("lock:acquire", key)
        else:
            _emit_lock_event("lock:contended", key)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
                _emit_lock_event("lock:release", key)


# ── Async advisory lock ────────────────────────────────────────────────


async def _pg_try_advisory_lock_async(db: AsyncSession, key: str) -> bool:
    """Async version: non-blocking advisory lock acquisition."""
    result = await db.execute(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": lock_key(key)}
    )
    return bool(result.scalar())


@asynccontextmanager
async def advisory_lock_async(
    db: AsyncSession,
    key: str,
    timeout_ms: float = ADVISORY_LOCK_TIMEOUT * 1000,
) -> AsyncGenerator[bool, None]:
    """Async context manager that acquires an advisory lock with timeout.

    PostgreSQL: pg_try_advisory_xact_lock in a polling loop.
    SQLite:     threading.Lock with timeout.

    Yields True if acquired, False if timeout.
    """
    # SQLAlchemy 2.x: AsyncSession.bind is always None; the dialect is on the
    # underlying sync session proxy instead.  For sync Session the existing
    # .bind attribute still works.
    if isinstance(db, AsyncSession):
        _sync_bind = db.sync_session.bind
        dialect = _sync_bind.dialect.name if _sync_bind else "sqlite"
    else:
        dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        deadline = time.monotonic() + timeout_ms / 1000.0
        while True:
            now = time.monotonic()
            if now >= deadline:
                _emit_lock_event("lock:timeout", key, error="timeout")
                yield False
                return
            acquired = await _pg_try_advisory_lock_async(db, key)
            if acquired:
                _emit_lock_event("lock:acquire", key)
                try:
                    yield True
                    return
                finally:
                    _emit_lock_event("lock:release", key)
            _emit_lock_event("lock:contended", key)
            remaining = deadline - time.monotonic()
            await asyncio.sleep(min(ADVISORY_LOCK_POLL_INTERVAL, max(0.05, remaining)))
    else:
        # SQLite fallback: use thread lock
        local_lock = _get_local_lock(key)
        acquired = local_lock.acquire(timeout=timeout_ms / 1000.0)
        if not acquired:
            _emit_lock_event("lock:timeout", key, error="timeout")
            yield False
            return
        _emit_lock_event("lock:acquire", key)
        try:
            yield True
        finally:
            local_lock.release()
            _emit_lock_event("lock:release", key)
