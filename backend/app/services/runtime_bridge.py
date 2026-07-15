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

import re
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
    modalidad_estudiante: str | None = None,
) -> Entrega:
    """El primer hecho real del flujo del estudiante que entra por el
    Boundary. `titulo_modulo` se traduce a `competencia` vía ADR-0010
    (`normalizar_asunto` — nunca un valor de COMP-0..5).

    `items_totales` activa la señal de sesión de Tutorizar (RFC-0002
    R4: fluidez/confusión/frustración) — su productor exige el total
    para clasificar; sin él la evidencia sigue siendo válida pero la
    señal conductual no se produce.

    `modalidad_estudiante` (visual/reading/audio/kinesthetic, ya
    diagnosticada) permite que Adaptar honre la modalidad real en el
    caso "reforzar" (RFC-0002 §3: Adaptar lee "modelo del estudiante") —
    sin ella, el diseño usa su valor por defecto de siempre."""
    almacen, almacen_memoria = almacenes()
    identidad = abrir_sesion(_peticion(student_id, course_id), almacen, almacen_memoria)
    contenido: dict[str, Any] = {
        "competencia": normalizar_asunto(titulo_modulo),
        "items_incorrectos": items_incorrectos,
    }
    if items_totales is not None:
        contenido["items_totales"] = items_totales
    if modalidad_estudiante is not None:
        contenido["modalidad_estudiante"] = modalidad_estudiante
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


def asunto_de_modalidad(titulo_modulo: str) -> str:
    """El `asunto` que Adaptar produce SIEMPRE tiene la forma
    `f"modalidad({competencia})"` (`runtime/domain/adaptar/productor.py`
    — el único lugar del runtime que fija `asunto` para sus claims); no
    es la competencia sola. Comparar contra `normalizar_asunto(titulo)`
    directamente nunca coincide — bug real encontrado en la Épica 2 (la
    comparación ingenua hacía que ninguna decisión del runtime se
    aplicara, silenciosamente). Extraído de `module_orchestration_
    service` para que TODO consumidor de la Entrega derive igual —
    una sola traducción, cero decisiones propias."""
    return f"modalidad({normalizar_asunto(titulo_modulo)})"


def bloom_target_desde_entrega(
    bloom_configurado: int | None, asunto_esperado: str, entrega: Entrega
) -> int:
    """El runtime decide, la plataforma ejecuta: si la Entrega vigente
    (S1) es sobre la MISMA competencia (`asunto_esperado`, ADR-0010), su
    `profundidad` gobierna el Bloom objetivo — "fundamentos" (accion
    "reforzar") nunca pide más que Comprender; "aplicacion" conserva el
    nivel configurado. Sin decisión aplicable: el nivel configurado del
    módulo, sin tocar."""
    base = bloom_configurado or 3
    if entrega.diseno is None or entrega.asunto != asunto_esperado:
        return base
    if entrega.diseno.get("profundidad") == "fundamentos":
        return min(base, 2)
    return base


def modalidad_desde_entrega(asunto_esperado: str, entrega: Entrega) -> str | None:
    """La modalidad que el runtime decidió para esta competencia
    (literalmente la palabra de `DISENO_POR_ACCION`, sin taxonomía
    adicional), o `None` si la Entrega vigente no aplica a este módulo
    — quien consuma decide su neutro, jamás una regla propia."""
    if entrega.diseno is None or entrega.asunto != asunto_esperado:
        return None
    modalidad = entrega.diseno.get("modalidad")
    return str(modalidad) if modalidad else None


#: Orden de bloques de contenido por modalidad del runtime (vocabulario
#: literal de `DISENO_POR_ACCION` — "visual" para "reforzar", "mixta"
#: para "avanzar-con-andamiaje"; sin taxonomía pedagógica adicional).
#: Es TRADUCCIÓN de la decisión, no una decisión: el orden solo dice
#: cómo se renderiza la modalidad que el runtime ya eligió.
ORDEN_CONTENIDO_POR_MODALIDAD: dict[str, tuple[str, ...]] = {
    "visual": ("diagram", "example", "video", "theory", "exercise", "simulation", "game"),
    "mixta": ("theory", "diagram", "example", "exercise", "video", "simulation", "game"),
}

#: Etiquetas de los tipos de bloque para la UI (heredadas del motor
#: D4.1 al retirarlo — presentación, no decisión).
CONTENT_TYPE_LABELS: dict[str, str] = {
    "theory": "Teoría",
    "example": "Ejemplo",
    "video": "Video",
    "diagram": "Diagrama",
    "game": "Juego",
    "simulation": "Simulación",
    "exercise": "Ejercicio",
}


