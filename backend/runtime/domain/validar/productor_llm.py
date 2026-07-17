"""Productor de Validar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion`, mismo `asunto`,
misma forma de `respaldo` — únicamente cambia CÓMO se juzga si la
diferencia antes/después cuenta como mejora (P13). El conteo mismo no lo
decide el proveedor: eso ya lo determinó el recorrido del estado (P12).

A diferencia de Evaluar/Tutorizar (M3 PR-5/6): Validar produce un CLAIM
(`TipoClaim.INTERPRETACION` en el reducer, RFC-0003 línea 247), no un
fact — así que, aunque `funciono` sea derivable de `antes`/`despues`
por una regla determinista, el proveedor legítimamente aporta algo que
un fact no tiene: razonamiento y confianza declarada (mismo patrón que
`diagnosticar/productor_llm.py`). Un sondeo real (Engineering Review
previa, M3 PR-7) mostró que un prompt sin la regla explícita no solo
fallaba en forma, sino que era NO DETERMINISTA a temperature=0 (tres
respuestas distintas para el mismo prompt exacto) y semánticamente
incorrecto cuando la decisión empeoró. Declarar la regla explícitamente
en el prompt (regla `validacion-v1`) eliminó ambos problemas — 9/9
corridas reales correctas y estables.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
from runtime.domain.validar.productor import competencia_de_decision, evidencia_de_validacion
from runtime.domain.validar.provider import FakeLLMProvider, LLMProvider
from runtime.kernel.state.entries import (
    Capacidad,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "validacion-efecto-v1"


def producir(
    estado: LearningState, proveedor: LLMProvider | None = None
) -> tuple[TransitionIntent, ...]:
    proveedor = proveedor or FakeLLMProvider()
    for decision in estado.decisiones:
        if decision.estado_validacion is not EstadoValidacion.PENDIENTE_DE_VALIDACION:
            continue
        if not decision.vigencia.vigente:
            continue
        competencia = competencia_de_decision(estado, decision)
        if competencia is None:
            continue
        original, posterior = evidencia_de_validacion(estado, decision, competencia)
        if original is None:
            continue
        antes = len(original.contenido["items_incorrectos"])
        despues = len(posterior.contenido["items_incorrectos"])
        prompt = (
            f"antes={antes} despues={despues}. Una decisión se considera "
            f"exitosa cuando items_incorrectos DISMINUYÓ estrictamente "
            f"(despues < antes) — regla validacion-v1. Responde JSON con "
            f'esta forma EXACTA y en este ORDEN: primero "razonamiento" '
            f"(aplica la regla paso a paso), luego \"funciono\" (booleano, "
            f"DEBE ser consistente con la conclusión de tu razonamiento), "
            f'luego "confianza" (STRING con formato decimal entre "0.00" '
            f'y "1.00", ejemplo "0.80", nunca como palabra ni como número).'
        )
        respuesta = ejecutar_roundtrip(
            proveedor, prompt, campos_requeridos=("funciono", "confianza")
        )
        return (
            TransitionIntent(
                productor=Capacidad.VALIDAR,
                operacion="validar_decision",
                argumentos={
                    "decision_id": decision.id,
                    "autor": Capacidad.VALIDAR,
                    "asunto": f"efecto({decision.id})",
                    "afirmacion": {
                        "competencia": competencia,
                        "funciono": respuesta["funciono"],
                        "razonamiento": respuesta.get("razonamiento", ""),
                    },
                    "respaldo": (decision.id, posterior.id),
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
