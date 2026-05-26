import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    prerequisite_course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    course = relationship("Course", foreign_keys=[course_id], backref="prerequisites_as_course")
    prerequisite_course = relationship("Course", foreign_keys=[prerequisite_course_id], backref="prerequisites_as_prerequisite")

    def __repr__(self) -> str:
        return f"<CoursePrerequisite course={self.course_id} requires={self.prerequisite_course_id}>"
