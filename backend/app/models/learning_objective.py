"""
Modelo de Objetivo de Aprendizaje.
Cada curso tiene objetivos con nivel de Bloom (1-6).
"""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class LearningObjective(Base):
    __tablename__ = "learning_objectives"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    course_id = Column(String(36), ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    bloom_level = Column(Integer, nullable=False)  # 1-6
    order = Column(Integer, nullable=False, default=0)

    # Relaciones
    course = relationship("Course", back_populates="objectives")
    resource_associations = relationship(
        "ResourceObjective", back_populates="objective", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<LearningObjective {self.title} (Bloom: {self.bloom_level})>"
