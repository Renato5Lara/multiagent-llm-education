"""
Modelo de etiquetado de recursos con conceptos de programación.
Permite asociar cada recurso educativo a conceptos específicos
con nivel de dificultad, lenguaje y tipo de ejercicio.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String

from app.db.base import Base
from app.models.programming_domain import ProgrammingConcept


class ResourceProgrammingTag(Base):
    """Etiqueta de concepto de programación para un recurso educativo."""
    __tablename__ = "resource_programming_tags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resource_id = Column(String(36), ForeignKey("resources.id"), nullable=False, index=True)
    concept = Column(
        Enum(ProgrammingConcept, name="programmingconcept", use_enum_values=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    bloom_level = Column(Integer, nullable=False, default=1)
    difficulty = Column(Float, nullable=False, default=0.5)
    language = Column(String(50), nullable=True)
    is_exercise = Column(Integer, nullable=False, default=0)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
