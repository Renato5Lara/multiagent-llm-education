"""El grafo mínimo del Walkthrough-0001 — la primera línea de LangGraph
del proyecto, sujeta a las ocho reglas del ADR-0006.

El programa pedagógico NO está cableado: `enrutar` es una función pura
de `(estado, política)` (RFC-0004 §4; RFC-0006/3 le agrega `política`,
antes solo dependía del estado) y la secuencia observada emerge. Los nodos son
productores que devuelven TransitionIntents (reglas 1 y 8); el único que
muta es `aplicar` — el portal del Kernel — que reduce, encadena y
persiste **después de aplicar y antes de la siguiente activación**
(criterio 4 del tesista). El checkpointer nativo de LangGraph no se usa:
la fuente es nuestra cadena + AlmacenTransiciones (regla 5).
"""

from __future__ import annotations

import dataclasses
from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from runtime.domain.adaptar import producir as producir_adaptacion
from runtime.domain.adaptar.productor import DISENO_POR_ACCION
from runtime.domain.diagnosticar import producir as producir_diagnostico
from runtime.domain.modelar import producir as producir_modelado
from runtime.domain.orientar import producir as producir_orientacion
from runtime.domain.remediar import producir as producir_remediacion
from runtime.domain.shared.causal import competencia_de_decision
from runtime.domain.tutorizar import producir as producir_tutoria
from runtime.domain.validar import producir as producir_validacion
from runtime.domain.validar.productor import evidencia_de_validacion
from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    RegistroTransicion,
    encadenar,
    reconstruir,
)
from runtime.kernel.deliberation import (
    Politica,
    convocar,
    derivar_decision,
    derivar_decision_directa,
    resolver_politica,
    tension_bloqueante,
)
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_deliberacion,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.memory import contexto_desde_version, preparar_version, validar_version
from runtime.kernel.state.entries import Capacidad, EstadoValidacion, TipoClaim
from runtime.kernel.state.salidas import proyectar_salidas
from runtime.kernel.state.state import Identidad, LearningState
from runtime.kernel.transitions import TransitionIntent

_OPERACIONES: dict[str, Callable] = {
    "registrar_fact": registrar_fact,
    "registrar_claim": registrar_claim,
    "registrar_deliberacion": registrar_deliberacion,
    "registrar_decision": registrar_decision,
    "validar_decision": validar_decision,
}


class EstadoGrafo(TypedDict):
    estado: LearningState
    intents: tuple[TransitionIntent, ...]
    registros: tuple[RegistroTransicion, ...]


def _nodo_productor(producir: Callable) -> Callable:
    """Regla 8: el nodo lee un estado inmutable y solo devuelve intents."""

    def nodo(grafo: EstadoGrafo) -> dict:
        return {"intents": producir(grafo["estado"])}

    return nodo


def _nodo_deliberar(grafo: EstadoGrafo, politica: Politica, urgente: bool) -> dict:
    """`urgente` (RFC-0006 §4, Parte E) es información del Boundary —
    ¿hay un estudiante esperando esta entrega en la pantalla? — jamás
    derivada de `estado.ejecucion` (ROADMAP-RFC-0006 §5/2). Llega como
    parámetro externo, igual que `politica`."""
    intent = convocar(grafo["estado"], politica, urgente)
    return {"intents": (intent,) if intent else ()}


def _nodo_decidir(grafo: EstadoGrafo, politica: Politica) -> dict:
    """Prueba primero `derivar_decision` (deliberación resuelta —
    RFC-0006/2 y anterior, sin cambios); si no hay nada que hacer ahí,
    `derivar_decision_directa` (propuesta única bajo θ — RFC-0006/3,
    Parte C). `enrutar()` solo enruta aquí cuando exactamente uno de
    los dos tiene trabajo pendiente — nunca ambos a la vez, por cómo
    están hechas las guardias de `enrutar()`."""
    estado = grafo["estado"]
    intent = derivar_decision(estado) or derivar_decision_directa(estado, politica)
    return {"intents": (intent,) if intent else ()}