def decision_adaptativa_neutra() -> dict[str, Any]:
    """La respuesta de `/adaptive-decision` cuando el Runtime todavía no
    tiene ninguna evidencia del estudiante (ni diagnóstico ni pre-test
    ni evaluaciones). Un default de presentación (orden mixto, sin
    énfasis), jamás una decisión: desaparece con el primer hecho real."""
    return {
        "content_order": list(ORDEN_CONTENIDO_POR_MODALIDAD["mixta"]),
        "content_type_labels": CONTENT_TYPE_LABELS,
        "skip_hint_topics": [],
        "emphasis_topics": [],
        "emphasis_topic_labels": [],
        "strategy_description": (
            "Aún no hay evidencia de tu aprendizaje: completa el diagnóstico "
            "o tu primera actividad para que el sistema multiagente decida "
            "tu estrategia."
        ),
        "prior_emphasis": "",
        "modality_label": "mixta",
    }

_RE_COMPETENCIA = re.compile(r"^[a-z]+\((?P<competencia>.+)\)$")


def _competencia_de_asunto(asunto: str) -> str:
    """`"modalidad(bucles)"` → `"bucles"`; `"dominio(x)"` → `"x"`. Si el
    asunto no tiene esa forma, se devuelve tal cual (traducción, jamás
    inferencia)."""
    m = _RE_COMPETENCIA.match(asunto)
    return m.group("competencia") if m else asunto


def decision_adaptativa(student_id: str, course_id: str) -> dict[str, Any] | None:
    """S3, solo lectura — la estrategia de contenido derivada de lo que
    el Runtime ya decidió para este estudiante en este curso (el motor
    D4.1, tabla VARK×nivel, fue retirado; el diagnóstico entra hoy como
    evidencia y la primera decisión también es del Runtime):

    - `content_order` — de la modalidad de la Entrega vigente (S1),
      ajustada por su `profundidad` (fundamentos → teoría/ejemplo
      primero; aplicacion → práctica primero).
    - `emphasis_topics` — competencias que Diagnosticar interpretó como
      NO dominadas (interpretaciones vigentes, `dominada=False`).
    - `skip_hint_topics` — competencias que Diagnosticar ya interpretó
      como dominadas.

    `None` si el runtime todavía no decidió nada para este curso
    (estudiante sin evidencia) — el llamador decide su arranque en frío,
    nunca esta función."""
    almacen, almacen_memoria = almacenes()
    peticion = _peticion(student_id, course_id)
    entrega = consultar_entrega_vigente(peticion, almacen, almacen_memoria)
    if entrega.diseno is None or entrega.asunto is None:
        return None
    estado = consultar_estado(peticion, almacen, almacen_memoria)

    modalidad = str(entrega.diseno.get("modalidad") or "mixta")
    profundidad = entrega.diseno.get("profundidad")
    orden = list(
        ORDEN_CONTENIDO_POR_MODALIDAD.get(
            modalidad, ORDEN_CONTENIDO_POR_MODALIDAD["mixta"]
        )
    )
    if profundidad == "fundamentos":
        al_frente = ["theory", "example"]
        nota = "Refuerzo de fundamentos: teoría y ejemplos antes de la práctica."
    elif profundidad == "aplicacion":
        al_frente = ["exercise"]
        nota = "Énfasis en aplicación: práctica desde el inicio, con andamiaje."
    else:
        al_frente = []
        nota = ""
    for bloque in reversed(al_frente):
        if bloque in orden:
            orden.remove(bloque)
            orden.insert(0, bloque)

    interpretaciones = [
        c
        for c in estado.claims
        if c.autor is Capacidad.DIAGNOSTICAR
        and c.vigencia.vigente
        and "dominada" in c.afirmacion
    ]
    emphasis = sorted(
        {
            _competencia_de_asunto(c.asunto)
            for c in interpretaciones
            if c.afirmacion["dominada"] is False
        }
    )
    dominadas = sorted(
        {
            _competencia_de_asunto(c.asunto)
            for c in interpretaciones
            if c.afirmacion["dominada"] is True
        }
    )

    def _etiqueta(slug: str) -> str:
        return slug.replace("-", " ").replace("_", " ").capitalize()

    return {
        "content_order": orden,
        "content_type_labels": CONTENT_TYPE_LABELS,
        "skip_hint_topics": dominadas,
        "emphasis_topics": emphasis,
        "emphasis_topic_labels": [_etiqueta(t) for t in emphasis],
        "strategy_description": (
            f"Estrategia decidida por el sistema multiagente a partir de tu "
            f"evidencia real: modalidad {modalidad}."
        ),
        "prior_emphasis": nota,
        "modality_label": modalidad,
    }


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
