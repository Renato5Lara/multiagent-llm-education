"""
Integration layer connecting idempotency to SharedMemory, Consensus,
and UnitOfWork.

Provides wrappers and mixins that add dedup protection, phase guards,
and causation chain safety to existing components without breaking
backward compatibility.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.db.locks import advisory_lock
from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    IdempotencyConflict,
    IdempotencyError,
)
from app.tracing import correlation_engine

logger = logging.getLogger(__name__)


# ── IdempotentSharedMemory ─────────────────────────────────────────


class IdempotentSharedMemory:
    """Idempotency wrapper around SharedMemoryStore operations.

    Wraps publish_observation with content-hash dedup and advisory
    locking.  The existing unique constraint
    (voter_name, student_id, module_id, memory_type, key) serves as
    the second line of defense.
    """

    def __init__(
        self,
        shared_memory_store: Any,
        idempotency_service: IdempotencyService | None = None,
    ):
        self._store = shared_memory_store
        self._idem = idempotency_service or IdempotencyService()

    def publish_observation(
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
        ttl_seconds: int | None = None,
        metadata_json: dict[str, Any] | None = None,
        force: bool = False,
    ) -> str | None:
        """Publish observation with idempotency dedup.

        Returns the record ID on first publish, or None on dedup.
        When force=True, bypasses idempotency check (always publishes).
        """
        if force:
            return self._store.publish_observation(
                voter_name=voter_name,
                key=key,
                value=value,
                confidence=confidence,
                student_id=student_id,
                module_id=module_id,
                memory_type=memory_type,
                ttl_seconds=ttl_seconds,
                metadata_json=metadata_json,
            )

        content_key = _memory_key(voter_name, key, value, confidence, student_id, module_id, memory_type)

        raw_record = self._idem.check(db, content_key)
        if raw_record and raw_record.status == "completed":
            logger.info(
                "Dedup memory observation: %s/%s (key=%s)",
                voter_name, key, content_key,
            )
            return None

        with advisory_lock(db, f"idempotency:memory:{content_key}"):
            raw_record = self._idem.check(db, content_key)
            if raw_record and raw_record.status == "completed":
                return None

            self._idem.acquire(db, content_key)

        try:
            record_id = self._store.publish_observation(
                voter_name=voter_name,
                key=key,
                value=value,
                confidence=confidence,
                student_id=student_id,
                module_id=module_id,
                memory_type=memory_type,
                ttl_seconds=ttl_seconds,
                metadata_json=metadata_json,
            )
            self._idem.complete(db, content_key, response_body={"record_id": record_id})
            return record_id
        except Exception as exc:
            self._idem.fail(db, content_key, reason=str(exc))
            raise


def _memory_key(
    voter_name: str,
    key: str,
    value: dict[str, Any],
    confidence: float,
    student_id: str | None,
    module_id: str | None,
    memory_type: str,
) -> str:
    raw = json.dumps(
        {
            "voter": voter_name,
            "key": key,
            "value": value,
            "confidence": confidence,
            "student_id": student_id,
            "module_id": module_id,
            "type": memory_type,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"idm:memory:{h}"


# ── IdempotentConsensusGuard ───────────────────────────────────────


class IdempotentConsensusGuard:
    """Phase-level idempotency for ConsensusEngine.run().

    Divides consensus execution into named phases:
      - vote_collection
      - aggregation
      - shared_memory_publish
      - diagnostics

    Each phase has its own idempotency key derived from
    (module_id, student_id, phase_name).  On retry, already
    completed phases are skipped.
    """

    PHASES = ["vote_collection", "aggregation", "shared_memory_publish", "diagnostics"]

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
    ):
        self._idem = idempotency_service or IdempotencyService()

    def phase_key(self, module_id: str, student_id: str, phase: str) -> str:
        return f"idm:consensus:{module_id}:{student_id}:phase:{phase}"

    def is_phase_completed(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase: str,
    ) -> bool:
        """Check if a consensus phase has already completed."""
        key = self.phase_key(module_id, student_id, phase)
        record = self._idem.check(db, key)
        return record is not None and record.status == "completed"

    def acquire_phase(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase: str,
    ) -> bool:
        """Acquire a consensus phase for execution.

        Returns True if the phase was acquired (first time).
        Returns False if already completed (skip).
        Raises IdempotencyConflict if in progress by another worker.
        """
        if phase not in self.PHASES:
            raise IdempotencyError(f"unknown consensus phase: {phase}")
        key = self.phase_key(module_id, student_id, phase)
        try:
            self._idem.acquire(db, key)
            return True
        except IdempotencyConflict:
            record = self._idem.check(db, key)
            if record and record.status == "completed":
                return False
            raise

    def complete_phase(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase: str,
        result: Any = None,
    ) -> None:
        key = self.phase_key(module_id, student_id, phase)
        self._idem.complete(db, key, response_body=result)

    def fail_phase(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase: str,
        reason: str | None = None,
    ) -> None:
        key = self.phase_key(module_id, student_id, phase)
        self._idem.fail(db, key, reason=reason)

    def run_with_phases(
        self,
        db: Session,
        module_id: str,
        student_id: str,
        phase_handlers: dict[str, Callable[[], Any]],
    ) -> dict[str, Any]:
        """Execute consensus phases with idempotency guards.

        phase_handlers: map of phase_name → callable
        Returns: map of phase_name → result
        """
        results: dict[str, Any] = {}

        for phase in self.PHASES:
            handler = phase_handlers.get(phase)
            if handler is None:
                continue

            if self.is_phase_completed(db, module_id, student_id, phase):
                logger.info("Skipping completed consensus phase: %s", phase)
                continue

            self.acquire_phase(db, module_id, student_id, phase)
            try:
                result = handler()
                self.complete_phase(db, module_id, student_id, phase, result)
                results[phase] = result
            except Exception as exc:
                self.fail_phase(db, module_id, student_id, phase, reason=str(exc))
                raise

        return results


# ── IdempotentUnitOfWork ───────────────────────────────────────────


class IdempotentUnitOfWork:
    """Extends UnitOfWork with outbox event dedup and double-commit guard.

    Wraps add_event to check for duplicate events within the same
    transaction (content-hash based).  Wraps commit to prevent
    accidental double-commit of the same event set.
    """

    def __init__(self, uow: Any, idempotency_service: IdempotencyService | None = None):
        self._uow = uow
        self._idem = idempotency_service or IdempotencyService()
        self._seen_hashes: set[str] = set()
        self._committed_keys: set[str] = set()

    @property
    def db(self):
        return self._uow.db

    def add_event(
        self,
        event_type: str,
        aggregate_id: str,
        payload: dict | None = None,
        *,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> Any:
        """Add event with in-transaction dedup.

        If the same event (type + aggregate + payload hash) was
        already added in this UoW, returns the existing event
        instead of creating a duplicate.
        """
        event_hash = _event_hash(event_type, aggregate_id, payload or {})

        if event_hash in self._seen_hashes:
            logger.debug(
                "Dedup event in UoW: %s[%s]",
                event_type, aggregate_id,
            )
            return None

        self._seen_hashes.add(event_hash)

        event = self._uow.add_event(
            event_type,
            aggregate_id,
            payload=payload,
            correlation_id=_resolve_correlation_id(correlation_id),
            causation_id=causation_id,
        )
        return event

    def commit(self) -> None:
        """Commit with double-commit guard."""
        if self._uow._committed:
            logger.warning("IdempotentUoW: commit skipped (already committed)")
            return
        self._uow.commit()

    def rollback(self) -> None:
        self._uow.rollback()
        self._seen_hashes.clear()
        self._committed_keys.clear()

    def close(self) -> None:
        self._uow.close()


def _resolve_correlation_id(explicit: str | None) -> str | None:
    if explicit is not None:
        return explicit
    try:
        from app.tracing import correlation_engine as _ce
        current = _ce.get_current()
        if current is not None:
            return current.correlation.correlation_id
    except Exception:
        pass
    return None


def _event_hash(event_type: str, aggregate_id: str, payload: dict) -> str:
    raw = json.dumps(
        {"type": event_type, "aggregate": aggregate_id, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Propagation-safe helpers ──────────────────────────────────────

# Module-level sequence counter keyed by span_id.
# ContextVar serialises/deserialises PropagationContext, so we cannot
# store mutable state on the context object itself.  This dict is
# cleared when the span ends (via CorrelationEngine.end).
_idem_seq_registry: dict[str, int] = {}


def get_idempotency_key_from_propagation(operation: str) -> str | None:
    """Derive an idempotency key from the active PropagationContext.

    Uses trace_id + span_id + sequence number for uniqueness
    within a distributed trace.
    """
    try:
        ce = correlation_engine
        ctx = ce.get_current()
        if ctx is not None:
            span_id = ctx.span.span_id
            seq = _idem_seq_registry.get(span_id, 0) + 1
            _idem_seq_registry[span_id] = seq
            return IdempotencyKeyGenerator.from_propagation(
                ctx.span.trace_id,
                span_id,
                seq,
            )
    except Exception:
        pass
    return None
