"""
DedupEventBus, IdempotentConsumer, and ReplayGuard.

Provides exactly-once event dispatch and processing guarantees
on top of the existing OutboxService and IdempotencyService.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    IdempotencyConflict,
)
from app.models.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


# ── DedupEventBus ──────────────────────────────────────────────────


class DedupEventBus:
    """Wraps event dispatch with idempotency checks.

    Before persisting an event (via UnitOfWork.add_event), checks
    if an equivalent event was already dispatched.  If so, returns
    the cached result (replay).  If a concurrent dispatch is in
    progress, raises IdempotencyConflict.

    Idempotency key strategies:
      - content-hash:   derived from (event_type, aggregate_id, payload)
      - explicit:       caller-provided key
      - trace-derived:  from PropagationContext (trace_id + span_id)
    """

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
    ):
        self._idem = idempotency_service or IdempotencyService()

    def dispatch(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        publish: Callable[[Session, EventOutbox], None] | None = None,
    ) -> EventOutbox | None:
        """Dispatch an event with idempotency protection.

        Args:
            db: SQLAlchemy session
            event_type: Domain event type
            aggregate_id: Entity that originated the event
            payload: Event data
            idempotency_key: Optional explicit key (auto-generated if None)
            trace_id: Optional trace ID from PropagationContext
            causation_id: Optional causation chain ID
            publish: Optional callback to run on first dispatch
                     (eg UnitOfWork.add_event)

        Returns:
            EventOutbox on first dispatch, or None if replayed (already dispatched).

        Raises:
            IdempotencyConflict: if concurrent dispatch in progress
        """
        key = idempotency_key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )

        record = self._idem.acquire(
            db,
            key,
            event_type=event_type,
            aggregate_id=aggregate_id,
            trace_id=trace_id,
            causation_id=causation_id,
        )

        if record.status == "completed":
            logger.info(
                "Replayed event %s[%s] via key %s",
                event_type, aggregate_id, key,
            )
            return None

        if publish:
            event = publish(db, record)
        else:
            event = self._default_publish(db, record, event_type, aggregate_id, payload)

        self._idem.complete(
            db, key,
            response_status=200,
            response_body={"event_id": event.id},
        )
        return event

    def _default_publish(
        self,
        db: Session,
        key_record: Any,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None,
    ) -> EventOutbox:
        event = EventOutbox(
            event_type=event_type,
            aggregate_id=aggregate_id,
            correlation_id=key_record.trace_id or key_record.key,
            causation_id=key_record.causation_id or key_record.id,
            payload=payload or {},
        )
        db.add(event)
        db.flush()
        logger.info(
            "Dispatched %s[%s] (event=%s, key=%s)",
            event_type, aggregate_id, event.id, key_record.key,
        )
        return event


# ── IdempotentConsumer ──────────────────────────────────────────────


class IdempotentConsumer:
    """Exactly-once event processing wrapper.

    Example::

        consumer = IdempotentConsumer(idempotency_service)
        for event in outbox_service.fetch_pending(db):
            consumer.process(
                db, event,
                handler=my_event_handler,
            )
    """

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
    ):
        self._idem = idempotency_service or IdempotencyService()
        self._stats = {
            "processed": 0,
            "replayed": 0,
            "failed": 0,
            "conflicts": 0,
        }

    def process(
        self,
        db: Session,
        event: EventOutbox,
        handler: Callable[[EventOutbox], Any],
        *,
        idempotency_key: str | None = None,
    ) -> Any:
        """Process an event exactly-once.

        Args:
            db: SQLAlchemy session
            event: The event to process
            handler: Callable that does the actual work
            idempotency_key: Optional explicit key

        Returns:
            Handler result on first processing, or cached result on replay.

        Raises:
            IdempotencyConflict: if concurrent processing in progress
            Exception: from handler (key marked as failed)
        """
        key = idempotency_key or IdempotencyKeyGenerator.from_content(
            event.event_type,
            event.aggregate_id,
            event.payload,
            prefix="consume",
        )

        record = self._idem.acquire(
            db, key,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            trace_id=event.correlation_id,
            causation_id=event.causation_id,
        )

        if record.status == "completed":
            self._stats["replayed"] += 1
            logger.info(
                "Replayed consumer for event %s[%s]",
                event.event_type, event.aggregate_id,
            )
            return _deserialize_body(record.response_body)

        try:
            result = handler(event)
            self._idem.complete(
                db, key,
                response_status=200,
                response_body=result,
            )
            self._stats["processed"] += 1
            return result
        except IdempotencyConflict:
            self._stats["conflicts"] += 1
            raise
        except Exception as exc:
            self._idem.fail(db, key, reason=str(exc))
            self._stats["failed"] += 1
            raise

    @property
    def stats(self) -> dict[str, int]:
        return dict(self._stats)

    def reset_stats(self) -> None:
        self._stats = {"processed": 0, "replayed": 0, "failed": 0, "conflicts": 0}


def _deserialize_body(body: str | None) -> Any:
    if body is None:
        return None
    import json
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return body


# ── ReplayGuard ────────────────────────────────────────────────────


class ReplayGuard:
    """Detects and prevents event replay attacks or accidental redelivery.

    A "replay" is when an event is *re-dispatched* after having already
    been completed.  The ReplayGuard can be configured to:
      - SILENT:     silently return cached result (default)
      - WARN:       log a warning but return cached result
      - REJECT:     raise ReplayDetected error
    """

    MODE_SILENT = "silent"
    MODE_WARN = "warn"
    MODE_REJECT = "reject"

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
        mode: str = MODE_WARN,
    ):
        self._idem = idempotency_service or IdempotencyService()
        self._mode = mode

    def guard(
        self,
        db: Session,
        event_type: str,
        aggregate_id: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotency_key: str | None = None,
    ) -> bool:
        """Check if an event would be a replay.

        Returns True if the event is safe to dispatch (not a replay).
        Returns False if event was already dispatched and mode is SILENT.
        Raises ReplayDetected if mode is REJECT and replay found.
        """
        key = idempotency_key or IdempotencyKeyGenerator.from_content(
            event_type, aggregate_id, payload,
        )

        record = self._idem.check(db, key)

        if record is None:
            return True

        if record.status == "completed":
            msg = f"Replay detected: {event_type}[{aggregate_id}] via key {key}"

            if self._mode == ReplayGuard.MODE_SILENT:
                return False

            if self._mode == ReplayGuard.MODE_WARN:
                logger.warning(msg)
                return False

            if self._mode == ReplayGuard.MODE_REJECT:
                logger.error(msg)
                raise ReplayDetected(event_type, aggregate_id, key)

        if record.status == "in_progress":
            raise IdempotencyConflict(key)

        return True


class ReplayDetected(IdempotencyConflict):
    """Raised when a replayed event is detected in REJECT mode."""

    def __init__(self, event_type: str, aggregate_id: str, key: str):
        self.event_type = event_type
        self.aggregate_id = aggregate_id
        super().__init__(key)
