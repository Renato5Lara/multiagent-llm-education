"""FakeLLMProvider de Adaptar — determinista, sin red (ADR-0005 §3).

El proveedor propone modalidad/profundidad/alternativas EN CATEGORÍAS
PEDAGÓGICAS — jamás recursos físicos, IDs de contenido ni URLs. Esa
frontera pertenece al Boundary (RFC-0010), no al dominio.
"""

from __future__ import annotations

from runtime.domain.shared.llm import LLMProvider

__all__ = ["LLMProvider", "FakeLLMProvider"]


class FakeLLMProvider:
    """Determinista: mismo criterio que la regla, por un camino distinto."""

    modelo = "fake-adaptacion-v1"
    version = "1"

    def generar(self, prompt: str) -> str:
        if "accion=reforzar" in prompt:
            return (
                '{"modalidad": "visual", "profundidad": "fundamentos", '
                '"alternativas_descartadas": ['
                '{"modalidad": "textual", "razon": "ya insuficiente en el intento anterior"}, '
                '{"modalidad": "ejemplo-codigo", "razon": "prematuro sin el concepto consolidado"}'
                '], "confianza": "0.80"}'
            )
        return (
            '{"modalidad": "mixta", "profundidad": "aplicacion", '
            '"alternativas_descartadas": ['
            '{"modalidad": "solo-texto", "razon": "el andamiaje requiere apoyo visual"}'
            '], "confianza": "0.75"}'
        )
