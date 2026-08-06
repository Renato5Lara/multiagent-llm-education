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
from runtime.domain.shared.objetivos import ObjetivoOrdenado, asunto_avance
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, TipoClaim


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
    hints_used: int | None = None,
    time_ms: int | None = None,
    objetivos: tuple[ObjetivoOrdenado, ...] = (),
    urgente: bool = False,
) -> Entrega:
    """El primer hecho real del flujo del estudiante que entra por el
    Boundary. `titulo_modulo` se traduce a `competencia` vía ADR-0010
    (`normalizar_asunto` — nunca un valor de COMP-0..5).

    `objetivos` (DESIGN-orientar-ruta-completa.md, Fase 2): estructura
    del curso, construida con `construir_objetivos`. Vacío (default):
    Orientar/Remediar operan sobre el asunto de sesión único, como
    siempre. No vacío: además producen, si corresponde, una propuesta
    por objetivo que `avance_por_objetivo` puede leer después.

    `items_totales` activa la señal de sesión de Tutorizar (RFC-0002
    R4: fluidez/confusión/frustración) — su productor exige el total
    para clasificar; sin él la evidencia sigue siendo válida pero la
    señal conductual no se produce.

    `modalidad_estudiante` (visual/reading/audio/kinesthetic, ya
    diagnosticada) permite que Adaptar honre la modalidad real en el
    caso "reforzar" (RFC-0002 §3: Adaptar lee "modelo del estudiante") —
    sin ella, el diseño usa su valor por defecto de siempre.

    `hints_used`/`time_ms` (ya presentes en `CycleEvidenceSubmit`, antes
    solo llegaban al dataset de investigación — nunca al propio hecho)
    permiten que Tutorizar deje de usar la proporción de items
    incorrectos como único proxy de la señal conductual (RFC-0002 R4:
    "detecta señales conductuales... a partir de la sesión") y clasifique
    con la evidencia real de la sesión — mismo vocabulario cerrado de
    señales, ninguna nueva.

    `urgente` (RFC-0006 §4 Parte E; mismo contrato que
    `PeticionHechoDelMundo.urgente`, `runtime/boundary/inbound/dto.py`):
    ¿la `Entrega` de esta llamada forma parte de la respuesta síncrona
    que desbloquea la siguiente acción del estudiante? Default `False`
    — el llamador lo declara explícitamente cuando sí lo es (ver
    ROADMAP-RFC-0006.md §8, tabla de clasificación por consumidor;
    ADR-0015 §8 documenta el hallazgo que hizo falta esta propagación)."""
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
    if hints_used is not None:
        contenido["hints_used"] = hints_used
    if time_ms is not None:
        contenido["time_ms"] = time_ms
    return registrar_hecho(
        PeticionHechoDelMundo(
            identidad=identidad,
            contenido=contenido,
            origen=OrigenProvenance.INSTRUMENTO,
            objetivos=objetivos,
            urgente=urgente,
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


def construir_objetivos(
    objetivos_curso: list[tuple[str, str, int]],
) -> tuple[ObjetivoOrdenado, ...]:
    """Traduce objetivos de la plataforma (`LearningObjective`) al
    parámetro externo que Orientar/Remediar aceptan (DESIGN-orientar-
    ruta-completa.md) — una sola traducción, mismo criterio que
    `asunto_de_modalidad`: ningún llamador arma `normalizar_asunto` por
    su cuenta. `objetivos_curso` es `[(id, title, order), ...]`."""
    return tuple(
        ObjetivoOrdenado(id=oid, asunto=normalizar_asunto(title), orden=orden)
        for oid, title, orden in objetivos_curso
    )


def avance_por_objetivo(
    student_id: str, course_id: str, objetivos: tuple[ObjetivoOrdenado, ...]
) -> dict[str, str]:
    """S3, solo lectura — `{objetivo.id: "avanzar" | "reforzar"}` para los
    objetivos con propuesta vigente de Orientar/Remediar (DESIGN-
    orientar-ruta-completa.md). Objetivos ausentes del dict: sin
    evidencia todavía — el llamador decide su comportamiento por
    defecto, nunca esta función (mismo contrato que `decision_adaptativa`
    y `consultar_decision_vigente`). Nunca registra nada (regla 2 de
    RFC-0010)."""
    if not objetivos:
        return {}
    almacen, almacen_memoria = almacenes()
    peticion = _peticion(student_id, course_id)
    estado = consultar_estado(peticion, almacen, almacen_memoria)
    resultado: dict[str, str] = {}
    for objetivo in objetivos:
        asunto = asunto_avance(objetivo.asunto)
        for claim in estado.claims:
            if not (
                claim.tipo is TipoClaim.PROPUESTA
                and claim.vigencia.vigente
                and claim.asunto == asunto
                and claim.autor in (Capacidad.ORIENTAR, Capacidad.REMEDIAR)
            ):
                continue
            accion = claim.afirmacion.get("accion")
            if accion in ("avanzar", "reforzar"):
                resultado[objetivo.id] = accion
            break
    return resultado


def decision_adaptativa_neutra() -> dict[str, Any]:
    """La respuesta de `/adaptive-decision` cuando el Runtime todavía no
    tiene ninguna evidencia del estudiante (ni diagnóstico ni pre-test
    ni evaluaciones). Un default de presentación (orden mixto, sin
    énfasis), jamás una decisión: desaparece con el primer hecho real."""
    return {
        "content_order": list(ORDEN_CONTENIDO_POR_MODALIDAD["mixta"]),
        "content_type_labels": CONTENT_TYPE_LABELS,
        "skip_hint_topics": [],
        "skip_hint_topic_labels": [],
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


def _asuntos_de_competencias_pretest() -> frozenset[str]:
    """Los 6 asuntos que produce `knowledge_test_service._evidencia_por_
    competencia` (dimensión cognitiva del pre-test — COMP_0..COMP_5,
    `titulo_modulo=COMPETENCY_LABELS[topic]` normalizado), NUNCA temas de
    curso reales. Diagnosticar interpreta evidencia sobre ambas familias
    de asunto con el mismo mecanismo (P13: mismo contrato, cualquier
    asunto) — correcto para que el pre-test alimente modalidad/profundidad
    como evidencia temprana. Pero `emphasis_topics`/`skip_hint_topics` de
    `decision_adaptativa` se muestran al estudiante como "temas
    prioritarios" de Fundamentos de Programación: mostrar aquí una
    competencia cognitiva ("Comprensión del problema") mezclada con un
    tema real ("Loops") sugiere que la adaptación ignora el curso y solo
    mira una taxonomía genérica. Se filtran aquí, no en el pre-test (que
    sigue alimentando al runtime igual) ni en Diagnosticar (que no debe
    saber para qué se van a mostrar sus interpretaciones)."""
    from app.data.knowledge_test_bank import COMPETENCY_LABELS

    return frozenset(normalizar_asunto(label) for label in COMPETENCY_LABELS.values())


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
    asuntos_pretest = _asuntos_de_competencias_pretest()
    emphasis = sorted(
        {
            _competencia_de_asunto(c.asunto)
            for c in interpretaciones
            if c.afirmacion["dominada"] is False
        }
        - asuntos_pretest
    )
    dominadas = sorted(
        {
            _competencia_de_asunto(c.asunto)
            for c in interpretaciones
            if c.afirmacion["dominada"] is True
        }
        - asuntos_pretest
    )

    def _etiqueta(slug: str) -> str:
        # Las 6 competencias del pre-test usan slugs internos con prefijo de
        # índice ("comp_0_problema") — el humanizador genérico los mostraba
        # tal cual ("Comp 0 problema"), un identificador interno filtrado a
        # la UI del estudiante. `COMPETENCY_LABELS` (app/data/knowledge_test_
        # bank.py) ya es la fuente de verdad para su nombre pedagógico. Los
        # slugs de temas de curso reales (p. ej. "loops", "arrays") vienen
        # de `ProgrammingConcept` (app/models/programming_domain.py, inglés
        # por diseño — vocabulario interno del Runtime) y tienen su propia
        # tabla, `PROGRAMMING_CONCEPT_LABELS` (Sesión UX/UI 2026-08-05, H1).
        # Solo un slug fuera de ambas tablas cae al humanizador genérico.
        #
        # `normalizar_asunto()` (runtime/boundary/inbound/asunto.py) convierte
        # CUALQUIER caracter no alfanumérico —incluido "_"— en "-": el slug
        # que de verdad llega aquí es "input-output", nunca "input_output"
        # (el valor literal de `ProgrammingConcept.INPUT_OUTPUT`). Sin esta
        # normalización, todo concepto de más de una palabra (8 de los 26)
        # fallaba la búsqueda en `PROGRAMMING_CONCEPT_LABELS` en silencio —
        # encontrado validando visualmente contra el servidor real, no en
        # los tests (fixture de un test usaba justo un slug de una palabra).
        from app.data.knowledge_test_bank import COMPETENCY_LABELS
        from app.models.programming_domain import PROGRAMMING_CONCEPT_LABELS

        slug_con_guion_bajo = slug.replace("-", "_")
        return (
            COMPETENCY_LABELS.get(slug)
            or PROGRAMMING_CONCEPT_LABELS.get(slug)
            or PROGRAMMING_CONCEPT_LABELS.get(slug_con_guion_bajo)
            or slug.replace("-", " ").replace("_", " ").capitalize()
        )

    return {
        "content_order": orden,
        "content_type_labels": CONTENT_TYPE_LABELS,
        "skip_hint_topics": dominadas,
        "emphasis_topics": emphasis,
        "emphasis_topic_labels": [_etiqueta(t) for t in emphasis],
        # `skip_hint_topics` (arriba) se mantiene crudo a propósito: el
        # frontend lo usa también para deduplicar contra `competencies`
        # (slugs crudos de misión, `Dashboard.tsx`) — traducirlo ahí
        # rompería esa comparación. `skip_hint_topic_labels` es aditivo,
        # solo para mostrar (mismo patrón que `emphasis_topic_labels`).
        "skip_hint_topic_labels": [_etiqueta(t) for t in dominadas],
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
