"""
AgentDecisionTraceRecord — ORM model for agent decision traces.

Stores the complete AgentDecisionTrace produced by each agent invocation.
Indexed for fast retrieval by session, context_key, and correlation_id
to support the reasoning chain API.

Relationship to other tables:
  - session_id → learning_sessions.id (optional, for student sessions)
  - student_id → users.id (soft reference, no FK for write performance)
  - causation_id → self (optional self-referential for chain navigation)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    JSON,
    String,
    Text,
)

from app.db.base import Base


class AgentDecisionTraceRecord(Base):
    __tablename__ = "agent_decision_traces"
    __table_args__ = (
        Index("ix_adt_correlation", "correlation_id"),
        Index("ix_adt_session", "session_id"),
        Index("ix_adt_context_key", "context_key"),
        Index("ix_adt_student_agent", "student_id", "agent_name"),
        Index("ix_adt_causal_chain", "correlation_id", "sequence"),
        Index("ix_adt_created_at", "created_at"),
    )

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # ── Identity ────────────────────────────────────────────────
    trace_id = Column(String(36), nullable=False, unique=True, index=True)
    agent_id = Column(String(36), nullable=False)
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(String(100), nullable=False)

    # ── Invocation context ───────────────────────────────────────
    session_id = Column(String(36), nullable=True)
    context_key = Column(String(255), nullable=False)
    student_id = Column(String(36), nullable=False)
    course_id = Column(String(36), nullable=False)

    # ── Causal chain ─────────────────────────────────────────────
    correlation_id = Column(String(36), nullable=True)
    causation_id = Column(String(36), nullable=True)
    sequence = Column(Integer, nullable=False, default=0)

    # ── Inputs summary ───────────────────────────────────────────
    state_inputs = Column(JSON, nullable=False, default=dict)
    memory_records_queried = Column(Integer, nullable=False, default=0)

    # ── Reasoning payload (stored as JSON for flexibility) ───────
    evidence = Column(JSON, nullable=False, default=list)
    reasoning_steps = Column(JSON, nullable=False, default=list)
    dimensions = Column(JSON, nullable=False, default=list)

    # ── Decision summary ─────────────────────────────────────────
    decision_summary = Column(Text, nullable=False, default="")
    confidence = Column(Float, nullable=False, default=0.0)
    output_keys = Column(JSON, nullable=False, default=list)

    # ── Performance ──────────────────────────────────────────────
    elapsed_ms = Column(Float, nullable=False, default=0.0)

    # ── Outcome ──────────────────────────────────────────────────
    success = Column(Boolean, nullable=False, default=True)
    error = Column(Text, nullable=True)

    # ── Timestamps ───────────────────────────────────────────────
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        tid = self.trace_id[:8] if self.trace_id else "none"
        return (
            f"<AgentDecisionTrace {tid} "
            f"agent={self.agent_name} "
            f"seq={self.sequence} "
            f"ok={self.success}>"
        )

    def to_schema_dict(self) -> dict:
        """Convert ORM record to dict matching AgentDecisionTrace schema."""
        return {
            "trace_id": self.trace_id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "session_id": self.session_id,
            "context_key": self.context_key,
            "student_id": self.student_id,
            "course_id": self.course_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "sequence": self.sequence,
            "state_inputs": self.state_inputs or {},
            "memory_records_queried": self.memory_records_queried or 0,
            "evidence": self.evidence or [],
            "reasoning_steps": self.reasoning_steps or [],
            "dimensions": self.dimensions or [],
            "decision_summary": self.decision_summary or "",
            "confidence": self.confidence or 0.0,
            "output_keys": self.output_keys or [],
            "elapsed_ms": self.elapsed_ms or 0.0,
            "success": self.success,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
        }
