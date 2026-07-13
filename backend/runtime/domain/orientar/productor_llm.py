"""Productor de Orientar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla (`productor.py`): mismo tipo de
claim, mismo asunto, misma estructura de argumentos hacia
`registrar_claim` — únicamente cambia CÓMO se justifica la propuesta
(P13: cambia la implementación, nunca el contrato).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.orientar.productor import ASUNTO_SIGUIENTE_PASO
from runtime.domain.orientar.provider import FakeLLMProvider, LLMProvider
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

_PROMPT_ID = "orientacion-siguiente-paso-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    """Misma guardia que la versión regla (`palabra_en_pie` — ciclo
    adaptativo continuo, 2026-07-13): re-propone solo si su palabra
    previa cayó con su respaldo o si el vencedor que la descartó cayó
    después (debate huérfano), jamás por el mero hecho de haber perdido
    una deliberación (anti-churn). Filtra por interpretaciones de
    DOMINIO ("dominada" en la afirmación) — no cualquier INTERPRETACION:
    respaldarse en un veredicto de Validar creó un bucle real
    (2026-07-13), mismo criterio de forma que Remediar."""
    proveedor = proveedor or FakeLLMProvider()
    if palabra_en_pie(estado, Capacidad.ORIENTAR, ASUNTO_SIGUIENTE_PASO):
        return ()
    for claim in estado.claims:
        if (
            claim.tipo is TipoClaim.INTERPRETACION
            and claim.vigencia.vigente
            and "dominada" in claim.afirmacion
        ):
            prompt = (
                f"Existe una interpretación vigente sobre el estudiante "
                f"(claim {claim.id}). La política ruta-v1 propone avanzar "
                f"al siguiente objetivo con andamiaje adicional como "
                f"CANDIDATA en la deliberación — no es una decisión final "
                f"ni un juicio tuyo sobre si conviene: eso lo resuelve "
                f"después el Kernel comparando esta propuesta contra la "
                f'de Remediar. Responde JSON con esta forma EXACTA y en '
                f'este ORDEN: primero "razonamiento" (por qué '
                f"avanzar-con-andamiaje es una propuesta razonable aquí), "
                f'luego "accion" (STRING, debe ser exactamente '
                f'"avanzar-con-andamiaje"), luego "confianza" (STRING con '
                f'formato decimal entre "0.00" y "1.00", ejemplo "0.78").'
            )
            respuesta = ejecutar_roundtrip(
                proveedor, prompt, campos_requeridos=("accion", "confianza")
            )
            return (
                TransitionIntent(
                    productor=Capacidad.ORIENTAR,
                    operacion="registrar_claim",
                    argumentos={
                        "autor": Capacidad.ORIENTAR,
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
