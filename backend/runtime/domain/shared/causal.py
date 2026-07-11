"""Recorrido causal decisión → competencia (P6, «la explicación se recorre»).

Extraído tras el segundo consumidor genuino (Validar, Adaptar) — mismo
criterio de evidencia que ya justificó `llm_roundtrip.py`: infraestructura
de recorrido del estado, no lógica de negocio de ninguna capacidad
concreta (P3 impide que Adaptar importe domain/validar directamente).
"""

from __future__ import annotations

from runtime.kernel.state.entries import ClaimEntry, DecisionEntry, DeliberacionEntry, FactEntry, Resuelta
from runtime.kernel.state.state import LearningState


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
