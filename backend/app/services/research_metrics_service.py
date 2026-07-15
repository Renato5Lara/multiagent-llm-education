"""
Registro de métricas de investigación (Research & Experiment Layer).

Event-log genérico sobre research_metrics: cada interacción relevante del
flujo real del estudiante deja evidencia consultable por el dashboard del
investigador. SIEMPRE best-effort: una métrica jamás rompe el flujo que la
origina (patrón active_mission_service).

No duplica lo ya persistido en otras tablas: hora de login (login_attempts),
inicio/fin/duración de pre/post-test (knowledge_test_attempts), recursos
vistos y tiempo de estudio (engagement_*).
"""

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# metric_type canónicos
PATH_GENERATION_MS = "path_generation_ms"
AI_ORCHESTRATION_MS = "ai_orchestration_ms"
TUTOR_MESSAGE = "tutor_message"
TUTOR_LATENCY_MS = "tutor_latency_ms"
MISSION_COMPLETED = "mission_completed"
MODULE_PROGRESS = "module_progress"
PRETEST_COMPLETED = "pretest_completed"
POSTTEST_COMPLETED = "posttest_completed"
CYCLE_EVIDENCE = "cycle_evidence"


def record_metric(
    db: Session,
    *,
    metric_type: str,
    student_id: str | None = None,
    course_id: str | None = None,
    value: float | None = None,
    unit: str | None = None,
    payload: dict | None = None,
) -> None:
    """Inserta una métrica de investigación. Nunca propaga excepciones."""
    try:
        from app.models.research import ResearchMetric

        db.add(
            ResearchMetric(
                student_id=student_id,
                course_id=course_id,
                metric_type=metric_type,
                value=value,
                unit=unit,
                payload=payload,
            )
        )
        db.commit()
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        logger.warning("Métrica %s no registrada", metric_type, exc_info=True)