def _decision_sin_adaptar(estado: LearningState) -> bool:
    """Guardia segura (PR-5): mismo criterio de disparo que
    `domain.adaptar.producir` — una decisión vigente cuya acción tiene
    diseño definido (DISENO_POR_ACCION) que Adaptar todavía no adaptó.
    Se rutea antes que Validar: Adaptar diseña la experiencia apenas
    existe la decisión, sin depender de evidencia posterior — Validar
    mide el efecto de esa experiencia más tarde."""
    for decision in estado.decisiones:
        if not decision.vigencia.vigente:
            continue
        if decision.contenido.get("accion") not in DISENO_POR_ACCION:
            continue
        ya_adapto = any(
            c.autor is Capacidad.ADAPTAR and c.vigencia.vigente and decision.id in c.respaldo
            for c in estado.claims
        )
        if not ya_adapto:
            return True
    return False


def _decision_lista_para_validar(estado: LearningState) -> bool:
    """Guardia segura (PR-2): mismo criterio de disparo que
    `domain.validar.producir` — evita rutear a "validar" cuando su propio
    contrato todavía no dispararía (falta el fact posterior de Evaluar),
    lo que produciría un ciclo aplicar→enrutar sin avance."""
    for decision in estado.decisiones:
        if decision.estado_validacion is not EstadoValidacion.PENDIENTE_DE_VALIDACION:
            continue
        if not decision.vigencia.vigente:
            continue
        competencia = competencia_de_decision(estado, decision)
        if competencia is None:
            continue
        original, _ = evidencia_de_validacion(estado, decision, competencia)
        if original is not None:
            return True
    return False


def _existe_veredicto_sin_modelar(estado: LearningState) -> bool:
    """Guardia segura (PR-3): mismo criterio de disparo que
    `domain.modelar.producir` — un veredicto vigente de Validar que ningún
    claim vigente de Modelar haya referenciado todavía en su respaldo.
    Predicado estructural plano (sin recorrido causal): a diferencia de
    Validar, no hace falta importar nada de domain.modelar."""
    for validacion in estado.claims:
        if validacion.autor is not Capacidad.VALIDAR or not validacion.vigencia.vigente:
            continue
        if (
            validacion.afirmacion.get("competencia") is None
            or validacion.afirmacion.get("funciono") is None
        ):
            continue
        ya_modelado = any(
            c.autor is Capacidad.MODELAR and c.vigencia.vigente and validacion.id in c.respaldo
            for c in estado.claims
        )
        if not ya_modelado:
            return True
    return False


def _existe_fact_evaluar_sin_tutorizar(estado: LearningState) -> bool:
    """Guardia segura (PR-4): mismo criterio de disparo que
    `domain.tutorizar.producir` — un fact vigente de Evaluar que Tutorizar
    todavía no procesó. Predicado estructural plano, igual que el de
    Modelar (sin recorrido causal, sin importar domain.tutorizar)."""
    for fact in estado.facts:
        if fact.autor is not Capacidad.EVALUAR or not fact.vigencia.vigente:
            continue
        if not fact.contenido.get("items_totales"):
            continue
        ya_detecte = any(
            f.autor is Capacidad.TUTORIZAR
            and f.vigencia.vigente
            and f.contenido.get("fact_origen") == str(fact.id)
            for f in estado.facts
        )
        if not ya_detecte:
            return True
    return False


def _interpretacion_pendiente_de_remediar(estado: LearningState) -> bool:
    """Guardia segura: mismo criterio de disparo que
    `domain.remediar.producir` — una interpretación vigente con
    `dominada=False` que Remediar todavía no atendió. Evita rutear a
    "remediar" cuando su propio contrato no dispararía (interpretación
    con `dominada=True`, competencia ya dominada, nada que remediar),
    lo que produciría un ciclo aplicar→enrutar sin avance — el mismo
    riesgo que ya cubren las guardias de Validar/Modelar/Tutorizar/
    Adaptar, aquí aplicado a Remediar."""
    ya_propuso = any(
        c.autor is Capacidad.REMEDIAR and c.vigencia.vigente for c in estado.claims
    )
    if ya_propuso:
        return False
    return any(
        c.tipo is TipoClaim.INTERPRETACION
        and c.vigencia.vigente
        and c.afirmacion.get("dominada") is False
        for c in estado.claims
    )


