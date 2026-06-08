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
    PENDING_ACTIVATION = "pending_activation"
    ACTIVO = "activo"
    COMPLETADO = "completado"
    ABANDONADO = "abandonado"


class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    enrolled_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    status = Column(
        Enum(EnrollmentStatus, name="enrollmentstatus", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        default=EnrollmentStatus.PENDING_ACTIVATION,
        nullable=False,
    )
    context_key = Column(String(255), nullable=True)

    course = relationship("Course", back_populates="enrollments")
    student = relationship("User", back_populates="enrollments", foreign_keys=[student_id])
    teacher = relationship("User", foreign_keys=[teacher_id])
    educational_context = relationship("EducationalContext", back_populates="enrollment", uselist=False)

    def __repr__(self) -> str:
        return f"<Enrollment student={self.student_id} course={self.course_id} status={self.status}>"
