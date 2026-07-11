"""Productor de Evaluar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo tipo de intent
(`registrar_fact`), mismas claves de `contenido` — únicamente cambia CÓMO
se confirma el conteo (P13). El proveedor no decide qué está incorrecto:
eso ya lo determinan `respuestas` (P12); solo confirma el resultado a
través de un round-trip de prompt.
"""

from __future__ import annotations

import json
from typing import Mapping

from runtime.domain.evaluar.provider import FakeLLMProvider, LLMProvider
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

_PROMPT_ID = "evaluacion-conteo-v1"


def producir(
    estado: LearningState,
    respuestas: Mapping[int, bool],
    competencia: str,
    proveedor: LLMProvider | None = None,
) -> tuple[TransitionIntent, ...]:
    proveedor = proveedor or FakeLLMProvider()
    ya_evalue = any(
        f.autor is Capacidad.EVALUAR
        and f.vigencia.vigente
        and f.contenido.get("competencia") == competencia
        for f in estado.facts
    )
    if ya_evalue:
        return ()
    items_incorrectos = sorted(
        item for item, correcto in respuestas.items() if not correcto
    )
    items_str = ",".join(str(i) for i in items_incorrectos)
    prompt = (
        f"items_incorrectos=[{items_str}] total={len(respuestas)}. "
        f"Confirma el conteo. Responde JSON."
    )
    respuesta = json.loads(proveedor.generar(prompt))
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": competencia,
                    "items_incorrectos": respuesta["items_incorrectos"],
                    "items_totales": respuesta["items_totales"],
                },
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
