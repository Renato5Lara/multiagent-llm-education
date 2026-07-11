"""Productor de Orientar — versión regla: propone avanzar con andamiaje
(el otro lado de la tensión canónica n.º 1). No conoce a Remediar (P3):
solo lee el estado que Diagnosticar modificó."""

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

_ASUNTO = "siguiente-paso(sesion)"


def producir(estado: LearningState) -> tuple[TransitionIntent, ...]:
    ya_propuse = any(
        c.autor is Capacidad.ORIENTAR and c.vigencia.vigente for c in estado.claims
    )
    if ya_propuse:
        return ()
    for claim in estado.claims:
        if claim.tipo is TipoClaim.INTERPRETACION and claim.vigencia.vigente:
            return (
                TransitionIntent(
                    productor=Capacidad.ORIENTAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.ORIENTAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": _ASUNTO,
                        "afirmacion": {"accion": "avanzar-con-andamiaje"},
                        "respaldo": (claim.id,),
                        "confianza": Decimal("0.75"),
                        "provenance": Provenance.de(
                            OrigenProvenance.REGLA, id="ruta-v1"
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()
