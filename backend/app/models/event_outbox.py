"""
Modelo EventOutbox.

Persiste eventos de dominio para el Outbox Pattern.
Cada evento se guarda en la misma transaccion que los datos de negocio,
asegurando consistencia atomica y habilitando replayability.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.db.base import Base


class EventOutbox(Base):
    __tablename__ = "event_outbox"

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # -- Identificacion del evento --
    event_type = Column(
        String(100), nullable=False, index=True,
        doc="Ej: 'module.completed', 'memory.stored'",
    )
    aggregate_id = Column(
        String(36), nullable=False, index=True,
        doc="ID de la entidad que origino el evento",
    )

    # -- Trazabilidad (correlation pattern) --
    correlation_id = Column(
        String(36), nullable=False, index=True,
        doc="ID que agrupa eventos de una misma causa raiz",
    )
    causation_id = Column(
        String(36), nullable=True,
        doc="ID del evento que causo este (event causation)",
    )

    # -- Datos --
    payload = Column(
        JSON, nullable=False, default=dict,
        doc="Datos del evento (dict serializable)",
    )

    # -- Ciclo de vida --
    status = Column(
        String(20), nullable=False, default="pending", index=True,
        doc="pending | published | failed | cancelled",
    )
    retry_count = Column(
        Integer, nullable=False, default=0,
    )
    max_retries = Column(
        Integer, nullable=False, default=3,
    )

    # -- Timestamps --
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    published_at = Column(
        DateTime(timezone=True), nullable=True,
    )
    last_error = Column(
        Text, nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<EventOutbox {self.id[:8]} "
            f"type={self.event_type} "
            f"agg={self.aggregate_id[:8]} "
            f"status={self.status}>"
        )
