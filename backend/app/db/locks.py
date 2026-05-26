"""
Advisory locking primitives.

PostgreSQL: pg_advisory_xact_lock (transaction-scoped, auto-released).
SQLite: threading.Lock para cobertura en tests.

Uso:
    with advisory_lock(db, "memory:user:preference:modality"):
        existing = db.query(...).first()
        ...
        uow.flush()
"""

import hashlib
import logging
import threading
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ADVISORY_LOCK_TIMEOUT = 30.0

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
        try:
            yield
        finally:
            pass
    else:
        lock = _get_local_lock(key)
        acquired = lock.acquire(timeout=ADVISORY_LOCK_TIMEOUT)
        if not acquired:
            raise TimeoutError(
                f"Could not acquire advisory lock within {ADVISORY_LOCK_TIMEOUT}s: {key}"
            )
        try:
            yield
        finally:
            lock.release()


@contextmanager
def try_advisory_lock(db: Session, key: str) -> Generator[bool, None, None]:
    """Non-blocking advisory lock.

    Yields True if lock was acquired, False otherwise.
    """
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        acquired = _pg_try_advisory_lock(db, key)
        try:
            yield acquired
        finally:
            pass
    else:
        lock = _get_local_lock(key)
        acquired = lock.acquire(timeout=0)
        try:
            yield acquired
        finally:
            if acquired:
                lock.release()
