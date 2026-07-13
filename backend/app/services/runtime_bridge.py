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

from typing import Any

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
    consultar_entrega_vigente,
    consultar_estado,
    consultar_memoria,
    normalizar_asunto,
    registrar_hecho,
)
from runtime.kernel.state.entries import Capacidad, OrigenProvenance


def _sesion_del_curso(student_id: str, course_id: str) -> str:
    """`session_id` determinista por estudiante+curso — RFC-0010 no fija
    ningún esquema; siempre reconstruible igual (regla de derivación),
    sin tabla adicional que mantener sincronizada."""
    return f"curso:{course_id}:estudiante:{student_id}"


def _peticion(student_id: str, course_id: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=_sesion_del_curso(student_id, course_id),
        student_id=student_id,
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )


def registrar_evidencia_evaluacion(
    student_id: str,
    course_id: str,
    titulo_modulo: str,
    items_incorrectos: list[int],
    items_totales: int | None = None,
) -> Entrega:
    """El primer hecho real del flujo del estudiante que entra por el
    Boundary. `titulo_modulo` se traduce a `competencia` vía ADR-0010
    (`normalizar_asunto` — nunca un valor de COMP-0..5).

    `items_totales` activa la señal de sesión de Tutorizar (RFC-0002
    R4: fluidez/confusión/frustración) — su productor exige el total
    para clasificar; sin él la evidencia sigue siendo válida pero la
    señal conductual no se produce."""
    almacen, almacen_memoria = almacenes()
    identidad = abrir_sesion(_peticion(student_id, course_id), almacen, almacen_memoria)
    contenido: dict[str, Any] = {
        "competencia": normalizar_asunto(titulo_modulo),
        "items_incorrectos": items_incorrectos,
    }
    if items_totales is not None:
        contenido["items_totales"] = items_totales
    return registrar_hecho(
        PeticionHechoDelMundo(
            identidad=identidad,
            contenido=contenido,
            origen=OrigenProvenance.INSTRUMENTO,
        ),
        almacen,
        almacen_memoria,
    )


def consultar_decision_vigente(student_id: str, course_id: str) -> Entrega:
    """S3 — la decisión que el runtime ya tomó para este estudiante en
    este curso, sin registrar ningún hecho nuevo (regla 2 de RFC-0010).
    `Entrega(asunto=None, diseno=None)` si todavía no hay evidencia
    (estudiante nuevo, o sin evaluaciones enviadas aún) — un estado
    válido, no un error; quien la consuma decide el comportamiento por
    defecto en ese caso."""
    almacen, almacen_memoria = almacenes()
    return consultar_entrega_vigente(
        _peticion(student_id, course_id), almacen, almacen_memoria
    )


def contexto_pedagogico_tutor(student_id: str, course_id: str) -> dict[str, Any]:
    """S3, solo lectura — el contexto pedagógico que el Runtime ya
    decidió para este estudiante: la adaptación vigente (S1), las
    señales conductuales de Tutorizar detectadas en la sesión (RFC-0002
    R4) y la memoria consolidada del estudiante (RFC-0005). El tutor de
    la plataforma redacta con este contexto; jamás decide adaptación por
    su cuenta — RFC-0002: ninguna capacidad del runtime "redacta
    mensajes al estudiante", y a partir de este puente ningún tutor de
    la plataforma decide pedagogía por fuera del runtime. Nunca registra
    nada (regla 2 de RFC-0010)."""
    almacen, almacen_memoria = almacenes()
    peticion = _peticion(student_id, course_id)
    entrega = consultar_entrega_vigente(peticion, almacen, almacen_memoria)
    estado = consultar_estado(peticion, almacen, almacen_memoria)
    memoria = consultar_memoria(peticion, almacen, almacen_memoria)
    senales = [
        str(f.contenido["senal"])
        for f in estado.facts
        if f.autor is Capacidad.TUTORIZAR
        and f.vigencia.vigente
        and "senal" in f.contenido
    ]
    return {
        "asunto": entrega.asunto,
        "diseno": dict(entrega.diseno) if entrega.diseno is not None else None,
        "senales": senales,
        "memoria": (
            {
                "ruta": memoria.catalogo.get("ruta_actualizada"),
                "deuda_abierta": list(memoria.catalogo.get("deuda_abierta", ())),
                "modelo_propuesto": list(memoria.catalogo.get("modelo_propuesto", ())),
            }
            if memoria is not None
            else None
        ),
    }


def registrar_pregunta_tutor(student_id: str, course_id: str, pregunta: str) -> None:
    """E2 — la pregunta del estudiante al tutor entra al Runtime como
    interacción de sesión (RFC-0002 R4: Tutorizar observa
    "interacciones"; regla 1 de RFC-0010: el contenido viaja sin
    interpretar). Provenance `humano` (la escribió el estudiante). No
    urgente: la respuesta del chat la redacta la plataforma, no es la
    Entrega del runtime — nadie queda bloqueado esperando consenso."""
    almacen, almacen_memoria = almacenes()
    identidad = abrir_sesion(_peticion(student_id, course_id), almacen, almacen_memoria)
    registrar_hecho(
        PeticionHechoDelMundo(
            identidad=identidad,
            contenido={"interaccion": "pregunta-tutor", "pregunta": pregunta},
            origen=OrigenProvenance.HUMANO,
        ),
        almacen,
        almacen_memoria,
    )
