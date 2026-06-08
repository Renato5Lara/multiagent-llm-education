import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class WeeklyPedagogicalPlan(Base):
    __tablename__ = "weekly_pedagogical_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False, index=True)
    topic = Column(String(255), nullable=False)
    objectives = Column(JSON, nullable=False, default=list)
    bloom_target = Column(Integer, nullable=False, default=3)
    pedagogical_style = Column(String(80), nullable=False)
    pedagogical_intention = Column(Text, nullable=False)
    preferred_modality = Column(String(80), nullable=False)
    orchestration_status = Column(String(30), nullable=False, default="generated")
    retrieval_summary = Column(JSON, nullable=False, default=dict)
    pedagogical_structure = Column(JSON, nullable=False, default=dict)
    adaptive_plan = Column(JSON, nullable=False, default=dict)
    multimodal_plan = Column(JSON, nullable=False, default=dict)
    prompt_plan = Column(JSON, nullable=False, default=dict)
    consistency_validation = Column(JSON, nullable=False, default=dict)
    consensus_result = Column(JSON, nullable=False, default=dict)
    generated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    validated_at = Column(DateTime(timezone=True), nullable=True)

    course = relationship("Course")
    teacher = relationship("User")

    def __repr__(self) -> str:
        return f"<WeeklyPedagogicalPlan course={self.course_id} week={self.week_number}>"
