"""FakeLLMProvider de Diagnosticar — determinista, sin red (ADR-0005 §3).

El contrato `LLMProvider` es compartido (domain/shared/llm.py); esta
implementación es específica de Diagnosticar: espeja la regla de
scoring-v1 leyendo el prompt, para que el guardián de P13 pueda comparar
el CONTRATO producido por dos caminos de implementación distintos sin
depender de una API externa.
"""

from __future__ import annotations

import re

from runtime.domain.shared.llm import LLMProvider

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: misma pregunta, misma respuesta — siempre."""

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
