"""
Modelo de Perfil de Estudiante.
Almacena las preferencias multimodales del estudiante.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True)
    preferred_modalities = Column(JSON, nullable=False)
    dominant_style = Column(String(50), nullable=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    student = relationship("User", back_populates="student_profile")

    def __repr__(self) -> str:
        return f"<StudentProfile student={self.student_id} style={self.dominant_style}>"