def enrutar(grafo: EstadoGrafo, politica: Politica) -> str:
    """Función pura de `(estado, politica)` (P12): nadie decide quién
    sigue, salvo el estado mismo. El orden de los chequeos ES el
    programa pedagógico. `politica` llega desde RFC-0006/3 (Parte C,
    ROADMAP-RFC-0006) — antes, `enrutar` solo dependía del estado."""
    estado = grafo["estado"]
    if estado.decisiones:
        if _decision_sin_adaptar(estado):
            return "adaptar"
        if _decision_lista_para_validar(estado):
            return "validar"
        if _existe_veredicto_sin_modelar(estado):
            return "modelar"
        return END
    # Guardia segura (Parte E, mismo patrón "misma función que el nodo"
    # que derivar_decision_directa más abajo): una deliberación aplazada
    # o escalada no tiene decisión derivable — enrutarla a "decidir"
    # ciclaría decidir→aplicar→decidir sin avance (precedente
    # GraphRecursionError). Solo se enruta cuando derivar_decision tiene
    # trabajo real (una Resuelta sin decisión).
    if derivar_decision(estado) is not None:
        return "decidir"
    if tension_bloqueante(estado) is not None:
        return "deliberar"
    if _existe_fact_evaluar_sin_tutorizar(estado):
        return "tutorizar"
    interpretaciones = [
        c
        for c in estado.claims
        if c.tipo is TipoClaim.INTERPRETACION and c.vigencia.vigente
    ]
    if not interpretaciones:
        return "diagnosticar"
    autores = {
        c.autor
        for c in estado.claims
        if c.tipo is TipoClaim.PROPUESTA and c.vigencia.vigente
    }
    if _interpretacion_pendiente_de_remediar(estado):
        return "remediar"
    if Capacidad.ORIENTAR not in autores:
        return "orientar"
    # Guardia segura (mismo patrón que PR-2..PR-5, precedente
    # GraphRecursionError): se llega aquí SOLO después de que tanto
    # Remediar como Orientar agotaron su oportunidad de proponer en
    # "siguiente-paso(sesion)" — es el único punto donde una propuesta
    # única puede considerarse definitiva (sin rival pendiente de
    # aparecer). Llamar la MISMA función que `_nodo_decidir` invocará
    # evita el riesgo que las guardias PR-2..PR-5 ya previenen para
    # otros nodos: que el guardia y el nodo evalúen criterios distintos
    # y diverjan (RFC-0006/3, corrige INV-6 — ver docstring de
    # `derivar_decision_directa`, mecanica.py).
    if derivar_decision_directa(estado, politica) is not None:
        return "decidir"
    return END


def _construir(
    almacen: AlmacenTransiciones,
    identidad: Identidad,
    productor_diagnostico: Callable = producir_diagnostico,
    productor_remediar: Callable = producir_remediacion,
    productor_orientar: Callable = producir_orientacion,
    productor_validar: Callable = producir_validacion,
    productor_modelar: Callable = producir_modelado,
    productor_tutorizar: Callable = producir_tutoria,
    productor_adaptar: Callable = producir_adaptacion,
    urgente: bool = False,
):
    """Los productores son inyectables (por defecto, la versión regla de
    cada uno) — demuestra P13: el grafo, el scheduler, los reducers y el
    checkpoint no cambian una línea al intercambiar la implementación de
    una capacidad (ADR-0005 §7, guardián de P13)."""
    politica: Politica = resolver_politica(identidad.version_politica)

    def aplicar(grafo: EstadoGrafo) -> dict:
        """El portal del Kernel: reducir → encadenar → persistir, por
        transición — el checkpoint ocurre antes de la siguiente activación."""
        estado, registros = grafo["estado"], grafo["registros"]
        for intent in grafo["intents"]:
            resultado = _OPERACIONES[intent.operacion](
                estado, **intent.argumentos
            )
            if not isinstance(resultado, Aplicado):
                # ADR-0004 E-2: un rechazo aquí es un bug del productor —
                # abortar ruidosamente, jamás disfrazarlo.
                raise RuntimeError(
                    f"rechazo inesperado ({resultado.invariante}): "
                    f"{resultado.motivo}"
                )
            estado = resultado.estado
            registro = encadenar(
                identidad,
                registros,
                {"intent": intent, "eventos": resultado.eventos},
            )
            almacen.persistir(registro)
            registros += (registro,)
        return {"estado": estado, "intents": (), "registros": registros}

    grafo = StateGraph(EstadoGrafo)
    grafo.add_node("aplicar", aplicar)
    grafo.add_node("diagnosticar", _nodo_productor(productor_diagnostico))
    grafo.add_node("remediar", _nodo_productor(productor_remediar))
    grafo.add_node("orientar", _nodo_productor(productor_orientar))
    grafo.add_node("deliberar", lambda g: _nodo_deliberar(g, politica, urgente))
    grafo.add_node("decidir", lambda g: _nodo_decidir(g, politica))
    grafo.add_node("validar", _nodo_productor(productor_validar))
    grafo.add_node("modelar", _nodo_productor(productor_modelar))
    grafo.add_node("tutorizar", _nodo_productor(productor_tutorizar))
    grafo.add_node("adaptar", _nodo_productor(productor_adaptar))

    grafo.add_edge(START, "aplicar")  # aplica los hechos sembrados (E2)
    for productor in (
        "diagnosticar", "remediar", "orientar", "deliberar", "decidir",
        "validar", "modelar", "tutorizar", "adaptar",
    ):
        grafo.add_edge(productor, "aplicar")
    grafo.add_conditional_edges("aplicar", lambda g: enrutar(g, politica))
    return grafo.compile()


