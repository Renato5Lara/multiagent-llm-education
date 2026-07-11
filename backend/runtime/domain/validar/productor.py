"""Productor de Validar — versión regla (RFC-0002 §3, R7).

Puro-de-estado, a diferencia de Evaluar: no necesita ningún parámetro
externo. Recorre la cadena causal (P6, «la explicación se recorre») —
decisión → propuesta → interpretación → fact original — para hallar la
competencia en juego, y busca en el propio estado el fact posterior de
Evaluar que la mide de nuevo. Si esa evidencia todavía no existe, la
capacidad simplemente no dispara (RFC-0004 §4: la secuencia emerge).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    EntryId,
    EstadoValidacion,
    FactEntry,
    OrigenProvenance,
    Provenance,
    Resuelta,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent


def competencia_de_decision(estado: LearningState, decision: DecisionEntry) -> str | None:
    """Recorre decisión → propuesta → interpretación → fact original."""
    origen = estado.buscar(decision.origen)
    if isinstance(origen, DeliberacionEntry):
        if not isinstance(origen.resultado, Resuelta):
            return None
        propuesta = estado.buscar(origen.resultado.aceptados[0])
    else:
        propuesta = origen  # decisión derivada de un claim-propuesta único
    if not isinstance(propuesta, ClaimEntry) or not propuesta.respaldo:
        return None
    interpretacion = estado.buscar(propuesta.respaldo[0])
    if not isinstance(interpretacion, ClaimEntry) or not interpretacion.respaldo:
        return None
    fact = estado.buscar(interpretacion.respaldo[0])
    if not isinstance(fact, FactEntry):
        return None
    return fact.contenido.get("competencia")


def evidencia_de_validacion(estado: LearningState, decision: DecisionEntry, competencia: str):
    """El fact original (antes) y el primer fact posterior (después) de
    Evaluar para esa competencia — ninguno se adivina, ambos se leen."""
    de_evaluar = [
        f
        for f in estado.facts
        if f.autor is Capacidad.EVALUAR and f.contenido.get("competencia") == competencia
    ]
    anteriores = [f for f in de_evaluar if f.id.transicion < decision.id.transicion]
    posteriores = [f for f in de_evaluar if f.id.transicion > decision.id.transicion]
    if not anteriores or not posteriores:
        return None, None
    return anteriores[0], posteriores[0]


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    for decision in estado.decisiones:
        if decision.estado_validacion is not EstadoValidacion.PENDIENTE_DE_VALIDACION:
            continue
        if not decision.vigencia.vigente:
            continue
        competencia = competencia_de_decision(estado, decision)
        if competencia is None:
            continue
        original, posterior = evidencia_de_validacion(estado, decision, competencia)
        if original is None:
            continue
        antes = len(original.contenido["items_incorrectos"])
        despues = len(posterior.contenido["items_incorrectos"])
        return (
            TransitionIntent(
                productor=Capacidad.VALIDAR,
                operacion="validar_decision",
                argumentos={
                    "decision_id": decision.id,
                    "autor": Capacidad.VALIDAR,
                    "asunto": f"efecto({decision.id})",
                    "afirmacion": {
                        "funciono": despues < antes,
                        "items_antes": antes,
                        "items_despues": despues,
                    },
                    "respaldo": (decision.id, posterior.id),
                    "confianza": Decimal("0.80"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="validacion-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
