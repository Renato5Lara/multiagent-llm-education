"""Productor de Validar — versión regla (RFC-0002 §3, R7).

Puro-de-estado, a diferencia de Evaluar: no necesita ningún parámetro
externo. Recorre la cadena causal (P6, «la explicación se recorre») —
decisión → propuesta → interpretación → fact original — para hallar la
competencia en juego, y busca en el propio estado el fact posterior que
la mide de nuevo. Si esa evidencia todavía no existe, la capacidad
simplemente no dispara (RFC-0004 §4: la secuencia emerge).

`evidencia_de_validacion` dispara por FORMA del contenido (`competencia`
+ `items_incorrectos`), no por autor — mismo patrón ya aplicado en
Tutorizar y Diagnosticar (commit `4b8c577`): desde RFC-0010 (Grieta A) la
evidencia real la autora el Boundary, no `Capacidad.EVALUAR` (esa
capacidad no está wireada a ningún nodo del grafo — RFC-0010/Grieta A);
exigir `autor is EVALUAR` dejaba a Validar estructuralmente muda en el
flujo real (0 veredictos en producción, verificado contra 19,412
transiciones reales).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.shared.causal import competencia_de_decision
from runtime.kernel.state.entries import (
    Capacidad,
    DecisionEntry,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

__all__ = ["competencia_de_decision", "evidencia_de_validacion", "producir"]


def evidencia_de_validacion(estado: LearningState, decision: DecisionEntry, competencia: str):
    """El fact original (antes) y el primer fact posterior (después) de
    evidencia evaluativa para esa competencia — ninguno se adivina, ambos
    se leen. Por forma (`competencia` + `items_incorrectos`), no por
    autor — ver docstring del módulo."""
    de_evaluar = [
        f
        for f in estado.facts
        if "competencia" in f.contenido
        and f.contenido.get("competencia") == competencia
        and "items_incorrectos" in f.contenido
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
                        "competencia": competencia,
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
