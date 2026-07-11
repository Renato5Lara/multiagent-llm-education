"""FakeLLMProvider de Orientar — determinista, sin red (ADR-0005 §3).

Igual que en Remediar: el disparador (existe una interpretación vigente)
ya lo decidió el productor antes de invocar al proveedor — la respuesta
del modelo solo aporta la justificación de avanzar.
"""

from __future__ import annotations

from runtime.domain.shared.llm import LLMProvider

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: siempre recomienda avanzar con andamiaje cuando se
    le consulta (el productor solo consulta si ya hay interpretación)."""

    modelo = "fake-orientacion-v1"
    version = "1"

    def generar(self, prompt: str) -> str:
        return (
            '{"accion": "avanzar-con-andamiaje", "confianza": "0.78", '
            '"razonamiento": "la ruta ya prevé soporte adicional en el siguiente objetivo"}'
        )
