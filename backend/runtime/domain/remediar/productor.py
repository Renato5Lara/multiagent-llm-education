"""Productor de Remediar — versión regla: ante una competencia no
dominada, propone reforzar antes de avanzar (tensión canónica n.º 1)."""

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

ASUNTO_SIGUIENTE_PASO = "siguiente-paso(sesion)"


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    ya_propuse = any(
        c.autor is Capacidad.REMEDIAR and c.vigencia.vigente for c in estado.claims
    )
    if ya_propuse:
        return ()
    for claim in estado.claims:
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.vigencia.vigente
            and claim.afirmacion.get("dominada") is False
        ):
            return (
                TransitionIntent(
                    productor=Capacidad.REMEDIAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.REMEDIAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": ASUNTO_SIGUIENTE_PASO,
                        "afirmacion": {"accion": "reforzar"},
                        "respaldo": (claim.id,),
                        "confianza": Decimal("0.82"),
                        "provenance": Provenance.de(
                            OrigenProvenance.REGLA, id="remediacion-v1"
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()
