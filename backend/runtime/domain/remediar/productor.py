"""Productor de Remediar — versión regla: ante una competencia no
dominada, propone reforzar antes de avanzar (tensión canónica n.º 1)."""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.shared.propuestas import palabra_en_pie
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
    # "Ya dije mi palabra sobre este suelo" (ver domain/shared/
    # propuestas.py): re-propone solo si su palabra previa cayó con su
    # respaldo, o si el vencedor que la descartó cayó después — jamás
    # por el mero hecho de haber perdido una deliberación (anti-churn).
    if palabra_en_pie(estado, Capacidad.REMEDIAR, ASUNTO_SIGUIENTE_PASO):
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
