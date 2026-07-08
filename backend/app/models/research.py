"""
Modelos de evidencia experimental (Research & Experiment Layer).

ExperimentResult materializa la comparación pre→post por estudiante
(diseño pre-experimental de un solo grupo). ResearchMetric es el event-log
genérico de métricas de investigación: discriminador `metric_type` + valor
numérico + payload, para instrumentar sin migraciones por métrica.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExperimentResult(Base):
    __tablename__ = "experiment_results"
    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="uq_experiment_result_student_course"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id"), nullable=False)
    pre_attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_test_attempts.id"), nullable=False
    )
    post_attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_test_attempts.id"), nullable=False
    )
    pre_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    post_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    absolute_gain: Mapped[float] = mapped_column(Float, nullable=False)
    percent_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    normalized_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    pre_level: Mapped[str] = mapped_column(String(20), nullable=False)
    post_level: Mapped[str] = mapped_column(String(20), nullable=False)
    pre_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    post_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group_label: Mapped[str] = mapped_column(String(30), nullable=False, default="Experimental")
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    student = relationship("User")
    course = relationship("Course")
    pre_attempt = relationship("KnowledgeTestAttempt", foreign_keys=[pre_attempt_id])
    post_attempt = relationship("KnowledgeTestAttempt", foreign_keys=[post_attempt_id])

    def __repr__(self) -> str:
        return (
            f"<ExperimentResult student={self.student_id} "
            f"pre={self.pre_percentage} post={self.post_percentage}>"
        )


class ResearchMetric(Base):
    __tablename__ = "research_metrics"
    __table_args__ = (
        Index("ix_rm_student_type", "student_id", "metric_type"),
        Index("ix_rm_course_type_time", "course_id", "metric_type", "recorded_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    course_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("courses.id"), nullable=True
    )
    metric_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )

    def __repr__(self) -> str:
        return f"<ResearchMetric {self.metric_type} value={self.value}>"
