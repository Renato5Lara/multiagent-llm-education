"""
Modelo de Inscripción (Enrollment).
Relaciona estudiantes con cursos.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class EnrollmentStatus(str, enum.Enum):
    """Estados de inscripción."""
    ACTIVO = "activo"
    COMPLETADO = "completado"
    ABANDONADO = "abandonado"


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    enrolled_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status = Column(
        Enum(EnrollmentStatus, name="enrollmentstatus"),
        default=EnrollmentStatus.ACTIVO,
        nullable=False,
    )

    # Relaciones
    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments")

    def __repr__(self) -> str:
        return f"<Enrollment student={self.student_id} course={self.course_id}>"
