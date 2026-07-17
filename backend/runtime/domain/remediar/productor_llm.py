"""Productor de Remediar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla (`productor.py`): mismo tipo de
claim, mismo asunto, misma estructura de argumentos hacia
`registrar_claim` — únicamente cambia CÓMO se justifica la propuesta
(P13: cambia la implementación, nunca el contrato).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.remediar.productor import ASUNTO_SIGUIENTE_PASO
from runtime.domain.remediar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.domain.shared.propuestas import palabra_en_pie
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "remediacion-siguiente-paso-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    """Misma guardia que la versión regla (`palabra_en_pie` — ciclo
    adaptativo continuo, 2026-07-13): re-propone solo si su palabra
    previa cayó con su respaldo o si el vencedor que la descartó cayó
    después (debate huérfano), jamás por el mero hecho de haber perdido
    una deliberación (anti-churn)."""
    proveedor = proveedor or FakeLLMProvider()
    if palabra_en_pie(estado, Capacidad.REMEDIAR, ASUNTO_SIGUIENTE_PASO):
        return ()
    for claim in estado.claims:
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.vigencia.vigente
            and claim.afirmacion.get("dominada") is False
        ):
            prompt = (
                f"El estudiante no domina la competencia (claim {claim.id}). "
                f'La política remediacion-v1 indica reforzar la competencia '
                f"antes de avanzar de tema. Responde JSON con esta forma "
                f'EXACTA y en este ORDEN: primero "razonamiento" (por qué '
                f'reforzar es la acción correcta aquí), luego "accion" '
                f'(STRING, debe ser exactamente "reforzar"), luego '
                f'"confianza" (STRING con formato decimal entre "0.00" y '
                f'"1.00", ejemplo "0.85").'
            )
            respuesta = ejecutar_roundtrip(
                proveedor, prompt, campos_requeridos=("accion", "confianza")
            )
            return (
                TransitionIntent(
                    productor=Capacidad.REMEDIAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.REMEDIAR,
                        "tipo": TipoClaim.PROPUESTA,
                        "asunto": ASUNTO_SIGUIENTE_PASO,
                        "afirmacion": {
                            "accion": respuesta["accion"],
                            "razonamiento": respuesta.get("razonamiento", ""),
                        },
                        "respaldo": (claim.id,),
                        "confianza": Decimal(str(respuesta["confianza"])),
                        "provenance": Provenance.de(
                            OrigenProvenance.LLM,
                            modelo=proveedor.modelo,
                            version=proveedor.version,
                            prompt_id=_PROMPT_ID,
                        ),
                    },
                    base=estado.transicion,
                ),
            )
    return ()
