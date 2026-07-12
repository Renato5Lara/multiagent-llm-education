"""Productor de Modelar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion` (registrar_claim),
mismo `tipo`, mismo `asunto`, misma forma de `respaldo` — únicamente
cambia CÓMO se interpreta la implicación del veredicto (P13).

Modelar produce un CLAIM (mismo criterio fijado en M3 PR-7: el tipo de
sobre, no la derivabilidad, decide la familia) — así que NO aplica
grounding. Pero es el caso más extremo de la familia claim: la regla no
aplica ni un umbral, copia literalmente `funciono` en `efecto_positivo`
(ver `productor.py`, y el guardián P13
`test_refleja_el_veredicto_sin_reinterpretarlo`) — Modelar no reabre el
veredicto de Validar, solo interpreta su implicación para el modelo del
estudiante. Un sondeo real (Engineering Review previa, M3 PR-8) mostró
que, sin declarar esa regla en el prompt, el modelo anida la respuesta
en una estructura libre inventada y nunca reproduce los campos
exigidos. Declararla explícitamente (mismo patrón que Diagnosticar/
Validar) produjo 10/10 corridas reales con `efecto_positivo` idéntico a
`funciono` en ambos casos — el LLM aporta razonamiento y confianza,
nunca el veredicto mismo.
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
            f"Esto es el veredicto ya determinado por Validar sobre si la "
            f"decisión pedagógica funcionó — efecto_positivo DEBE ser "
            f"exactamente igual a funciono (regla modelado-v1: Modelar no "
            f"reinterpreta el veredicto, solo explica su implicación para "
            f"el modelo del estudiante). Responde JSON con esta forma "
            f'EXACTA y en este ORDEN: primero "razonamiento" (explica la '
            f'implicación para el modelo del estudiante), luego '
            f'"efecto_positivo" (booleano, debe ser exactamente igual a '
            f'funciono), luego "confianza" (STRING con formato decimal '
            f'entre "0.00" y "1.00", ejemplo "0.80").'
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
