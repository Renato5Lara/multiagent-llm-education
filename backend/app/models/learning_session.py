import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.db.base import Base


class LearningSession(Base):
    __tablename__ = "learning_sessions"

    id = Column(String, primary_key=True, default=lambda: uuid.uuid4().hex[:16])
    student_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False, index=True)
    module_id = Column(String, ForeignKey("path_modules.id"), nullable=True)
    enrollment_id = Column(String, ForeignKey("enrollments.id"), nullable=True)

    status = Column(String, default="active", index=True)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_minutes = Column(Float, nullable=True)

    swarm_activated = Column(String, nullable=True)
    context_key = Column(String, nullable=True)

    metadata_json = Column(JSON, default=dict)

    student = relationship("User", backref="learning_sessions")
    course = relationship("Course", backref="learning_sessions")
    module = relationship("PathModule", backref="learning_sessions")

    def end(self):
        now = datetime.now(timezone.utc)
        self.ended_at = now
        self.status = "completed"
        if self.started_at:
            start = self.started_at
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            duration = (now - start).total_seconds()
            self.duration_minutes = round(duration / 60, 2)