@dataclasses.dataclass(frozen=True, slots=True)
class SesionAbierta:
    """Lo que `materializar_sesion` produce: un `LearningState` listo
    para ejecutar, más la historia ya leída (para no releerla al armar
    `EstadoGrafo`). M4 PR-6."""

    estado: LearningState
    registros: tuple[RegistroTransicion, ...]


def materializar_sesion(
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria | None,
    identidad: Identidad,
) -> SesionAbierta:
    """Abre o reanuda una sesión — nunca decide qué versión de memoria
    usar (RFC-0003 INV-1: `identidad.version_student_model` ya la fija
    atómicamente, decidida por quien construyó `identidad`; esta
    función solo la materializa vía `cargar_version`, jamás `cargar`
    vigente — M4 PR-6, Engineering Review previa).

    `almacen_memoria=None` (opt-in, mismo patrón que `cerrar_sesion` en
    `ejecutar_walkthrough`): `contexto` usa el valor por defecto, sin
    tocar memoria — compatibilidad con todo caller que todavía no
    integra Memoria.
    """
    almacen.abrir_sesion(identidad)
    registros_previos = almacen.leer(identidad.session_id)

    version_memoria = (
        almacen_memoria.cargar_version(identidad.student_id, identidad.version_student_model)
        if almacen_memoria is not None
        else None
    )
    contexto = contexto_desde_version(version_memoria)

    estado = (
        reconstruir(identidad, contexto, registros_previos)
        if registros_previos
        else LearningState(identidad=identidad, contexto=contexto)
    )
    return SesionAbierta(estado=estado, registros=registros_previos)


