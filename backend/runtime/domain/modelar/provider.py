"""FakeLLMProvider de Modelar — determinista, sin red (ADR-0005 §3).

El veredicto (funcionó / no) ya lo determinó Validar; el proveedor solo
interpreta qué implica para el modelo del estudiante — el mismo juicio
que la regla, por un camino distinto (P13).
"""

from __future__ import annotations

from runtime.domain.shared.llm import LLMProvider

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: espeja el veredicto de Validar sin reinterpretarlo."""

    modelo = "fake-modelado-v1"
    version = "1"

    def generar(self, prompt: str) -> str:
        efecto_positivo = "true" if "funciono=true" in prompt else "false"
        return (
            f'{{"efecto_positivo": {efecto_positivo}, "confianza": "0.80", '
            f'"razonamiento": "modelo actualizado a partir del veredicto de Validar"}}'
        )
