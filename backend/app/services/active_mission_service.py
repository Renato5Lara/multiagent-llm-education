"""Misión Activa — continuidad de la misión del estudiante (SPEC_MISION_ACTIVA.md).

La misión activa es la unidad indivisible {adaptación, posición, evidencia}:
- adaptación: snapshot del contenido orquestado, tal como se mostró
- posición:   cursor del recorrido (paso actual, pasos completados, XP)
- evidencia:  session_id de la deliberación (las trazas ya persisten en DB)

Dueño del estado: `LearningSession` refundada — de "visita cronometrada" a
"proceso de misión que sobrevive a múltiples visitas". El snapshot y el cursor
viven juntos en `metadata_json` y se invalidan juntos (invariante del contrato).

Regla madre: releer es el comportamiento por defecto; navegar NUNCA regenera.
Un snapshot degradado no se persiste (regla de regeneración: no congelar una
experiencia degradada como "la" experiencia del estudiante).

Toda la persistencia aquí es best-effort: si la tabla no existe todavía
(migración sin aplicar), la misión sigue funcionando como antes (regenera),
jamás rompe el flujo del estudiante.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.learning_session import LearningSession
from app.models.user import User

logger = logging.getLogger(__name__)

SNAPSHOT_KEY = "orchestration_snapshot"
CURSOR_KEY = "mission_cursor"

# Claves de anotación que el endpoint añade a la respuesta y que NUNCA deben
# guardarse dentro del snapshot (evita snapshots anidados en re-lecturas).
_ANNOTATION_KEYS = ("resumed", "mission_cursor")


def _default_cursor() -> dict[str, Any]:
    return {"current_index": 0, "completed_step_ids": [], "total_xp": 0}


def get_mission(db: Session, student: User, module_id: str) -> LearningSession | None:
    """Última sesión de misión del estudiante para este módulo (cualquier estado:
    una misión COMPLETADA también se relee — "Repasar" es lectura, no reapertura)."""
    try:
        return (
            db.query(LearningSession)
            .filter(
                LearningSession.student_id == student.id,
                LearningSession.module_id == module_id,
            )
            .order_by(LearningSession.started_at.desc())
            .first()
        )
    except SQLAlchemyError:
        # Tabla ausente (migración sin aplicar) u otro fallo de lectura: la
        # transacción queda envenenada en PostgreSQL — limpiar y degradar.
        db.rollback()
        logger.warning("active_mission: lectura de learning_sessions falló; se degrada a regenerar", exc_info=True)
        return None


def get_resumable(db: Session, student: User, module_id: str) -> LearningSession | None:
    mission = get_mission(db, student, module_id)
    if mission is not None and (mission.metadata_json or {}).get(SNAPSHOT_KEY):
        return mission
    return None


def save_snapshot(
    db: Session,
    student: User,
    course_id: str,
    module_id: str,
    snapshot: dict[str, Any],
) -> LearningSession | None:
    """Persiste la adaptación generada. Idempotente: reutiliza la misión existente."""
    clean = {k: v for k, v in snapshot.items() if k not in _ANNOTATION_KEYS}
    try:
        mission = get_mission(db, student, module_id)
        if mission is None:
            mission = LearningSession(
                student_id=student.id,
                course_id=course_id,
                module_id=module_id,
                status="active",
                context_key=f"ctx:{student.id}:{course_id}",
                swarm_activated="completed",
            )
            db.add(mission)
        metadata = dict(mission.metadata_json or {})
        metadata[SNAPSHOT_KEY] = clean
        metadata.setdefault(CURSOR_KEY, _default_cursor())
        mission.metadata_json = metadata
        db.commit()
        return mission
    except SQLAlchemyError:
        db.rollback()
        logger.warning("active_mission: no se pudo persistir el snapshot (best-effort)", exc_info=True)
        return None


def update_cursor(
    db: Session,
    student: User,
    module_id: str,
    current_index: int,
    completed_step_ids: list[str],
    total_xp: int,
) -> LearningSession | None:
    try:
        mission = get_mission(db, student, module_id)
        if mission is None:
            return None
        metadata = dict(mission.metadata_json or {})
        metadata[CURSOR_KEY] = {
            "current_index": max(0, current_index),
            "completed_step_ids": completed_step_ids,
            "total_xp": max(0, total_xp),
        }
        mission.metadata_json = metadata
        db.commit()
        return mission
    except SQLAlchemyError:
        db.rollback()
        logger.warning("active_mission: no se pudo actualizar el cursor (best-effort)", exc_info=True)
        return None


def complete_mission(db: Session, student: User, module_id: str) -> None:
    """COMPLETADA = recorrido confirmado (unidireccional). El snapshot se
    conserva: "Repasar" relee la experiencia vivida."""
    try:
        mission = get_mission(db, student, module_id)
        if mission is not None and mission.status == "active":
            mission.end()
            db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.warning("active_mission: no se pudo cerrar la misión (best-effort)", exc_info=True)


def record_completed_session(
    db: Session,
    student: User,
    course_id: str | None,
    module_id: str,
    duration_minutes: float | None,
) -> None:
    """Fase de cierre del producto (jul 2026): el flujo continuo de ciclos
    (ModuleExperienceView) nunca llama `save_snapshot`, así que
    `get_mission()` siempre devuelve None para esas misiones y
    `complete_mission()` no tenía ningún LearningSession que cerrar —
    "¿se registra el tiempo?" respondía NO para el 100% del flujo real.
    Cuando no existe una misión (best-effort igual que el resto de este
    módulo), se crea una ya cerrada con la duración real que el cliente
    midió — nunca se inventa un tiempo, se usa el que el estudiante vivió."""
    if duration_minutes is None or duration_minutes <= 0 or not course_id:
        return
    try:
        mission = get_mission(db, student, module_id)
        if mission is not None:
            return  # ya cubierto por complete_mission (flujo con snapshot)
        now = datetime.now(timezone.utc)
        started = now - timedelta(minutes=duration_minutes)
        db.add(LearningSession(
            student_id=student.id,
            course_id=course_id,
            module_id=module_id,
            status="completed",
            started_at=started,
            ended_at=now,
            duration_minutes=round(duration_minutes, 2),
            context_key=f"ctx:{student.id}:{course_id}",
        ))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.warning("active_mission: no se pudo registrar la duración real (best-effort)", exc_info=True)


def annotate(result: dict[str, Any], mission: LearningSession | None, resumed: bool) -> dict[str, Any]:
    """Añade a la respuesta del endpoint la posición persistida y si fue relectura."""
    result["resumed"] = resumed
    cursor = None
    if mission is not None:
        cursor = (mission.metadata_json or {}).get(CURSOR_KEY)
    result["mission_cursor"] = cursor or _default_cursor()
    return result
