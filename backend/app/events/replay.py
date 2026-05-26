"""
Event Replay Service — safe outbox event replay with idempotency protection.

Supports:
  - Replay by event_id, event_type, aggregate_id, or time range
  - Dry-run mode for testing without side effects
  - Automatic skip of already-replayed events (via idempotency key)
  - Progress reporting with stats
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    idempotency_service as _global_idem,
)
from app.models.event_outbox import EventOutbox
from app.models.idempotency_key import IdempotencyKey

logger = logging.getLogger(__name__)


class EventReplayService:
    """Replay events from the outbox with idempotency protection.

    Each replay is wrapped with an idempotency key derived from
    (event_type, aggregate_id, payload) so that:
      - First replay → processes the event
      - Second replay → returns cached result (no side effects)
    """

    def __init__(
        self,
        idempotency_service: IdempotencyService | None = None,
    ):
        self._idem = idempotency_service or _global_idem

    def replay_by_id(
        self,
        db: Session,
        event_id: str,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Replay a single event by its ID.

        Returns dict with replay result and metadata.
        """
        event = (
            db.query(EventOutbox)
            .filter(EventOutbox.id == event_id)
            .first()
        )
        if event is None:
            return {"event_id": event_id, "status": "not_found"}

        return self._replay_single(db, event, handler, dry_run=dry_run)

    def replay_by_type(
        self,
        db: Session,
        event_type: str,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
        limit: int = 100,
        status_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Replay all events of a given type."""
        query = (
            db.query(EventOutbox)
            .filter(EventOutbox.event_type == event_type)
        )
        if status_filter:
            query = query.filter(EventOutbox.status == status_filter)
        query = query.order_by(EventOutbox.created_at.asc()).limit(limit)

        results: list[dict[str, Any]] = []
        for event in query.all():
            result = self._replay_single(db, event, handler, dry_run=dry_run)
            results.append(result)
        return results

    def replay_by_aggregate(
        self,
        db: Session,
        aggregate_id: str,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Replay all events for a given aggregate."""
        events = (
            db.query(EventOutbox)
            .filter(EventOutbox.aggregate_id == aggregate_id)
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .all()
        )
        results: list[dict[str, Any]] = []
        for event in events:
            result = self._replay_single(db, event, handler, dry_run=dry_run)
            results.append(result)
        return results

    def replay_by_time_range(
        self,
        db: Session,
        since: datetime,
        until: datetime | None = None,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Replay events within a time range."""
        query = (
            db.query(EventOutbox)
            .filter(EventOutbox.created_at >= since)
        )
        if until:
            query = query.filter(EventOutbox.created_at <= until)
        query = query.order_by(EventOutbox.created_at.asc()).limit(limit)

        results: list[dict[str, Any]] = []
        for event in query.all():
            result = self._replay_single(db, event, handler, dry_run=dry_run)
            results.append(result)
        return results

    def replay_failed(
        self,
        db: Session,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Replay all failed events that still have retries available."""
        events = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.status == "failed",
                EventOutbox.retry_count < EventOutbox.max_retries,
            )
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .all()
        )
        results: list[dict[str, Any]] = []
        for event in events:
            result = self._replay_single(db, event, handler, dry_run=dry_run)
            results.append(result)
        return results

    def replay_all_pending(
        self,
        db: Session,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Replay all pending events."""
        events = (
            db.query(EventOutbox)
            .filter(EventOutbox.status == "pending")
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .all()
        )
        results: list[dict[str, Any]] = []
        for event in events:
            result = self._replay_single(db, event, handler, dry_run=dry_run)
            results.append(result)
        return results

    # ── Internal ──────────────────────────────────────────────────

    def _replay_single(
        self,
        db: Session,
        event: EventOutbox,
        handler: Callable[[EventOutbox], Any] | None = None,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Replay a single event with idempotency protection.

        Returns dict with:
          - event_id, event_type, aggregate_id
          - status: replayed | skipped | dry_run | error
          - replay_count: how many times this event was replayed
          - result: handler output (if applicable)
          - error: error message (if applicable)
        """
        dedup_key = IdempotencyKeyGenerator.from_content(
            event.event_type, event.aggregate_id, event.payload,
            prefix="replay",
        )

        record = self._idem.check(db, dedup_key)

        if record and record.status == "completed":
            replay_count = db.query(IdempotencyKey).filter(
                IdempotencyKey.key.like(
                    f"replay:content:{event.event_type}:{event.aggregate_id}%",
                ),
            ).count()

            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "status": "skipped",
                "replay_count": replay_count,
                "reason": "Already completed, use force=True to re-replay",
            }

        if dry_run:
            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "status": "dry_run",
                "replay_count": 0,
            }

        if handler is None:
            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "status": "no_handler",
            }

        try:
            self._idem.acquire(
                db, dedup_key,
                event_type=event.event_type,
                aggregate_id=event.aggregate_id,
                trace_id=event.correlation_id,
                causation_id=event.causation_id,
            )

            result = handler(event)

            self._idem.complete(db, dedup_key, response_body=result)

            event.status = "published"
            event.published_at = datetime.now(timezone.utc)
            db.commit()

            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "status": "replayed",
                "replay_count": 1,
                "result": str(result)[:500] if result is not None else None,
            }
        except Exception as exc:
            try:
                self._idem.fail(db, dedup_key, reason=str(exc))
            except Exception:
                pass
            return {
                "event_id": event.id,
                "event_type": event.event_type,
                "aggregate_id": event.aggregate_id,
                "status": "error",
                "error": str(exc)[:500],
            }

    def get_stats(
        self,
        db: Session,
        window_hours: int = 24,
    ) -> dict[str, Any]:
        """Get replay statistics."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        total_outbox = db.query(EventOutbox).filter(
            EventOutbox.created_at > cutoff,
        ).count()

        pending = db.query(EventOutbox).filter(
            EventOutbox.status == "pending",
            EventOutbox.created_at > cutoff,
        ).count()

        failed = db.query(EventOutbox).filter(
            EventOutbox.status == "failed",
            EventOutbox.created_at > cutoff,
        ).count()

        replay_keys = db.query(IdempotencyKey).filter(
            IdempotencyKey.key.like("replay:content:%"),
            IdempotencyKey.created_at > cutoff,
        ).count()

        return {
            "window_hours": window_hours,
            "total_events": total_outbox,
            "pending": pending,
            "failed": failed,
            "replay_keys_registered": replay_keys,
            "replayable_failed": db.query(EventOutbox).filter(
                EventOutbox.status == "failed",
                EventOutbox.retry_count < EventOutbox.max_retries,
                EventOutbox.created_at > cutoff,
            ).count(),
        }


# ── Global singleton ───────────────────────────────────────────────

event_replay_service = EventReplayService()