def ejecutar_walkthrough(
    almacen: AlmacenTransiciones,
    identidad: Identidad,
    hechos_del_mundo: tuple[TransitionIntent, ...],
    productor_diagnostico: Callable = producir_diagnostico,
    productor_remediar: Callable = producir_remediacion,
    productor_orientar: Callable = producir_orientacion,
    productor_validar: Callable = producir_validacion,
    productor_modelar: Callable = producir_modelado,
    productor_tutorizar: Callable = producir_tutoria,
    productor_adaptar: Callable = producir_adaptacion,
    cerrar_sesion: bool = False,
    almacen_memoria: AlmacenMemoria | None = None,
    urgente: bool = False,
) -> EstadoGrafo:
    """Corre el Walkthrough-0001: hechos → tutoría → diagnóstico → tensión
    → deliberación → decisión → adaptación (→ validación → modelado, si ya
    hay evidencia), con checkpoint por transición.

    Apertura/reanudación (M4 PR-6): delegada a `materializar_sesion` —
    esta función deja de construir `LearningState`; `almacen_memoria`
    (opt-in) también gobierna Cargar aquí, no solo Consolidar (ver más
    abajo). Cuando se provee, `contexto` viene de la versión de memoria
    exacta anclada en `identidad.version_student_model` (nunca "la más
    reciente" — esa decisión ya se tomó al construir `identidad`).

    Reanudación (M4 PR-1B): si `identidad.session_id` ya tiene historia
    persistida, el estado de arranque se reconstruye desde ella
    (`reconstruir`, RFC-0008 §3) en vez de partir de un `LearningState`
    vacío — nunca reejecuta un productor ni un proveedor LLM para
    reproducir esa historia (ADR-0007). `enrutar` es función pura del
    estado (P12): no distingue si el estado llegó de una única
    invocación o de una reconstruida, así que continúa exactamente donde
    la sesión anterior se detuvo de forma natural (`END` sin evidencia
    suficiente aún para Validar/Tutorizar).

    Contrato de `hechos_del_mundo` (vale para toda invocación, nueva o
    reanudada): es la evidencia NUEVA de ESTA invocación — nunca hechos
    ya persistidos. `ejecutar_walkthrough` no deduplica entradas del
    mundo (a diferencia de los productores, que sí evitan reinterpretar
    dos veces la misma evidencia vía sus propias guard clauses); volver
    a pasar un hecho ya aplicado lo registraría como una entrada nueva y
    distinta. Invariante que gobernará también a Boundary (RFC-0010,
    entrada E2) y a cualquier reanudación vía HITL o Memoria.

    Cierre (M4 PR-2): al terminar cada invocación, `estado.salidas`
    queda poblado con `proyectar_salidas` (RFC-0003 §2, RFC-0005 §2) —
    una proyección pura, recalculada siempre, nunca fuente de verdad.

    Urgencia (RFC-0006 §4, Parte E): `urgente=True` declara que hay un
    estudiante esperando esta entrega en la pantalla — con margen < δ,
    la deliberación se resuelve provisionalmente en vez de aplazarse
    (CONCEPT-0002 §4: "el aplazamiento es para el sistema; la
    provisionalidad es para el estudiante"). Es información del
    transporte que solo el llamador conoce (ROADMAP-RFC-0006 §5/2) —
    jamás se deriva de `estado.ejecucion`.

    Consolidar (M4 PR-5): `cerrar_sesion=True` es la señal explícita de
    cierre que ADR-0008 §2.4 exige — nunca se infiere de que el grafo
    llegue a `END` (una sesión reanudada llega a `END` varias veces sin
    cerrarse, M4 PR-1B). Con `cerrar_sesion=True`, `almacen_memoria` es
    obligatorio — su ausencia es un error de programación del llamador
    (ADR-0004 E-2), nunca un `None` silencioso. Una sesión consolida
    como máximo una vez (ADR-0008 §5); un segundo intento lo rechaza
    `AlmacenMemoria.consolidar` sin dejar la tabla a medias.
    """
    if cerrar_sesion and almacen_memoria is None:
        raise ValueError(
            "cerrar_sesion=True exige almacen_memoria — ADR-0008 §2.4: la "
            "consolidación nunca ocurre sin un almacén explícito"
        )
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    inicial: EstadoGrafo = {
        "estado": sesion.estado,
        "intents": hechos_del_mundo,
        "registros": sesion.registros,
    }
    final = _construir(
        almacen,
        identidad,
        productor_diagnostico,
        productor_remediar,
        productor_orientar,
        productor_validar,
        productor_modelar,
        productor_tutorizar,
        productor_adaptar,
        urgente=urgente,
    ).invoke(inicial)

    # T14 — Cierre (M4 PR-2): proyección pura, fuera del grafo (no es un
    # TransitionIntent, no muta el dominio, no emite Domain Events —
    # ADR-0006 regla 1: los nodos solo proponen intents). Se recalcula
    # en cada invocación; nunca es fuente de verdad (RFC-0003/RFC-0005).
    final["estado"] = dataclasses.replace(
        final["estado"], salidas=proyectar_salidas(final["estado"])
    )

    if cerrar_sesion:
        version = preparar_version(identidad, final["estado"].salidas)
        validar_version(version)
        almacen_memoria.consolidar(version)

    return final
