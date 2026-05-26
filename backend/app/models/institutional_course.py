import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class InstitutionalCourse(Base):
    __tablename__ = "institutional_courses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    credits = Column(Integer, nullable=False, default=0)
    cycle = Column(Integer, nullable=False, index=True)
    hours_theory = Column(Integer, nullable=True)
    hours_practice = Column(Integer, nullable=True)
    hours_lab = Column(Integer, nullable=True)
    competencies = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    prerequisites = relationship(
        "InstitutionalCourse",
        secondary="institutional_course_prerequisites",
        primaryjoin="InstitutionalCourse.id == InstitutionalCoursePrerequisite.course_id",
        secondaryjoin="InstitutionalCourse.id == InstitutionalCoursePrerequisite.prerequisite_id",
        backref="required_by",
    )

    def __repr__(self) -> str:
        return f"<InstitutionalCourse {self.code}: {self.name}>"


class InstitutionalCoursePrerequisite(Base):
    __tablename__ = "institutional_course_prerequisites"

    course_id = Column(String(36), ForeignKey("institutional_courses.id"), primary_key=True)
    prerequisite_id = Column(String(36), ForeignKey("institutional_courses.id"), primary_key=True)
