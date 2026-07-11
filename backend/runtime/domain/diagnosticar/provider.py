"""LLMProvider — la interfaz que aísla la capacidad del proveedor concreto.

Interior libre de la capacidad (P13, RFC-0004 §4): el runtime no conoce
esta interfaz, solo ve `TransitionIntent`s. Sustituir el proveedor
(fake → OpenAI → Anthropic) no toca el Kernel, el Engine, los reducers ni
el grafo — es exactamente la propiedad que el guardián de P13 verifica
(ADR-0005 §7).

`FakeLLMProvider` es determinista y no llama a ninguna API: cero costo,
cero red, cero credenciales (ADR-0005 §3 — la capacidad puede doblar el
LLM en sus tests; aquí, además, en su implementación de desarrollo).
"""

from __future__ import annotations

import re
from typing import Protocol


class LLMProvider(Protocol):
    """Contrato mínimo: un prompt entra, texto sale."""

    modelo: str
    version: str

    def generar(self, prompt: str) -> str: ...


class FakeLLMProvider:
    """Determinista: misma pregunta, misma respuesta — siempre.

    No razona; espeja la regla de scoring-v1 leyendo el prompt, para que
    el guardián de P13 pueda comparar el CONTRATO producido por dos
    caminos de implementación distintos sin depender de una red externa.
    """

    modelo = "fake-diagnostico-v1"
    version = "1"

    def generar(self, prompt: str) -> str:
        # Texto plano con forma de JSON — imita la respuesta de una API
        # externa; no es serialización del runtime (ADR-0001/ADR-0005
        # §5: json.dumps queda reservado a canonical.py, no a esto).
        match = re.search(r"items_incorrectos=(\d+)", prompt)
        errores = int(match.group(1)) if match else 0
        dominada = "true" if errores < 2 else "false"
        return (
            f'{{"dominada": {dominada}, "errores": {errores}, '
            f'"confianza": "0.80", '
            f'"razonamiento": "{errores} ítem(s) incorrecto(s) detectado(s)"}}'
        )
