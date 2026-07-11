"""Productor de Modelar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion` (registrar_claim),
mismo `tipo`, mismo `asunto`, misma forma de `respaldo` — únicamente
cambia CÓMO se interpreta la implicación del veredicto (P13).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.modelar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "modelado-implicacion-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    proveedor = proveedor or FakeLLMProvider()
    for validacion in estado.claims:
        if validacion.autor is not Capacidad.VALIDAR or not validacion.vigencia.vigente:
            continue
        ya_modele = any(
            c.autor is Capacidad.MODELAR
            and c.vigencia.vigente
            and validacion.id in c.respaldo
            for c in estado.claims
        )
        if ya_modele:
            continue
        competencia = validacion.afirmacion.get("competencia")
        funciono = validacion.afirmacion.get("funciono")
        if competencia is None or funciono is None:
            continue
        prompt = (
            f"competencia={competencia} funciono={str(funciono).lower()}. "
            f"¿Qué implica esto para el modelo del estudiante? Responde JSON."
        )
        respuesta = ejecutar_roundtrip(
            proveedor, prompt, campos_requeridos=("efecto_positivo", "confianza")
        )
        return (
            TransitionIntent(
                productor=Capacidad.MODELAR,
                operacion="registrar_claim",
                argumentos={
                    "autor": Capacidad.MODELAR,
                    "tipo": TipoClaim.INTERPRETACION,
                    "asunto": f"modelo-estudiante({competencia})",
                    "afirmacion": {
                        "competencia": competencia,
                        "efecto_positivo": respuesta["efecto_positivo"],
                        "razonamiento": respuesta.get("razonamiento", ""),
                    },
                    "respaldo": (validacion.id,),
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
