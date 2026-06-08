import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class EducationalContextStatus(str, enum.Enum):
    PENDING = "pending"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    PARTIAL = "partial"
    RECOVERING = "recovering"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class EducationalContext(Base):
    __tablename__ = "educational_contexts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    enrollment_id = Column(String(36), ForeignKey("enrollments.id"), nullable=False, unique=True)
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=True)

    status = Column(
        Enum(
            EducationalContextStatus,
            name="educationalcontextstatus",
            use_enum_values=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=EducationalContextStatus.PENDING,
        nullable=False,
    )

    swarm_config = Column(JSON, nullable=True)
    adaptive_params = Column(JSON, nullable=True)
    shared_memory_key = Column(String(255), nullable=True, unique=True)
    activation_attempts = Column(Integer, default=0, nullable=False)
    last_error = Column(String(500), nullable=True)

    activated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    enrollment = relationship("Enrollment", back_populates="educational_context")
    student = relationship("User", foreign_keys=[student_id])
    course = relationship("Course", foreign_keys=[course_id])
    teacher = relationship("User", foreign_keys=[teacher_id])

    def __repr__(self) -> str:
        return f"<EducationalContext {self.id[:8]} enrollment={self.enrollment_id[:8]} status={self.status}>"
