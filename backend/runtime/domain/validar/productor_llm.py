"""Productor de Validar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo `operacion`, mismo `asunto`,
misma forma de `respaldo` — únicamente cambia CÓMO se juzga si la
diferencia antes/después cuenta como mejora (P13). El conteo mismo no lo
decide el proveedor: eso ya lo determinó el recorrido del estado (P12).
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
        prompt = f"antes={antes} despues={despues}. ¿Funcionó? Responde JSON."
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
