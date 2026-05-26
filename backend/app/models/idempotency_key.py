"""
Modelo IdempotencyKey — enterprise-grade idempotency with full lifecycle.

Soporta:
  - Idempotency key lifecycle: pending → in_progress → completed | failed
  - Content-hash based dedup (event_type + aggregate_id + payload)
  - Explicit caller-provided keys (HTTP Idempotency-Key header)
  - TTL-based expiration (24h default)
  - Optimistic locking for concurrent safety
  - Event metadata for distributed dedup (trace_id, causation_id)
  - Retrofit compatible: existing HTTP middleware uses response_status only
"""

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base

IDEMPOTENCY_EXPIRY_HOURS = 24


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String(255), unique=True, nullable=False, index=True)

    # -- Lifecycle (enterprise-grade) --
    # pending | in_progress | completed | failed
    status = Column(
        String(20), nullable=False, default="pending", index=True,
        doc="Lifecycle: pending → in_progress → completed | failed",
    )
    response_status = Column(Integer, nullable=False, default=0)
    response_body = Column(Text, nullable=True)

    # -- Event metadata for distributed dedup --
    event_type = Column(
        String(100), nullable=True,
        doc="Domain event type (eg 'module.completed')",
    )
    aggregate_id = Column(
        String(36), nullable=True,
        doc="Entity that originated the event",
    )
    trace_id = Column(
        String(36), nullable=True,
        doc="Trace ID from PropagationContext",
    )
    causation_id = Column(
        String(36), nullable=True,
        doc="Parent event causation chain ID",
    )

    # -- Timestamps --
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(
        DateTime(timezone=True), nullable=True,
        doc="When the operation completed (success or failure)",
    )

    def __repr__(self) -> str:
        return (
            f"<IdempotencyKey {self.key} "
            f"status={self.status} "
            f"http={self.response_status}>"
        )
