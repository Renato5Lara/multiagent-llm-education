"""P2 — persistencia del resultado experimental. Capa fina y aislada:
solo el runner (`backend/scripts/experimento_cmg_runner.py`) la usa —
ningún endpoint HTTP del producto la referencia (§21/§17)."""

from __future__ import annotations

from typing import Literal

from sqlalchemy.orm import Session

from app.models.experiment_cmg_result import ExperimentCMGResult
from app.services.cmg_evaluation_service import EvaluacionCMG
from app.services.cmg_generation_service import CMG, GenerationConfig

Condition = Literal["experimental", "control"]
#: R28/R29 — vocabulario controlado del metadato de trazabilidad de
#: oleada (espejo de `ck_ecr_run_label` en la migración `928a10b002db`).
RunLabel = Literal["pilot_1", "corrida_2"]
RUN_LABELS_VALIDOS = frozenset({"pilot_1", "corrida_2"})


def persistir_resultado(
    db: Session,
    *,
    condition: Condition,
    configuration_source: str,
    configuration: GenerationConfig,
    cmg: CMG,
    evaluacion: EvaluacionCMG,
    traceability: dict,
    run_label: RunLabel,
) -> ExperimentCMGResult:
    if run_label not in RUN_LABELS_VALIDOS:
        raise ValueError(f"run_label inválido: {run_label!r} — valores permitidos: {sorted(RUN_LABELS_VALIDOS)}")

    fila = ExperimentCMGResult(
        concept_id=cmg.concept_id,
        learning_objective_id=cmg.learning_objective_id,
        condition=condition,
        configuration_source=configuration_source,
        configuration={"modalidad": configuration.modalidad, "profundidad": configuration.profundidad},
        cmg=cmg.to_dict(),
        d1=evaluacion.d1.to_dict(),
        d2=evaluacion.d2.to_dict(),
        d3=evaluacion.d3.to_dict(),
        execution_valid=evaluacion.d2.execution_valid,
        traceability=traceability,
        run_label=run_label,
    )
    db.add(fila)
    db.flush()
    return fila
