"""Primera capacidad de "Plataforma Operativa 2 — Inteligencia Docente":
agrega las decisiones que el Runtime ya tomó para los estudiantes de un
curso (vía `runtime_bridge.consultar_decision_vigente`, S3) en una
sugerencia de prioridad semanal para el docente.

No decide el plan — el docente conserva la autoridad (RFC-0009: "el
docente ejerce autoridad EXTERNA"; el Boundary traduce, jamás decide,
RFC-0010 regla 1). Esto es una SUGERENCIA de solo lectura; el docente
sigue creando el plan con `WeeklyPedagogicalPlanCreate` como hasta
ahora, con o sin usarla.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.enrollment import Enrollment, EnrollmentStatus
from app.services.runtime_bridge import consultar_decision_vigente

_ASUNTO_RE = re.compile(r"^modalidad\((.+)\)$")


def _competencia_desde_asunto(asunto: str) -> str:
    """Deshace el envoltorio que Adaptar siempre produce
    (`f"modalidad({competencia})"`, `runtime/domain/adaptar/productor.py`)
    para mostrarle al docente el nombre del asunto, no el envoltorio."""
    m = _ASUNTO_RE.match(asunto)
    return m.group(1) if m else asunto


@dataclass(frozen=True, slots=True)
class PrioridadAsunto:
    competencia: str
    estudiantes_reforzar: int
    estudiantes_avanzar: int


@dataclass(frozen=True, slots=True)
class SugerenciaSemanal:
    estudiantes_totales: int
    estudiantes_con_evidencia: int
    prioridades: tuple[PrioridadAsunto, ...]
    competencia_sugerida: str | None
    bloom_target_sugerido: int | None


def sugerir_prioridad_semanal(db: Session, course_id: str) -> SugerenciaSemanal:
    student_ids = [
        row[0]
        for row in db.query(Enrollment.student_id)
        .filter(
            Enrollment.course_id == course_id,
            Enrollment.status == EnrollmentStatus.ACTIVO,
        )
        .distinct()
        .all()
    ]

    conteo: dict[str, dict[str, int]] = {}
    con_evidencia = 0
    for student_id in student_ids:
        entrega = consultar_decision_vigente(student_id=student_id, course_id=course_id)
        if entrega.diseno is None or entrega.asunto is None:
            continue
        con_evidencia += 1
        competencia = _competencia_desde_asunto(entrega.asunto)
        bucket = conteo.setdefault(competencia, {"reforzar": 0, "avanzar": 0})
        if entrega.diseno.get("profundidad") == "fundamentos":
            bucket["reforzar"] += 1
        else:
            bucket["avanzar"] += 1

    prioridades = tuple(
        sorted(
            (
                PrioridadAsunto(
                    competencia=competencia,
                    estudiantes_reforzar=b["reforzar"],
                    estudiantes_avanzar=b["avanzar"],
                )
                for competencia, b in conteo.items()
            ),
            key=lambda p: p.estudiantes_reforzar,
            reverse=True,
        )
    )

    top = prioridades[0] if prioridades else None
    competencia_sugerida = top.competencia if top and top.estudiantes_reforzar > 0 else None
    bloom_target_sugerido = 2 if competencia_sugerida else None

    return SugerenciaSemanal(
        estudiantes_totales=len(student_ids),
        estudiantes_con_evidencia=con_evidencia,
        prioridades=prioridades,
        competencia_sugerida=competencia_sugerida,
        bloom_target_sugerido=bloom_target_sugerido,
    )
