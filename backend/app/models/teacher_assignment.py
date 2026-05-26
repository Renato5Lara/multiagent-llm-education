import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    institutional_course_id = Column(String(36), ForeignKey("institutional_courses.id"), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    teacher = relationship("User", back_populates="teacher_assignments")
    institutional_course = relationship("InstitutionalCourse")

    def __repr__(self) -> str:
        return f"<TeacherAssignment teacher={self.teacher_id} course={self.institutional_course_id}>"
