"""
Tabla intermedia M:M entre Resource y LearningObjective.
Incluye un score de relevancia.
"""

from sqlalchemy import Column, Float, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ResourceObjective(Base):
    __tablename__ = "resource_objectives"

    resource_id = Column(
        String(36), ForeignKey("resources.id"), primary_key=True
    )
    objective_id = Column(
        String(36), ForeignKey("learning_objectives.id"), primary_key=True
    )
    relevance_score = Column(Float, default=1.0, nullable=False)

    # Relaciones
    resource = relationship("Resource", back_populates="objective_associations")
    objective = relationship(
        "LearningObjective", back_populates="resource_associations"
    )
