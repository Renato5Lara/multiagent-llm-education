"""Exportador de SOLO LECTURA de la Traza (RFC-0007 §2.1) hacia LangSmith,
para visualización operativa durante la demo/sustentación.

No es una segunda tubería de telemetría: consume exactamente la misma
superficie que ya usan el endpoint HTTP (`GET /api/runtime/sessions/{id}/
traza`) y Modo Evidencia v2 — `consultar_traza` + `traza_a_pasos_dict`,
ambos ya existentes. No reconstruye nada, no calcula nada que la Traza no
tenga ya. La fuente de evidencia de la tesis sigue siendo esa misma Traza,
consultable directamente por HTTP; esto solo la re-proyecta a un formato
visual, en un proyecto de LangSmith separado.

Nota sobre tiempos: los `start_time`/`end_time` que se envían a LangSmith
son el momento de la EXPORTACIÓN (ahora), no un dato persistido — RFC-0007
excluye deliberadamente el reloj de pared del registro científico (A3/A4),
así que no existe una marca de tiempo real por transición que exportar.
Esto es exactamente el uso que la alternativa 2 del RFC admite: telemetría
operativa, nunca evidencia.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.telemetry.config import HABILITADO, PROYECTO


def exportar_sesion(session_id: str) -> None:
    """Proyecta la traza persistida de una sesión a LangSmith.

    No-op si la telemetría está deshabilitada, si la sesión todavía no
    tiene transiciones, o si cualquier paso falla — nunca debe afectar al
    llamador (el mismo contrato que `spans_operativos.registrar_llamada_llm`)."""
    if not HABILITADO:
        return
    try:
        _exportar_sesion_impl(session_id)
    except Exception:
        pass


def _exportar_sesion_impl(session_id: str) -> None:
    from langsmith import Client

    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )
    from app.services.runtime_trace_serialization import traza_a_pasos_dict
    from runtime.boundary import PeticionAbrirSesion, consultar_traza

    almacen, almacen_memoria = almacenes()
    identidad = almacen.identidad_existente(session_id)
    if identidad is None:
        return  # sesión sin transiciones aún — nada que exportar

    peticion = PeticionAbrirSesion(
        session_id=session_id,
        student_id=identidad.student_id,
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )
    traza = consultar_traza(peticion, almacen, almacen_memoria)
    if not traza:
        return

    pasos = traza_a_pasos_dict(traza)
    ahora = datetime.now(timezone.utc)

    cliente = Client()
    raiz_id = uuid.uuid4()
    cliente.create_run(
        id=raiz_id,
        name=f"sesion:{session_id}",
        run_type="chain",
        inputs={"session_id": session_id, "student_id": identidad.student_id},
        outputs={"total_transiciones": len(pasos)},
        start_time=ahora,
        end_time=ahora,
        project_name=PROYECTO,
    )
    for paso in pasos:
        tipos = sorted({evento["tipo"] for evento in paso["eventos"]})
        nombre = ", ".join(tipos) or "sin-eventos"
        cliente.create_run(
            id=uuid.uuid4(),
            name=f"transicion-{paso['transicion']}: {nombre}",
            run_type="chain",
            parent_run_id=raiz_id,
            inputs={"transicion": paso["transicion"]},
            outputs={"eventos": paso["eventos"]},
            start_time=ahora,
            end_time=ahora,
            project_name=PROYECTO,
        )
