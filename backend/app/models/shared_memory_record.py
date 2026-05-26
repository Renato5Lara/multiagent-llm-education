"""
SharedMemoryRecord — Collective Memory for Consensus Voters.

Each record stores an observation, inference, pattern, or signal
published by a voter during or after a consensus run. Records are
deterministic, versioned, TTL-aware, and fully traceable.

Supports:
    - student-scoped, module-scoped, and consensus-scoped memory
    - temporal memory via created_at + optional TTL
    - confidence tracking per record
    - source lineage via parent_id chains
    - trace linkage via source_trace_id / source_event_id
    - replayability via deterministic key + version
    - conflict resolution via same-key grouping
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db.base import Base


class SharedMemoryRecord(Base):
    __tablename__ = "shared_memory_records"
    __table_args__ = (
        UniqueConstraint(
            "voter_name", "student_id", "module_id",
            "memory_type", "key",
            name="uq_shared_memory_voter_scope_key",
        ),
        Index("ix_shared_memory_student_type", "student_id", "memory_type"),
        Index("ix_shared_memory_module_type", "module_id", "memory_type"),
        Index("ix_shared_memory_trace", "source_trace_id"),
    )

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # -- Who published this record --
    voter_name = Column(
        String(100), nullable=False, index=True,
    )

    # -- Scoping (all nullable for global records) --
    student_id = Column(
        String(36), nullable=True, index=True,
    )
    module_id = Column(
        String(36), nullable=True, index=True,
    )

    # -- Memory classification --
    memory_type = Column(
        String(50), nullable=False, index=True,
        doc="observation | inference | pattern | signal",
    )
    key = Column(
        String(255), nullable=False,
        doc="Semantic key for querying and dedup",
    )

    # -- Data --
    value = Column(
        JSON, nullable=False, default=dict,
        doc="The actual payload (dict or list)",
    )

    # -- Confidence (0.0 = none, 1.0 = certain) --
    confidence = Column(
        Float, nullable=False, default=1.0,
    )

    # -- Trace / event lineage --
    source_trace_id = Column(
        String(36), nullable=True,
        doc="Trace ID from the consensus run that produced this",
    )
    source_event_id = Column(
        String(36), nullable=True,
        doc="EventOutbox ID that produced this",
    )

    # -- Lineage chain: parent record --
    parent_id = Column(
        String(36), nullable=True,
        doc="ID of the previous record this derives from",
    )

    # -- Optimistic locking --
    version = Column(
        Integer, nullable=False, default=1,
    )

    __mapper_args__ = {"version_id_col": version}

    # -- TTL (null = never expires) --
    ttl_seconds = Column(
        Integer, nullable=True,
        doc="Time-to-live in seconds from created_at",
    )

    # -- Extra metadata --
    metadata_json = Column(
        JSON, nullable=True, default=dict,
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

    @property
    def is_stale(self) -> bool:
        if self.ttl_seconds is None:
            return False
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            now = now.replace(tzinfo=None)
        elapsed = (now - created).total_seconds()
        return elapsed > self.ttl_seconds

    @property
    def age_seconds(self) -> float:
        if self.created_at is None:
            return 0.0
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            now = now.replace(tzinfo=None)
        return (now - created).total_seconds()

    def __repr__(self) -> str:
        rid = self.id[:8] if self.id else "none"
        return (
            f"<SharedMemoryRecord {rid} "
            f"voter={self.voter_name} "
            f"type={self.memory_type} "
            f"key={self.key} "
            f"confidence={self.confidence:.2f}>"
        )
