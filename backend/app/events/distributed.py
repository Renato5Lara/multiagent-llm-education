"""
Distributed Deduplication Engine for the multi-agent swarm.

Provides cross-process event dedup via:
  - Lock-free optimistic dedup using unique constraint on content-hash
  - Multiple idempotency key strategies (content, propagation, explicit)
  - Dead-letter detection when retries exhausted
  - Configurable dedup window (TTL)
  - Propagation-context integration (baggage carries dedup keys)
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.locks import advisory_lock
from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    IdempotencyConflict,
    IdempotencyError,
    idempotency_service as _global_idem,
)
from app.models.idempotency_key import IdempotencyKey
from app.tracing import correlation_engine

logger = logging.getLogger(__name__)

DEFAULT_DEDUP_WINDOW_HOURS = 24
MAX_BAGGAGE_KEYS = 16


class DistributedDedupEngine:
    """Cross-process event deduplication engine.

    Uses three layers of dedup:
      1. Advisory lock (serializes per-key access)
      2. DB unique constraint + status check (prevents double processing)
      3. Propagation baggage (carries active keys within a trace)
    """

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
        window_hours: int = DEFAULT_DEDUP_WINDOW_HOURS,
    ):
        self._idem = idempotency_service or _global_idem
        self._window_hours = window_hours

    def is_duplicate(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        key: str | None = None,
    ) -> bool:
        """Check if an event is a duplicate without acquiring.

        Returns True if the event was already processed.
        Safe for read-only checks (no side effects).
        """
        dedup_key = key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )
        record = self._idem.check(db, dedup_key)
        return record is not None and record.status == "completed"

    def dedup_or_none(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        key: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        handler: Any = None,
    ) -> Any | None:
        """Execute handler with dedup protection.

        If the event was already processed:
          - Returns the cached result (replay)
          - Adds X-Dedup-Replay: true baggage tag

        If the event is new:
          - Acquires the key, runs handler, completes key
          - Carries the dedup key in PropagationContext baggage

        If concurrently processing:
          - Returns None (silent skip) — avoids 409 in distributed context

        Returns:
            Handler result on first execution
            Cached result on replay
            None if concurrently processing (skip)
        """
        dedup_key = key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )

        try:
            record = self._idem.acquire(
                db, dedup_key,
                event_type=event_type,
                aggregate_id=aggregate_id,
                trace_id=trace_id,
                causation_id=causation_id,
            )
        except IdempotencyConflict:
            logger.info(
                "Dedup skip (concurrent): %s[%s]",
                event_type, aggregate_id,
            )
            return None

        if record.status == "completed":
            cached = self._deserialize(record.response_body)
            if cached is not None:
                logger.info(
                    "Dedup replay: %s[%s] via key %s",
                    event_type, aggregate_id, dedup_key,
                )
                self._tag_baggage(dedup_key, "replay")
                return cached
            # Completed with no response_body → dispatched but not yet
            # processed.  Fall through to run the handler.

        if handler is None:
            self._idem.complete(db, dedup_key, response_body=None)
            return None

        try:
            result = handler(event_type, aggregate_id, payload)
            self._idem.complete(db, dedup_key, response_body=result)
            self._tag_baggage(dedup_key, "first")
            return result
        except IdempotencyConflict:
            raise
        except Exception as exc:
            self._idem.fail(db, dedup_key, reason=str(exc))
            raise

    def dedup_publish(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        key: str | None = None,
    ) -> bool:
        """Publish with dedup — returns True if claimed, False if duplicate.

        Acquires and completes (with no response body) so the key is
        visible to concurrent callers.  dedup_or_none treats a
        completed key with no response_body as "dispatched but not yet
        processed" and will still run the handler.
        """
        dedup_key = key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )
        record = self._idem.check(db, dedup_key)
        if record is not None:
            return False
        try:
            self._idem.acquire(
                db, dedup_key,
                event_type=event_type,
                aggregate_id=aggregate_id,
            )
            self._idem.complete(db, dedup_key, response_body=None)
            return True
        except IdempotencyConflict:
            return False

    def dedup_consensus(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase: str,
        *,
        handler: Any = None,
    ) -> Any | None:
        """Phase-level consensus dedup.

        Returns None if phase already completed (skip).
        Runs handler if phase is new.
        """
        from app.events.integration import IdempotentConsensusGuard
        guard = IdempotentConsensusGuard(self._idem)
        key = guard.phase_key(module_id, student_id, phase)

        if guard.is_phase_completed(db, module_id, student_id, phase):
            logger.info("Dedup skip (completed phase): %s/%s/%s", module_id, student_id, phase)
            return None

        try:
            guard.acquire_phase(db, module_id, student_id, phase)
        except IdempotencyConflict:
            logger.info("Dedup skip (concurrent phase): %s/%s/%s", module_id, student_id, phase)
            return None

        if handler is None:
            guard.complete_phase(db, module_id, student_id, phase)
            return None

        try:
            result = handler()
            guard.complete_phase(db, module_id, student_id, phase, result)
            return result
        except Exception as exc:
            guard.fail_phase(db, module_id, student_id, phase, reason=str(exc))
            raise

    def check_memory_duplicate(
        self,
        db: Session,
        voter_name: str,
        key: str,
        value: dict[str, Any],
        *,
        confidence: float = 1.0,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str = "observation",
    ) -> str | None:
        """Read-only check if a memory observation was already published.

        Returns the existing SharedMemoryRecord ID if a duplicate is
        found, None otherwise.  No side effects (no key acquisition).
        """
        from app.events.integration import _memory_key
        content_key = _memory_key(voter_name, key, value, confidence, student_id, module_id, memory_type)
        record = self._idem.check(db, content_key)
        if record and record.status == "completed" and record.response_body:
            try:
                cached = json.loads(record.response_body)
                if "record_id" in cached:
                    return cached["record_id"]
            except (json.JSONDecodeError, TypeError):
                pass
        return None

    def dedup_memory(
        self,
        db: Session,
        voter_name: str,
        key: str,
        value: dict[str, Any],
        *,
        confidence: float = 1.0,
        student_id: str | None = None,
        module_id: str | None = None,
        memory_type: str = "observation",
    ) -> bool:
        """Memory publish with dedup.

        Returns True if published, False if duplicate.
        Uses advisory lock + content hash for cross-process safety.

        Note: stores ``{"deduped": True}`` as the response body.  Callers
        that need record-level dedup (e.g. SharedMemoryStore integration)
        should use :meth:`check_memory_duplicate` for read-only checks
        and then call ``_idem.acquire`` / ``_idem.complete`` directly
        with ``{"record_id": "..."}`` for full lifecycle.
        """
        from app.events.integration import _memory_key
        content_key = _memory_key(voter_name, key, value, confidence, student_id, module_id, memory_type)

        with advisory_lock(db, f"idempotency:memory:{content_key}"):
            record = self._idem.check(db, content_key)
            if record and record.status == "completed":
                return False

            try:
                self._idem.acquire(db, content_key)
                self._idem.complete(db, content_key, response_body={"deduped": True})
                return True
            except IdempotencyConflict:
                return False

    def dead_letter_count(
        self,
        db: Session,
        window_hours: int | None = None,
    ) -> int:
        """Count events that exhausted their retries (dead letters)."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours or self._window_hours)
        return (
            db.query(func.count(IdempotencyKey.id))
            .filter(
                IdempotencyKey.status == "failed",
                IdempotencyKey.created_at > cutoff,
            )
            .scalar()
        ) or 0

    # ── Propagation baggage integration ──────────────────────────

    def _tag_baggage(self, dedup_key: str, outcome: str) -> None:
        """Tag the current PropagationContext with dedup metadata."""
        try:
            ctx = correlation_engine.get_current()
            if ctx is not None:
                short_key = dedup_key[-16:]
                current_baggage = ctx.baggage.items.copy()
                dedup_keys = {
                    k: v for k, v in current_baggage.items()
                    if k.startswith("dedup:")
                }
                n = len(dedup_keys)
                if n < MAX_BAGGAGE_KEYS:
                    ctx.baggage.set(f"dedup:{n}", f"{outcome}:{short_key}")
        except Exception:
            pass

    @staticmethod
    def _deserialize(body: str | None) -> Any:
        if body is None:
            return None
        try:
            return json.loads(body)
        except (json.JSONDecodeError, TypeError):
            return body


# ── Propagated dedup via Baggage ───────────────────────────────────


def extract_dedup_keys_from_propagation() -> list[dict[str, str]]:
    """Extract dedup metadata from the active PropagationContext baggage.

    Returns list of {outcome, key_suffix} for each dedup: key.
    """
    results: list[dict[str, str]] = []
    try:
        ctx = correlation_engine.get_current()
        if ctx is not None:
            for k, v in ctx.baggage.items.items():
                if k.startswith("dedup:"):
                    parts = v.split(":", 1)
                    results.append({
                        "slot": k,
                        "outcome": parts[0] if len(parts) > 0 else "",
                        "key_suffix": parts[1] if len(parts) > 1 else "",
                    })
    except Exception:
        pass
    return results


# ── Global singleton ───────────────────────────────────────────────

distributed_dedup = DistributedDedupEngine()
