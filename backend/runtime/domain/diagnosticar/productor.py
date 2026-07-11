"""Productor de Diagnosticar — versión regla (provenance `regla`).

Capacidad real y determinista: interpreta los resultados evaluativos con
la regla de scoring de politica-v1. Cuando llegue la versión LLM, cambia
la provenance y el interior — jamás la salida (P13: la capacidad es
estable; su implementación, intercambiable).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_UMBRAL_ERRORES = 2  # regla scoring-v1: ≥2 errores ⇒ competencia no dominada


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    """LEER → INTERPRETAR → PRODUCIR (RFC-0004 §1, pasos 1–3)."""
    ya_interprete = any(
        c.autor is Capacidad.DIAGNOSTICAR and c.vigencia.vigente
        for c in estado.claims
    )
    if ya_interprete:
        return ()
    for fact in estado.facts:
        if not fact.vigencia.vigente or "competencia" not in fact.contenido:
            continue
        errores = len(fact.contenido.get("items_incorrectos", ()))
        return (
            TransitionIntent(
                productor=Capacidad.DIAGNOSTICAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.DIAGNOSTICAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": f"dominio({fact.contenido['competencia']})",
                    "afirmacion": {
                        "dominada": errores < _UMBRAL_ERRORES,
                        "errores": errores,
                    },
                    "respaldo": (fact.id,),
                    "confianza": Decimal("0.78"),
                    "provenance": Provenance.de(
                        OrigenProvenance.REGLA, id="scoring-v1"
                    ),
                },
                base=estado.transicion,
            ),
        )
    return ()
