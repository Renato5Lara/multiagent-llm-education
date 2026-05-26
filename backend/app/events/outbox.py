"""
Event Outbox Pattern.

Persiste eventos de dominio en la misma transaccion que los datos de negocio,
asegurando consistencia atomica y habilitando replayability.

Arquitectura:
    Service -> UoW.add_event() -> EventOutbox (persistido en misma TX)
    OutboxService.publish_pending() -> marca como published (future: broker)

Fases:
    Fase 1 (actual):  persistencia atomica + mark published
    Fase 2 (future):  enviar a handlers locales / dominio
    Fase 3 (future):  enviar a brokers externos (NATS, Kafka)
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.event_outbox import EventOutbox

logger = logging.getLogger(__name__)


class OutboxService:
    """Servicio de outbox.

    Responsabilidades:
    - Publicar eventos pendientes (mark as published)
    - Reintentar eventos fallidos
    - Consultar eventos por aggregate / correlation
    - Monitorear salud del outbox
    """

    def publish_pending(self, db: Session, batch_size: int = 50) -> int:
        """Publica eventos pendientes.

        Usa FOR UPDATE SKIP LOCKED en PostgreSQL para evitar
        contention entre workers sin bloquearse mutuamente.

        En Fase 1: solo marca como 'published'.
        En Fase 2: dispara handlers de dominio.
        En Fase 3: envia a broker externo.
        """
        events = self._fetch_pending(db, batch_size)
        if not events:
            return 0

        now = datetime.now(timezone.utc)
        published = 0

        for event in events:
            try:
                self._publish_event(event, now)
                published += 1
            except Exception as exc:
                self._mark_failed(event, exc)

        db.commit()
        logger.info("Outbox: published %d/%d events", published, len(events))
        return published

    def _fetch_pending(self, db: Session, batch_size: int) -> list[EventOutbox]:
        query = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.status == "pending",
                EventOutbox.retry_count < EventOutbox.max_retries,
            )
            .order_by(EventOutbox.created_at.asc())
        )

        dialect = db.bind.dialect.name if db.bind else "sqlite"
        if dialect == "postgresql":
            query = query.with_for_update(skip_locked=True)

        return query.limit(batch_size).all()

    def _publish_event(self, event: EventOutbox, now: datetime) -> None:
        logger.info(
            "Publishing event: %s[%s] (id=%s, correlation=%s)",
            event.event_type, event.aggregate_id, event.id, event.correlation_id,
        )
        event.status = "published"
        event.published_at = now
        event.updated_at = now

    def _mark_failed(self, event: EventOutbox, exc: Exception) -> None:
        event.retry_count = (event.retry_count or 0) + 1
        event.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        event.status = "failed" if event.retry_count >= event.max_retries else "pending"
        event.updated_at = datetime.now(timezone.utc)
        logger.warning(
            "Event %s failed (retry %d/%d): %s",
            event.id, event.retry_count, event.max_retries, event.last_error,
        )

    # -- Consultas --

    def count_pending(self, db: Session) -> int:
        return (
            db.query(EventOutbox)
            .filter(EventOutbox.status == "pending")
            .count()
        )

    def count_failed(self, db: Session) -> int:
        return (
            db.query(EventOutbox)
            .filter(EventOutbox.status == "failed")
            .count()
        )

    def get_events_by_aggregate(
        self, db: Session, aggregate_id: str, limit: int = 100,
    ) -> list[EventOutbox]:
        return (
            db.query(EventOutbox)
            .filter(EventOutbox.aggregate_id == aggregate_id)
            .order_by(EventOutbox.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_events_by_correlation(
        self, db: Session, correlation_id: str, limit: int = 100,
    ) -> list[EventOutbox]:
        return (
            db.query(EventOutbox)
            .filter(EventOutbox.correlation_id == correlation_id)
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
            .all()
        )

    # -- Reintentos --

    def retry_failed(self, db: Session, max_events: int = 20) -> int:
        """Reintenta eventos fallidos que aun tienen retries disponibles."""
        events = (
            db.query(EventOutbox)
            .filter(
                EventOutbox.status == "failed",
                EventOutbox.retry_count < EventOutbox.max_retries,
            )
            .limit(max_events)
            .all()
        )
        for event in events:
            event.status = "pending"
            event.updated_at = datetime.now(timezone.utc)

        if events:
            db.commit()
            logger.info("Outbox: requeued %d failed events", len(events))

        return len(events)


outbox_service = OutboxService()
