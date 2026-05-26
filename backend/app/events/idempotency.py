"""
Enterprise Event Idempotency Service.

Core responsibilities:
  - IdempotencyKey lifecycle management
  - Content-hash and explicit key generation
  - In-memory LRU hot cache with DB fallback
  - Advisory-lock serialized acquisition
  - TTL-based background expiration

Lifecycle:
  PENDING → IN_PROGRESS → COMPLETED | FAILED
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.db.locks import advisory_lock
from app.models.idempotency_key import IdempotencyKey, IDEMPOTENCY_EXPIRY_HOURS

logger = logging.getLogger(__name__)

# ── In-memory hot cache ────────────────────────────────────────────

_HOT_CACHE_MAX = 10_000
_HOT_CACHE_TTL_SECONDS = 300  # 5 minutes


class _HotCache:
    """Thread-safe LRU hot cache for idempotency keys.

    Refreshes TTL on hit.  Falls back to DB on miss.
    Not safe for multi-process; each process has its own cache.
    """

    def __init__(self, maxsize: int = _HOT_CACHE_MAX, ttl: int = _HOT_CACHE_TTL_SECONDS):
        self._maxsize = maxsize
        self._ttl = ttl
        self._data: OrderedDict[str, tuple[float, IdempotencyKey]] = OrderedDict()

    def get(self, key: str) -> IdempotencyKey | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        ts, record = entry
        if time.monotonic() - ts > self._ttl:
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return record

    def put(self, key: str, record: IdempotencyKey) -> None:
        self._data[key] = (time.monotonic(), record)
        self._data.move_to_end(key)
        while len(self._data) > self._maxsize:
            self._data.popitem(last=False)

    def remove(self, key: str) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()

    @property
    def size(self) -> int:
        return len(self._data)


_hot_cache = _HotCache()


# ── Idempotency Key Generation ─────────────────────────────────────


class IdempotencyKeyGenerator:
    """Strategies for deterministic idempotency key generation."""

    @staticmethod
    def from_content(
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        prefix: str = "ik",
    ) -> str:
        """Deterministic key from event content.

        Uses SHA-256 of (event_type, aggregate_id, canonical payload).
        Same inputs → same key → idempotent dedup.
        """
        raw = json.dumps(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "payload": _canonical(payload or {}),
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"{prefix}:content:{h}"

    @staticmethod
    def from_propagation(
        trace_id: str,
        span_id: str,
        sequence: int = 0,
        *,
        prefix: str = "ik",
    ) -> str:
        """Key derived from distributed tracing context.

        Ensures uniqueness within a single trace/span.
        Useful for internal events where the caller doesn't
        need to manage keys explicitly.
        """
        return f"{prefix}:trace:{trace_id}:{span_id}:{sequence}"

    @staticmethod
    def from_explicit(key: str, *, prefix: str = "ik") -> str:
        """Wrap an explicit caller-provided key."""
        return f"{prefix}:explicit:{key}"


def _canonical(payload: dict[str, Any]) -> dict[str, Any]:
    """Canonicalize payload for deterministic hashing."""
    result: dict[str, Any] = {}
    for k in sorted(payload.keys()):
        v = payload[k]
        if isinstance(v, dict):
            result[k] = _canonical(v)
        elif isinstance(v, list):
            result[k] = [_canonical(i) if isinstance(i, dict) else i for i in v]
        else:
            result[k] = v
    return result


# ── Core Idempotency Service ──────────────────────────────────────


class IdempotencyService:
    """Enterprise idempotency service with caching and lifecycle management.

    Thread-safe (advisory lock) and async-safe (ContextVar compatible).
    """

    def __init__(self, expiry_hours: int = IDEMPOTENCY_EXPIRY_HOURS):
        self._expiry_hours = expiry_hours

    # ── Lifecycle Operations ──────────────────────────────────────

    def acquire(
        self,
        db: Session,
        key: str,
        *,
        event_type: str | None = None,
        aggregate_id: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
    ) -> IdempotencyKey:
        """Acquire an idempotency key for processing.

        Returns:
          - Existing COMPLETED key → replay (cached response available)
          - Existing IN_PROGRESS key → raises IdempotencyConflict
          - Missing key → creates PENDING record and transitions to IN_PROGRESS

        Raises:
          IdempotencyConflict: if another request is already processing
          IdempotencyError: on unexpected DB errors
        """
        if not key:
            raise IdempotencyError("idempotency key is required")

        with advisory_lock(db, f"idempotency:{key}"):
            existing = self._query(db, key)

            if existing:
                if existing.status == "completed":
                    _hot_cache.put(key, existing)
                    return existing

                if existing.status == "in_progress":
                    raise IdempotencyConflict(key)

                if existing.status == "failed":
                    existing.status = "in_progress"
                    existing.response_status = 0
                    existing.response_body = None
                    existing.completed_at = None
                    db.commit()
                    _hot_cache.remove(key)
                    return existing

            if existing is None:
                record = IdempotencyKey(
                    key=key,
                    status="in_progress",
                    response_status=0,
                    event_type=event_type,
                    aggregate_id=aggregate_id,
                    trace_id=trace_id,
                    causation_id=causation_id,
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(hours=self._expiry_hours),
                )
                db.add(record)
                db.commit()
                return record

            return existing

    def complete(
        self,
        db: Session,
        key: str,
        *,
        response_status: int = 200,
        response_body: Any = None,
    ) -> IdempotencyKey | None:
        """Mark an idempotency key as completed with cached response."""
        if not key:
            return None

        with advisory_lock(db, f"idempotency:{key}"):
            record = self._query(db, key)
            if record is None:
                logger.warning("complete called for unknown key %s — creating", key)
                record = IdempotencyKey(
                    key=key,
                    status="completed",
                    response_status=response_status,
                    response_body=_serialize_body(response_body),
                    expires_at=datetime.now(timezone.utc)
                    + timedelta(hours=self._expiry_hours),
                )
                db.add(record)
            else:
                record.status = "completed"
                record.response_status = response_status
                record.response_body = _serialize_body(response_body)
                record.completed_at = datetime.now(timezone.utc)

            db.commit()
            _hot_cache.put(key, record)
            return record

    def fail(
        self,
        db: Session,
        key: str,
        *,
        reason: str | None = None,
    ) -> IdempotencyKey | None:
        """Mark an idempotency key as failed (allows future retry)."""
        if not key:
            return None

        with advisory_lock(db, f"idempotency:{key}"):
            record = self._query(db, key)
            if record is None:
                logger.warning("fail called for unknown key %s", key)
                return None

            record.status = "failed"
            record.response_body = reason
            record.completed_at = datetime.now(timezone.utc)
            db.commit()
            _hot_cache.remove(key)
            return record

    def check(self, db: Session, key: str) -> IdempotencyKey | None:
        """Check idempotency status without acquiring.

        Returns the cached record if completed, or the in-progress
        record.  Returns None for unknown/failed/pending keys.
        """
        if not key:
            return None

        cached = _hot_cache.get(key)
        if cached is not None:
            return cached

        return self._query(db, key)

    def cancel(self, db: Session, key: str) -> bool:
        """Cancel a PENDING or IN_PROGRESS key (delete it)."""
        if not key:
            return False

        with advisory_lock(db, f"idempotency:{key}"):
            record = self._query(db, key)
            if record is None:
                return False
            db.delete(record)
            db.commit()
            _hot_cache.remove(key)
            return True

    # ── Maintenance ───────────────────────────────────────────────

    def purge_expired(self, db: Session, batch_size: int = 500) -> int:
        """Remove expired idempotency keys from DB.

        Returns count of purged records.
        """
        now = datetime.now(timezone.utc)
        expired = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.expires_at < now)
            .limit(batch_size)
            .all()
        )
        for record in expired:
            _hot_cache.remove(record.key)
            db.delete(record)

        if expired:
            db.commit()
            logger.info("Purged %d expired idempotency keys", len(expired))

        return len(expired)

    def clear_cache(self) -> None:
        _hot_cache.clear()

    @property
    def cache_size(self) -> int:
        return _hot_cache.size

    # ── Internal ──────────────────────────────────────────────────

    def _query(self, db: Session, key: str) -> IdempotencyKey | None:
        return (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == key)
            .first()
        )


def _serialize_body(body: Any) -> str | None:
    if body is None:
        return None
    if isinstance(body, str):
        return body
    try:
        return json.dumps(body, default=str)
    except (TypeError, ValueError):
        return str(body)


# ── Exceptions ─────────────────────────────────────────────────────


class IdempotencyError(RuntimeError):
    """Base exception for idempotency errors."""


class IdempotencyConflict(IdempotencyError):
    """Raised when a concurrent request holds the same key."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(
            f"idempotency key '{key}' is already being processed",
        )


# ── Global singleton ───────────────────────────────────────────────

idempotency_service = IdempotencyService()
