"""
Modelo de Competencia.
Competencias institucionales UPAO, de carrera y de curso.
"""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class CompetencyType(str, enum.Enum):
    """Tipos de competencia."""
    INSTITUTIONAL = "institutional"
    CAREER = "career"
    COURSE = "course"


class Competency(Base):
    __tablename__ = "competencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    competency_type = Column(
        Enum(CompetencyType, name="competencytype", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    cycle = Column(Integer, nullable=True)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    course_associations = relationship(
        "CourseCompetency", back_populates="competency", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Competency {self.name} ({self.competency_type.value})>"


class CourseCompetency(Base):
    __tablename__ = "course_competencies"

    course_id = Column(String(36), ForeignKey("courses.id"), primary_key=True)
    competency_id = Column(String(36), ForeignKey("competencies.id"), primary_key=True)

    course = relationship("Course", back_populates="competency_associations")
    competency = relationship("Competency", back_populates="course_associations")

    def __repr__(self) -> str:
        return f"<CourseCompetency course={self.course_id} competency={self.competency_id}>"
