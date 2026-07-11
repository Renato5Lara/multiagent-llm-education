"""Productor de Diagnosticar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla (`productor.py`): mismo tipo de
claim, mismo asunto, misma estructura de argumentos hacia
`registrar_claim` — únicamente cambia CÓMO se interpreta el hecho (P13:
cambia la implementación, nunca el contrato). El runtime no distingue
esta capacidad de su versión regla: ambas producen exclusivamente
`TransitionIntent`s hacia el mismo reducer.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.diagnosticar.productor import _UMBRAL_ERRORES
from runtime.domain.diagnosticar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "diagnostico-competencia-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    """LEER → INTERPRETAR → PRODUCIR (RFC-0004 §1, pasos 1–3)."""
    proveedor = proveedor or FakeLLMProvider()
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
        prompt = (
            f"Competencia={fact.contenido['competencia']} "
            f"items_incorrectos={errores}. Una competencia se considera "
            f"DOMINADA cuando tiene menos de {_UMBRAL_ERRORES} items "
            f"incorrectos (regla scoring-v1). Responde JSON con esta "
            f'forma EXACTA y en este ORDEN: primero "razonamiento" '
            f"(explica el criterio y aplica la regla paso a paso), luego "
            f'"errores" (el número de items incorrectos), luego '
            f'"dominada" (booleano, DEBE ser consistente con la '
            f'conclusión de tu razonamiento), luego "confianza" (STRING '
            f'con formato decimal entre "0.00" y "1.00", ejemplo "0.80", '
            f"nunca como palabra ni como número)."
        )
        respuesta = ejecutar_roundtrip(
            proveedor, prompt, campos_requeridos=("dominada", "errores", "confianza")
        )
        return (
            TransitionIntent(
                productor=Capacidad.DIAGNOSTICAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.DIAGNOSTICAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": f"dominio({fact.contenido['competencia']})",
                    "afirmacion": {
                        "dominada": respuesta["dominada"],
                        "errores": respuesta["errores"],
                        "razonamiento": respuesta.get("razonamiento", ""),
                    },
                    "respaldo": (fact.id,),
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
