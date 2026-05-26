"""
Modelo de Curso.
Un docente puede crear y gestionar cursos con estados borrador/publicado/archivado.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class CourseStatus(str, enum.Enum):
    """Estados posibles de un curso."""
    BORRADOR = "borrador"
    PUBLICADO = "publicado"
    ARCHIVADO = "archivado"


class Course(Base):
    __tablename__ = "courses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    cycle = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    status = Column(
        Enum(CourseStatus, name="coursestatus", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        default=CourseStatus.BORRADOR,
        nullable=False,
    )
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    institutional_course_id = Column(String(36), ForeignKey("institutional_courses.id"), nullable=True, index=True)
    is_institutional = Column(Boolean, default=False, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    teacher = relationship("User", back_populates="courses_taught")
    institutional_course = relationship("InstitutionalCourse", backref="course_instances")
    objectives = relationship(
        "LearningObjective", back_populates="course", cascade="all, delete-orphan"
    )
    resources = relationship(
        "Resource", back_populates="course", cascade="all, delete-orphan"
    )
    enrollments = relationship(
        "Enrollment", back_populates="course", cascade="all, delete-orphan"
    )
    competency_associations = relationship(
        "CourseCompetency", back_populates="course", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Course {self.code}: {self.name}>"
