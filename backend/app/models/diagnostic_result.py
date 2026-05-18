import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class DiagnosticResult(Base):
    __tablename__ = "diagnostic_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    profile = Column(JSON, nullable=True)
    modality_scores = Column(JSON, nullable=True)
    dominant_modality = Column(String(50), nullable=True)
    completed_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    student = relationship("User")
    course = relationship("Course")
