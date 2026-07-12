"""Traduce evidencia de evaluación del estudiante hacia el Platform
Boundary del runtime (RFC-0010, ADR-0010) — el primer punto donde una
decisión pedagógica real del runtime LangGraph llega al flujo del
estudiante (Épica 2).

No decide nada: abre/reanuda la sesión (E1) y registra el hecho (E2),
dejando que el runtime delibere y adapte. Devuelve la `Entrega` (S1)
tal cual — quien la consuma decide qué hacer con ella (regla 1 de
RFC-0010: traducción, jamás interpretación). La generación de contenido
(Tavily/LLM) sigue siendo responsabilidad de `module_orchestration_
service.py`; este puente solo le entrega la decisión del runtime.
"""

from __future__ import annotations

from app.services.runtime_connection import (
    SPEC_VERSION,
    VERSION_BANCO,
    VERSION_POLITICA,
    almacenes,
)
from runtime.boundary import (
    Entrega,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    normalizar_asunto,
    registrar_hecho,
)
from runtime.kernel.state.entries import OrigenProvenance


def _sesion_del_curso(student_id: str, course_id: str) -> str:
    """`session_id` determinista por estudiante+curso — RFC-0010 no fija
    ningún esquema; siempre reconstruible igual (regla de derivación),
    sin tabla adicional que mantener sincronizada."""
    return f"curso:{course_id}:estudiante:{student_id}"


def registrar_evidencia_evaluacion(
    student_id: str,
    course_id: str,
    titulo_modulo: str,
    items_incorrectos: list[int],
) -> Entrega:
    """El primer hecho real del flujo del estudiante que entra por el
    Boundary. `titulo_modulo` se traduce a `competencia` vía ADR-0010
    (`normalizar_asunto` — nunca un valor de COMP-0..5)."""
    almacen, almacen_memoria = almacenes()
    identidad = abrir_sesion(
        PeticionAbrirSesion(
            session_id=_sesion_del_curso(student_id, course_id),
            student_id=student_id,
            version_banco=VERSION_BANCO,
            version_politica=VERSION_POLITICA,
            spec_version=SPEC_VERSION,
        ),
        almacen,
        almacen_memoria,
    )
    return registrar_hecho(
        PeticionHechoDelMundo(
            identidad=identidad,
            contenido={
                "competencia": normalizar_asunto(titulo_modulo),
                "items_incorrectos": items_incorrectos,
            },
            origen=OrigenProvenance.INSTRUMENTO,
        ),
        almacen,
        almacen_memoria,
    )
