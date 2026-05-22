"""
Modelo de Intento de Evaluación.
Almacena preguntas, respuestas y resultados de una evaluación.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class EvaluationAttempt(Base):
    __tablename__ = "evaluation_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    module_id = Column(String(36), ForeignKey("path_modules.id"), nullable=True)
    questions = Column(JSON, nullable=False)
    answers = Column(JSON, nullable=True)
    score = Column(Float, nullable=True)
    max_score = Column(Integer, nullable=False)
    passed = Column(Integer, default=0)
    attempted_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)

    student = relationship("User")
    course = relationship("Course")

    def __repr__(self) -> str:
        return f"<EvaluationAttempt student={self.student_id} score={self.score}/{self.max_score}>"
