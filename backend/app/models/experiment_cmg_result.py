"""Modelo de persistencia experimental — P2 del experimento CMG.

Una fila por (Concept × condición). No pertenece al dominio educativo
del producto (nunca se lee desde el flujo real del estudiante); vive
como tabla aditiva, aislada, exclusivamente para el runner experimental
(`backend/scripts/experimento_cmg_runner.py`).

No almacena información personal del estudiante (§17): la evidencia
sintética que activó la Rama A NO es información de un estudiante real
— es metadata experimental (`traceability`), nunca parte del CMG.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.base import Base


class ExperimentCMGResult(Base):
    __tablename__ = "experiment_cmg_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    concept_id = Column(String(36), ForeignKey("concepts.id"), nullable=False, index=True)
    learning_objective_id = Column(
        String(36), ForeignKey("learning_objectives.id"), nullable=False, index=True
    )

    #: "experimental" | "control" — §18/§19.
    condition = Column(String(20), nullable=False, index=True)
    #: "multiagent_runtime" | "fixed_control" — de dónde vino la configuración.
    configuration_source = Column(String(30), nullable=False)
    #: {"modalidad": ..., "profundidad": ...} — GenerationConfig.to_dict-like.
    configuration = Column(JSON, nullable=False)

    #: El CMG completo (CMG.to_dict()) — explicación, código, ejercicio, diagrama.
    cmg = Column(JSON, nullable=False)

    #: D1Resultado.to_dict(), D2Resultado.to_dict(), D3Resultado.to_dict().
    d1 = Column(JSON, nullable=False)
    d2 = Column(JSON, nullable=False)
    d3 = Column(JSON, nullable=False)
    execution_valid = Column(Boolean, nullable=False)

    #: Metadata experimental — NUNCA contenido educativo (§18). Para
    #: "experimental": {dominada, urgente, margen, regla_aplicada, ...}
    #: (la traza de `determinar_configuracion_experimental`). Para
    #: "control": {} — no se ejecuta Diagnosticar/Remediar/Orientar (§19).
    traceability = Column(JSON, nullable=False, default=dict)

    #: R28/R29 — trazabilidad de la oleada de recolección: "pilot_1" |
    #: "corrida_2". Metadato de trazabilidad, no un factor experimental:
    #: nunca entra a `configuration`, `cmg`, `d1`, `d2`, `d3` ni al
    #: evaluador/generador. Sin default en el ORM a propósito — debe
    #: pasarse explícito en cada inserción (R29 Parte 6).
    run_label = Column(String(20), nullable=False)

    generated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    evaluated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    concept = relationship("Concept")
    learning_objective = relationship("LearningObjective")

    def __repr__(self) -> str:
        return f"<ExperimentCMGResult concept={self.concept_id} condition={self.condition}>"
