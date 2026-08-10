"""
Reconciliación legacy -> runtime (P0).

Contexto (memoria del proyecto, no repetir la investigación aquí):
  - auditoria_integridad_datos_pedagogicos_2026_08_09.md (hallazgo P0)
  - gate_p0_legacy_runtime_bridge_2026_08_09.md (alcance real, 2 call sites)
  - diseno_reconciliacion_p0_legacy_runtime_2026_08_09.md (diseño aprobado)

El registro de evidencia en el runtime (student_service.py,
knowledge_test_service.py) es best-effort: si falla, el submit del
estudiante NO se bloquea, pero la escritura queda marcada como
`failed` en `idempotency_keys` (event_type=runtime_evidencia_registrada),
con un snapshot minimo del payload en `response_body`
(items_incorrectos/items_totales/modalidad_estudiante -- nunca el
prompt/respuesta del LLM ni el estado completo del estudiante).

Este script:
  1. Busca keys `failed` de ese event_type, parsea la key para
     recuperar student_id/course_id/topic (o objetivo_id) y usa el
     snapshot para reintentar exactamente la misma escritura runtime.
  2. Reporta (sin poder reintentar, por diseño) las keys `in_progress`
     mas viejas que su `expires_at` -- probablemente huerfanas por un
     crash entre `acquire()` y `complete()/fail()`; no tienen snapshot
     porque nunca llegaron a fallar formalmente. Se dejan para
     `purge_expired()`/revision manual, no se tocan a ciegas.

Modo por defecto: DRY RUN. Solo reporta que intentaria reconciliar.
Nada se escribe en el runtime hasta pasar --apply explicitamente.

Uso (desde backend/, con el venv activado):
    python scripts/reconciliar_legacy_runtime.py                # dry run + reporte
    python scripts/reconciliar_legacy_runtime.py --apply         # reintenta de verdad
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

logger = logging.getLogger(__name__)

from app.data.knowledge_test_bank import COMPETENCY_LABELS  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.events.idempotency import IdempotencyConflict, idempotency_service  # noqa: E402
from app.models.idempotency_key import IdempotencyKey  # noqa: E402
from app.models.learning_objective import LearningObjective  # noqa: E402
from app.services import runtime_bridge  # noqa: E402

# Referenciado vía módulo (no `from ... import registrar_evidencia_evaluacion`)
# a propósito: un import directo del nombre se resuelve una sola vez al
# importar este script, y un monkeypatch posterior sobre
# `runtime_bridge.registrar_evidencia_evaluacion` (como hacen los tests de
# reconciliación) no lo alcanzaría.

EVENT_TYPE = "runtime_evidencia_registrada"


def _parse_key(key: str) -> dict | None:
    """Las 3 formas que construyen student_service.py/
    knowledge_test_service.py -- ver
    diseno_reconciliacion_p0_legacy_runtime_2026_08_09.md. Prefijos
    distintos por origen (no una sola forma ambigua) a propósito: sin
    esto, un `attempt_id` (UUID) y un `version` (int) comparten la
    misma posición en la key y no se podrían distinguir de forma
    confiable."""
    partes = key.split(":")
    if len(partes) != 5:
        return None
    tipo = partes[0]
    if tipo == "runtime-evidencia-vark":
        _, student_id, course_id, version, topic = partes
        return {
            "tipo": tipo,
            "student_id": student_id,
            "course_id": course_id,
            "version": version,
            "topic": topic,
        }
    if tipo == "runtime-evidencia-pretest":
        _, student_id, course_id, attempt_id, topic = partes
        return {
            "tipo": tipo,
            "student_id": student_id,
            "course_id": course_id,
            "attempt_id": attempt_id,
            "topic": topic,
        }
    if tipo == "runtime-evidencia-pretest-objetivo":
        _, student_id, course_id, attempt_id, objetivo_id = partes
        return {
            "tipo": tipo,
            "student_id": student_id,
            "course_id": course_id,
            "attempt_id": attempt_id,
            "objetivo_id": objetivo_id,
        }
    return None


def _titulo_modulo(db, info: dict, snapshot: dict) -> str | None:
    if info["tipo"] == "runtime-evidencia-pretest-objetivo":
        if "objetivo_titulo" in snapshot:
            return snapshot["objetivo_titulo"]
        # Snapshot sin objetivo_titulo (key de antes de este fix, o
        # snapshot corrupto): fallback a consultar el estado ACTUAL de
        # LearningObjective -- puede diferir del vigente al momento del
        # fallo original si el objetivo fue editado/eliminado desde
        # entonces (ver cierre_p0_legacy_runtime_2026_08_09 punto 3).
        logger.warning(
            "Snapshot sin objetivo_titulo para key con objetivo_id=%s -- "
            "reconstruyendo desde el estado ACTUAL de LearningObjective, "
            "que puede haber cambiado desde el fallo original.",
            info["objetivo_id"],
        )
        objetivo = (
            db.query(LearningObjective)
            .filter(LearningObjective.id == info["objetivo_id"])
            .first()
        )
        return objetivo.title if objetivo else None
    if info["tipo"] == "runtime-evidencia-pretest":
        return COMPETENCY_LABELS.get(info["topic"], info["topic"])
    return info["topic"]  # vark: el topic YA es el título usado en el registro original


def _objetivos(db, info: dict, snapshot: dict) -> tuple:
    """Preferir el snapshot (título/orden tal como estaban al momento
    del fallo) sobre re-derivar de `LearningObjective` -- la regla de
    derivación asume que la tabla legacy es estable, pero "estable" no
    es lo mismo que "inmutable": un objetivo puede editarse o
    eliminarse entre el fallo original y la reconciliación (hallazgo de
    la auditoría de implementación, punto 3)."""
    if info["tipo"] != "runtime-evidencia-pretest-objetivo":
        return ()
    if "objetivo_titulo" in snapshot:
        return runtime_bridge.construir_objetivos(
            [(info["objetivo_id"], snapshot["objetivo_titulo"], snapshot.get("objetivo_order", 0))]
        )
    objetivo = (
        db.query(LearningObjective).filter(LearningObjective.id == info["objetivo_id"]).first()
    )
    if objetivo is None:
        return ()
    return runtime_bridge.construir_objetivos(
        [(objetivo.id, objetivo.title, objetivo.order or 0)]
    )


def reconciliar(db, *, apply: bool) -> dict:
    reporte: dict[str, list[str]] = {
        "reintentables": [],
        "convergidos": [],
        "fallidos_de_nuevo": [],
        "fallos_permanentes_no_reintentados": [],
        "ya_en_proceso_por_otra_ejecucion": [],
        "no_parseables": [],
        "sin_snapshot": [],
        "in_progress_huerfanos": [],
    }

    fallidas = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.event_type == EVENT_TYPE, IdempotencyKey.status == "failed")
        .all()
    )

    for k in fallidas:
        info = _parse_key(k.key)
        if info is None:
            reporte["no_parseables"].append(k.key)
            continue

        try:
            snapshot = json.loads(k.response_body) if k.response_body else None
        except (TypeError, ValueError):
            snapshot = None
        if not snapshot or "items_incorrectos" not in snapshot:
            reporte["sin_snapshot"].append(k.key)
            continue

        # E-1 (dominio, permanente) vs E-3 (infraestructura, transitorio)
        # -- mismo criterio de runtime_bridge.clasificar_fallo_reconciliable,
        # ya aplicado al fallar por primera vez. Ausente (snapshot de
        # antes de este fix): se trata como reintentable, no se ignora
        # en silencio.
        if snapshot.get("clasificacion") == "E-1":
            reporte["fallos_permanentes_no_reintentados"].append(k.key)
            continue

        reporte["reintentables"].append(k.key)
        if not apply:
            continue

        try:
            record = idempotency_service.acquire(
                db,
                k.key,
                event_type=EVENT_TYPE,
                aggregate_id=f"{info['student_id']}:{info['course_id']}",
            )
        except IdempotencyConflict:
            reporte["ya_en_proceso_por_otra_ejecucion"].append(k.key)
            continue

        if record.status == "completed":
            # Convergió por otra vía entre el query y el acquire.
            reporte["convergidos"].append(k.key)
            continue

        titulo_modulo = _titulo_modulo(db, info, snapshot)
        objetivos = _objetivos(db, info, snapshot)
        try:
            runtime_bridge.registrar_evidencia_evaluacion(
                student_id=info["student_id"],
                course_id=info["course_id"],
                titulo_modulo=titulo_modulo,
                items_incorrectos=snapshot["items_incorrectos"],
                items_totales=snapshot["items_totales"],
                modalidad_estudiante=snapshot.get("modalidad_estudiante"),
                objetivos=objetivos,
            )
        except Exception as exc:  # noqa: BLE001
            # Re-clasificar: el fallo de ESTE intento puede ser distinto
            # en naturaleza al que originó la key (p.ej. el original fue
            # un timeout transitorio ya resuelto, pero ahora el dato
            # mismo resulta inválido). El snapshot se actualiza con la
            # clasificación más reciente, no se mezcla con la vieja.
            snapshot["clasificacion"] = runtime_bridge.clasificar_fallo_reconciliable(exc)
            idempotency_service.fail(db, k.key, reason=json.dumps(snapshot))
            reporte["fallidos_de_nuevo"].append(k.key)
        else:
            idempotency_service.complete(db, k.key)
            reporte["convergidos"].append(k.key)

    huerfanas = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.event_type == EVENT_TYPE, IdempotencyKey.status == "in_progress")
        .all()
    )
    reporte["in_progress_huerfanos"] = [k.key for k in huerfanas]

    return reporte


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Reintenta de verdad. Sin este flag, solo reporta (dry run).",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        reporte = reconciliar(db, apply=args.apply)
    finally:
        db.close()

    print(json.dumps({"apply": args.apply, **reporte}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
