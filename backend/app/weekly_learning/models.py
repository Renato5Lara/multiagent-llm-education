"""
SQLAlchemy models for weekly learning architecture.

CourseWeeklyPlan  — one per course, defines the overall weekly structure
CourseWeek       — one per week in a plan, stores metadata + generated content
WeekContent      — the generated pedagogical payload for a week
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class WeeklyPlan(Base):
    """
    Top-level weekly plan for a course.
    Defines the structure (num weeks, theme, progression) and tracks state.
    """
    __tablename__ = "weekly_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)
    teacher_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    total_weeks = Column(Integer, nullable=False, default=5)
    thematic_line = Column(String(500), nullable=False, doc="Línea temática del curso")
    pedagogical_intention = Column(Text, nullable=False, doc="Intención pedagógica general")

    bloom_progression = Column(JSON, nullable=False, default=list, doc="Bloom level per week [1,2,3,4,5,...]")
    week_themes = Column(JSON, nullable=False, default=list, doc="Theme per week")

    status = Column(String(30), nullable=False, default="draft", doc="draft | active | completed")
    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __mapper_args__ = {"version_id_col": version}

    course = relationship("Course")
    teacher = relationship("User")
    weeks = relationship("CourseWeek", back_populates="plan", cascade="all, delete-orphan", order_by="CourseWeek.week_number")

    def __repr__(self) -> str:
        return f"<WeeklyPlan course={self.course_id} weeks={self.total_weeks}>"


class CourseWeek(Base):
    """
    A single week in a course's weekly plan.
    Stores the week-specific configuration and references to generated content.
    """
    __tablename__ = "course_weeks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id = Column(String(36), ForeignKey("weekly_plans.id"), nullable=False, index=True)
    week_number = Column(Integer, nullable=False, index=True)

    theme = Column(String(255), nullable=False, doc="Tema de la semana")
    bloom_target = Column(Integer, nullable=False, default=1, doc="Bloom level objetivo (1-6)")
    objectives = Column(JSON, nullable=False, default=list, doc="Objetivos semanales")
    misconceptions = Column(JSON, nullable=False, default=list, doc="Misconceptions esperadas")
    real_applications = Column(JSON, nullable=False, default=list, doc="Aplicaciones reales")
    recommended_modality = Column(String(50), nullable=True, doc="Modalidad recomendada")
    multimodal_prompts = Column(JSON, nullable=False, default=list, doc="Prompts multimodales")
    evaluation_criteria = Column(JSON, nullable=False, default=list, doc="Criterios de evaluación")

    orchestration_status = Column(String(30), nullable=False, default="pending", doc="pending | running | completed | failed")
    confidence = Column(Float, nullable=True, doc="Confianza de la orquestación")
    generated_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, nullable=False, default=1)

    __mapper_args__ = {"version_id_col": version}

    plan = relationship("WeeklyPlan", back_populates="weeks")

    content = relationship("WeekContent", back_populates="week", uselist=False, cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<CourseWeek plan={self.plan_id} week={self.week_number} bloom={self.bloom_target}>"


class WeekContent(Base):
    """
    The fully generated pedagogical content for a single week.
    Populated by the swarm orchestration pipeline.
    """
    __tablename__ = "week_contents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    week_id = Column(String(36), ForeignKey("course_weeks.id"), nullable=False, unique=True, index=True)

    introduction = Column(Text, nullable=False, default="")
    pedagogical_explanation = Column(Text, nullable=False, default="")
    examples = Column(JSON, nullable=False, default=list)
    guided_practice = Column(Text, nullable=False, default="")
    storyboard = Column(Text, nullable=True, default="")
    continuity_notes = Column(Text, nullable=True, default="")

    pedagogical_stages = Column(JSON, nullable=False, default=list)
    retrieval_evidence = Column(JSON, nullable=False, default=dict)
    swarm_trace = Column(JSON, nullable=False, default=dict)
    memory_ids = Column(JSON, nullable=False, default=list)

    version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    week = relationship("CourseWeek", back_populates="content")

    def __repr__(self) -> str:
        return f"<WeekContent week={self.week_id}>"
