"""
Modelos de Progreso Estudiantil.
LearningPath, PathModule y StudentProgress para el seguimiento adaptativo.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class LearningPath(Base):
    __tablename__ = "learning_paths"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    generated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    total_modules = Column(Integer, default=0)
    # completed_modules eliminado (2026-08-09, auditoría de concurrencia): era
    # un contador cacheado, escrito solo por update_module_progress() vía un
    # COUNT() recalculado sin lock — race condition confirmada con HTTP real
    # (3/3 reproducciones, lost update silencioso) y 15/73 learning_paths
    # reales ya desincronizados en producción. Todo el resto del producto
    # (evidence_service, course_service, learning_experience_service,
    # knowledge_test_service — este último por el mismo bug, Iteración 6.1)
    # ya derivaba en vivo desde PathModule.status en vez de confiar en este
    # valor. Regla de derivación (CLAUDE.md): un atributo reconstruible
    # determinísticamente no debe persistirse. Ver migración
    # 20260809_drop_completed_modules.
    status = Column(String(20), default="active")
    knowledge_level = Column(String(20), nullable=True)
    generation_duration_ms = Column(Integer, nullable=True)
    version = Column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}

    student = relationship("User")
    course = relationship("Course")
    modules = relationship("PathModule", back_populates="path", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<LearningPath student={self.student_id} course={self.course_id}>"


class PathModule(Base):
    __tablename__ = "path_modules"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    path_id = Column(String(36), ForeignKey("learning_paths.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    order = Column(Integer, nullable=False, default=0)
    week_number = Column(Integer, nullable=True, index=True)
    status = Column(String(20), default="locked")
    # Distingue, dentro de los módulos `status="available"`, cuál es el
    # frente de trabajo real (a dónde debe navegar el estudiante) de los
    # que están disponibles por ya estar dominados y ser saltables.
    # Corrección de adaptación por nivel (auditoría causal, ago. 2026).
    is_frontier = Column(Boolean, nullable=False, default=False, server_default="false")
    bloom_level = Column(Integer, nullable=True)
    resource_id = Column(String(36), ForeignKey("resources.id"), nullable=True)
    score = Column(Float, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)

    __mapper_args__ = {"version_id_col": version}

    path = relationship("LearningPath", back_populates="modules")
    resource = relationship("Resource")

    def __repr__(self) -> str:
        return f"<PathModule {self.title} ({self.status})>"


class StudentProgress(Base):
    __tablename__ = "student_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    resource_id = Column(String(36), ForeignKey("resources.id"), nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    progress_percentage = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    student = relationship("User")
    course = relationship("Course")
    resource = relationship("Resource")

    def __repr__(self) -> str:
        return f"<StudentProgress student={self.student_id} course={self.course_id} {self.progress_percentage}%>"
