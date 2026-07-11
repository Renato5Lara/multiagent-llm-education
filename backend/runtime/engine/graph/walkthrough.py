"""El grafo mínimo del Walkthrough-0001 — la primera línea de LangGraph
del proyecto, sujeta a las ocho reglas del ADR-0006.

El programa pedagógico NO está cableado: `enrutar` es una función pura
del estado (RFC-0004 §4) y la secuencia observada emerge. Los nodos son
productores que devuelven TransitionIntents (reglas 1 y 8); el único que
muta es `aplicar` — el portal del Kernel — que reduce, encadena y
persiste **después de aplicar y antes de la siguiente activación**
(criterio 4 del tesista). El checkpointer nativo de LangGraph no se usa:
la fuente es nuestra cadena + AlmacenTransiciones (regla 5).
"""

from __future__ import annotations

from typing import Callable, TypedDict

from langgraph.graph import END, START, StateGraph

from runtime.domain.diagnosticar import producir as producir_diagnostico
from runtime.domain.modelar import producir as producir_modelado
from runtime.domain.orientar import producir as producir_orientacion
from runtime.domain.remediar import producir as producir_remediacion
from runtime.domain.validar import producir as producir_validacion
from runtime.domain.validar.productor import competencia_de_decision, evidencia_de_validacion
from runtime.engine.checkpoint import (
    AlmacenTransiciones,
    RegistroTransicion,
    encadenar,
)
from runtime.kernel.deliberation import (
    convocar,
    derivar_decision,
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
from runtime.kernel.state.entries import Capacidad, EstadoValidacion, TipoClaim
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


def _nodo_deliberar(grafo: EstadoGrafo) -> dict:
    intent = convocar(grafo["estado"])
    return {"intents": (intent,) if intent else ()}


def _nodo_decidir(grafo: EstadoGrafo) -> dict:
    intent = derivar_decision(grafo["estado"])
    return {"intents": (intent,) if intent else ()}


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


def enrutar(grafo: EstadoGrafo) -> str:
    """Función pura del estado (P12): nadie decide quién sigue, salvo el
    estado mismo. El orden de los chequeos ES el programa pedagógico."""
    estado = grafo["estado"]
    if estado.decisiones:
        if _decision_lista_para_validar(estado):
            return "validar"
        if _existe_veredicto_sin_modelar(estado):
            return "modelar"
        return END
    if estado.deliberaciones:
        return "decidir"
    if tension_bloqueante(estado) is not None:
        return "deliberar"
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
    if Capacidad.REMEDIAR not in autores:
        return "remediar"
    if Capacidad.ORIENTAR not in autores:
        return "orientar"
    return END


def _construir(
    almacen: AlmacenTransiciones,
    identidad: Identidad,
    productor_diagnostico: Callable = producir_diagnostico,
    productor_remediar: Callable = producir_remediacion,
    productor_orientar: Callable = producir_orientacion,
    productor_validar: Callable = producir_validacion,
    productor_modelar: Callable = producir_modelado,
):
    """Los productores son inyectables (por defecto, la versión regla de
    cada uno) — demuestra P13: el grafo, el scheduler, los reducers y el
    checkpoint no cambian una línea al intercambiar la implementación de
    una capacidad (ADR-0005 §7, guardián de P13)."""
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
    grafo.add_node("deliberar", _nodo_deliberar)
    grafo.add_node("decidir", _nodo_decidir)
    grafo.add_node("validar", _nodo_productor(productor_validar))
    grafo.add_node("modelar", _nodo_productor(productor_modelar))

    grafo.add_edge(START, "aplicar")  # aplica los hechos sembrados (E2)
    for productor in (
        "diagnosticar", "remediar", "orientar", "deliberar", "decidir",
        "validar", "modelar",
    ):
        grafo.add_edge(productor, "aplicar")
    grafo.add_conditional_edges("aplicar", enrutar)
    return grafo.compile()


def ejecutar_walkthrough(
    almacen: AlmacenTransiciones,
    identidad: Identidad,
    hechos_del_mundo: tuple[TransitionIntent, ...],
    productor_diagnostico: Callable = producir_diagnostico,
    productor_remediar: Callable = producir_remediacion,
    productor_orientar: Callable = producir_orientacion,
    productor_validar: Callable = producir_validacion,
    productor_modelar: Callable = producir_modelado,
) -> EstadoGrafo:
    """Corre el Walkthrough-0001: hechos → diagnóstico → tensión →
    deliberación → decisión (→ validación → modelado, si ya hay evidencia),
    con checkpoint por transición."""
    almacen.abrir_sesion(identidad)
    inicial: EstadoGrafo = {
        "estado": LearningState(
            identidad=identidad, contexto={"ruta": "condicionales"}
        ),
        "intents": hechos_del_mundo,
        "registros": (),
    }
    return _construir(
        almacen,
        identidad,
        productor_diagnostico,
        productor_remediar,
        productor_orientar,
        productor_validar,
        productor_modelar,
    ).invoke(inicial)
