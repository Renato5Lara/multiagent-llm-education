"""Recorrido causal decisión → competencia / señal (P6, «la explicación se
recorre»).

Extraído tras el segundo consumidor genuino (Validar, Adaptar) — mismo
criterio de evidencia que ya justificó `llm_roundtrip.py`: infraestructura
de recorrido del estado, no lógica de negocio de ninguna capacidad
concreta (P3 impide que Adaptar importe domain/validar directamente).
"""

from __future__ import annotations

from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    FactEntry,
    Resuelta,
)
from runtime.kernel.state.state import LearningState


def _fact_original_de_decision(
    estado: LearningState, decision: DecisionEntry
) -> FactEntry | None:
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
    return fact


def competencia_de_decision(estado: LearningState, decision: DecisionEntry) -> str | None:
    """Recorre decisión → propuesta → interpretación → fact original."""
    fact = _fact_original_de_decision(estado, decision)
    return None if fact is None else fact.contenido.get("competencia")


def modalidad_estudiante_de_decision(estado: LearningState, decision: DecisionEntry) -> str | None:
    """Modalidad diagnosticada del estudiante (visual/reading/audio/
    kinesthetic), cuando el Boundary la adjuntó al fact original —
    mismo recorrido causal que `competencia_de_decision`, nunca por
    posición ni por "último fact"."""
    fact = _fact_original_de_decision(estado, decision)
    return None if fact is None else fact.contenido.get("modalidad_estudiante")


def senal_tutorizar_de_decision(
    estado: LearningState, decision: DecisionEntry
) -> FactEntry | None:
    """Recorre decisión → ... → fact original → fact de Tutorizar que
    declara ESE fact como su `fact_origen` (P6: nunca por posición ni por
    "último fact", siempre por la relación causal ya validada para
    competencia)."""
    fact_original = _fact_original_de_decision(estado, decision)
    if fact_original is None:
        return None
    for fact in estado.facts:
        if (
            fact.autor is Capacidad.TUTORIZAR
            and fact.vigencia.vigente
            and fact.contenido.get("fact_origen") == str(fact_original.id)
        ):
            return fact
    return None
