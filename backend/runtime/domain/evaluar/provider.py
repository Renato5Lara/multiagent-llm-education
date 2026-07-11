"""FakeLLMProvider de Evaluar — determinista, sin red (ADR-0005 §3).

A diferencia de Diagnosticar/Remediar/Orientar, aquí el proveedor no
"interpreta" nada nuevo: confirma un conteo ya determinado por las
respuestas crudas, a través de un round-trip de prompt/respuesta — el
mismo resultado que la regla, por un camino distinto (P13).
"""

from __future__ import annotations

import re

from runtime.domain.shared.llm import LLMProvider, LLMResponse

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: recalcula el conteo leyéndolo del propio prompt."""

    modelo = "fake-evaluacion-v1"
    version = "1"

    def generar(self, prompt: str) -> LLMResponse:
        incorrectos = re.search(r"son \[([\d,]*)\]", prompt)
        total = re.search(r"total de (\d+) preguntas", prompt)
        lista = (
            [int(n) for n in incorrectos.group(1).split(",") if n]
            if incorrectos
            else []
        )
        return LLMResponse(
            texto=(
                f'{{"items_incorrectos": {lista}, '
                f'"items_totales": {int(total.group(1)) if total else 0}, '
                f'"razonamiento": "conteo confirmado por revisión ítem a ítem"}}'
            )
        )
