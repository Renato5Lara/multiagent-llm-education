"""
Modelos del instrumento experimental de conocimiento (Research & Experiment Layer).

Banco fijo de preguntas MCQ (mismo instrumento para todos los estudiantes),
intentos pre/post corregidos con nivel Básico/Intermedio/Avanzado y respuestas
normalizadas por pregunta para agregación estadística por módulo.
El LLM no participa en la construcción del instrumento.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeTestQuestion(Base):
    """Ítem del banco fijo. `options` es un atributo atómico del ítem (JSON);
    la dimensión de análisis es la respuesta, que sí se normaliza."""

    __tablename__ = "knowledge_test_questions"
    __table_args__ = (
        CheckConstraint("module_number >= 1 AND module_number <= 9", name="ck_ktq_module_range"),
        Index("ix_ktq_course_module_order", "course_code", "module_number", "order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_code: Mapped[str] = mapped_column(String(20), nullable=False, default="IS301", index=True)
    module_number: Mapped[int] = mapped_column(Integer, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list] = mapped_column(JSON, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    bloom_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<KnowledgeTestQuestion m{self.module_number} {self.topic} ({self.difficulty})>"


class KnowledgeTestAttempt(Base):
    """Un intento pre o post por (estudiante, curso). El constraint único
    garantiza que el pre-test se rinde una sola vez; un intento in_progress
    abandonado se reanuda, no se duplica."""

    __tablename__ = "knowledge_test_attempts"
    __table_args__ = (
        CheckConstraint("kind IN ('pre', 'post')", name="ck_kta_kind"),
        UniqueConstraint("student_id", "course_id", "kind", name="uq_kt_attempt_student_course_kind"),
        Index("ix_kta_course_kind_status", "course_id", "kind", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    course_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("courses.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(4), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_questions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    question_order: Mapped[list | None] = mapped_column(JSON, nullable=True)
    module_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    bank_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    student = relationship("User")
    course = relationship("Course")
    answers = relationship(
        "KnowledgeTestAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<KnowledgeTestAttempt {self.kind} student={self.student_id} {self.status}>"


class KnowledgeTestAnswer(Base):
    """Respuesta por pregunta. `correct_index` se copia como auditoría del
    instrumento en el momento del intento (requisito de la investigación)."""

    __tablename__ = "knowledge_test_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_kt_answer_attempt_question"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    attempt_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("knowledge_test_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_test_questions.id"), nullable=False
    )
    selected_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    attempt = relationship("KnowledgeTestAttempt", back_populates="answers")
    question = relationship("KnowledgeTestQuestion")

    def __repr__(self) -> str:
        return f"<KnowledgeTestAnswer attempt={self.attempt_id} correct={self.is_correct}>"
