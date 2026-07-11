"""FakeLLMProvider de Tutorizar — determinista, sin red (ADR-0005 §3).

Fact-producer (como Evaluar): la respuesta NO lleva `confianza` — ese
campo es exclusivo de los claims (INV-5); un fact no lo tiene.
"""

from __future__ import annotations

import re

from runtime.domain.shared.llm import LLMProvider, LLMResponse

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: la misma clasificación que la regla, por un camino distinto."""

    modelo = "fake-tutoria-v1"
    version = "1"

    def generar(self, prompt: str) -> LLMResponse:
        incorrectos = re.search(r"incorrectos=(\d+)", prompt)
        total = re.search(r"total=(\d+)", prompt)
        n_incorrectos = int(incorrectos.group(1)) if incorrectos else 0
        n_total = int(total.group(1)) if total else 1
        if n_incorrectos == 0:
            senal = "fluidez"
        elif n_incorrectos == n_total:
            senal = "frustracion"
        else:
            senal = "confusion"
        return LLMResponse(texto=f'{{"senal": "{senal}"}}')
