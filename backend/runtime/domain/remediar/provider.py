"""FakeLLMProvider de Remediar — determinista, sin red (ADR-0005 §3).

El contrato `LLMProvider` es compartido (domain/shared/llm.py). El
disparador (competencia no dominada) ya lo decidió el productor antes de
llamar al proveedor — la respuesta del modelo aquí solo aporta la
justificación, no la decisión de invocar.
"""

from __future__ import annotations

from runtime.domain.shared.llm import LLMProvider, LLMResponse

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: siempre recomienda reforzar cuando se le consulta
    (el productor solo consulta cuando ya hay una brecha detectada)."""

    modelo = "fake-remediacion-v1"
    version = "1"

    def generar(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            texto=(
                '{"accion": "reforzar", "confianza": "0.85", '
                '"razonamiento": "brecha detectada antes de avanzar de tema"}'
            )
        )
