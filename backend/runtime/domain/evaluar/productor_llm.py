"""Productor de Evaluar — versión LLM (provenance `llm`).

Mismo contrato que la versión regla: mismo tipo de intent
(`registrar_fact`), mismas claves de `contenido` — únicamente cambia CÓMO
se confirma el conteo (P13). El proveedor no decide qué está incorrecto:
eso ya lo determinan `respuestas` (P12); solo confirma el resultado a
través de un round-trip de prompt.

A diferencia de Diagnosticar/Remediar/Orientar (donde el LLM aporta una
interpretación que se registra como claim), aquí el LLM no aporta
conocimiento nuevo: el fact es una observación objetiva (RFC-0003 §1,
"un fact solo puede ser cuestionado por un nuevo fact — nunca por una
opinión"). Por eso el roundtrip valida que el proveedor responde con la
forma esperada, pero el `contenido` del fact se construye siempre con
los valores deterministas ya calculados — nunca con lo que el modelo
devuelve.
"""

from __future__ import annotations

from typing import Mapping

from runtime.domain.evaluar.provider import FakeLLMProvider, LLMProvider
from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip
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
    items_totales = len(respuestas)
    prompt = (
        f"El sistema calculó que los ítems incorrectos son "
        f"[{items_str}] de un total de {items_totales} preguntas "
        f"respondidas. Confirma esta observación. Responde JSON con esta "
        f'forma EXACTA y en este ORDEN: primero "razonamiento" (por qué '
        f'el conteo es consistente), luego "items_incorrectos" (ARRAY de '
        f"enteros, debe ser exactamente [{items_str}]), luego "
        f'"items_totales" (INTEGER, debe ser exactamente {items_totales} '
        f"— el total de preguntas respondidas, no la cantidad de "
        f"incorrectas)."
    )
    # El roundtrip solo verifica que el proveedor responde con la forma
    # esperada; el contenido del fact nunca proviene de esta respuesta
    # (ver docstring del módulo — el LLM confirma, no calcula).
    ejecutar_roundtrip(
        proveedor, prompt, campos_requeridos=("items_incorrectos", "items_totales")
    )
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": competencia,
                    "items_incorrectos": items_incorrectos,
                    "items_totales": items_totales,
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
