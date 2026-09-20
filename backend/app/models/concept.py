"""
Modelo de Concepto curricular.
Unidad curricular propia de los 32 conceptos de Fundamentos de la
Programación, independiente de `ProgrammingConcept` (2C-3.2/2C-3.10,
Deliberacion - Cruce Auditoria 01 x Auditoria 02.md). Pertenece a un
único LearningObjective/Módulo de introducción.
"""

import uuid

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Concept(Base):
    __tablename__ = "concepts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=False)
    learning_objective_id = Column(
        String(36), ForeignKey("learning_objectives.id"), nullable=False
    )
    order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint(
            "learning_objective_id", "order", name="uq_concepts_objective_order"
        ),
    )

    learning_objective = relationship("LearningObjective", back_populates="concepts")

    def __repr__(self) -> str:
        return f"<Concept {self.title}>"
