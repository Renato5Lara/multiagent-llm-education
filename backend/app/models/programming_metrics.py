"""
Modelo de métricas especializadas para cursos de programación.
Mide 12 dimensiones: calidad pseudocódigo, eficiencia depuración,
velocidad lectura código, 4 dimensiones de CT, 3 tasas de error,
progresión de etapa, tasa de dominio conceptual.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, String

from app.db.base import Base


class ProgrammingMetrics(Base):
    """Métricas de programación por estudiante-curso."""
    __tablename__ = "programming_metrics"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    student_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False, index=True)

    pseudocode_quality = Column(Float, default=0.0, nullable=False)
    debugging_efficiency = Column(Float, default=0.0, nullable=False)
    code_reading_speed = Column(Float, default=0.0, nullable=False)

    ct_decomposition = Column(Float, default=0.0, nullable=False)
    ct_pattern_recognition = Column(Float, default=0.0, nullable=False)
    ct_abstraction = Column(Float, default=0.0, nullable=False)
    ct_algorithm_design = Column(Float, default=0.0, nullable=False)

    syntax_error_rate = Column(Float, default=0.0, nullable=False)
    logic_error_rate = Column(Float, default=0.0, nullable=False)
    semantic_error_rate = Column(Float, default=0.0, nullable=False)

    stage_progression = Column(Float, default=0.0, nullable=False)
    concept_mastery_rate = Column(Float, default=0.0, nullable=False)

    concept_scores = Column(JSON, nullable=True)
    error_history = Column(JSON, nullable=True)
    calculated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
