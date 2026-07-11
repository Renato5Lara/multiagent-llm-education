"""FakeLLMProvider de Validar — determinista, sin red (ADR-0005 §3).

El conteo (antes/después) ya lo determinó el productor a partir del
estado (P12); el proveedor solo interpreta si esa diferencia cuenta como
mejora — el mismo juicio que la regla, por un camino distinto (P13).
"""

from __future__ import annotations

import re

from runtime.domain.shared.llm import LLMProvider

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: menos incorrectos después que antes ⇒ funcionó."""

    modelo = "fake-validacion-v1"
    version = "1"

    def generar(self, prompt: str) -> str:
        antes = re.search(r"antes=(\d+)", prompt)
        despues = re.search(r"despues=(\d+)", prompt)
        n_antes = int(antes.group(1)) if antes else 0
        n_despues = int(despues.group(1)) if despues else 0
        funciono = "true" if n_despues < n_antes else "false"
        return (
            f'{{"funciono": {funciono}, "confianza": "0.85", '
            f'"razonamiento": "errores {n_antes}\\u2192{n_despues}"}}'
        )
