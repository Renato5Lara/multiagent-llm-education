"""LLMProvider — la interfaz que aísla una capacidad del proveedor
concreto (compartida entre capacidades; P3 prohíbe que se importen entre
sí, no que compartan un contrato genérico).

Interior libre de la capacidad (P13, RFC-0004 §4): el runtime no conoce
esta interfaz, solo ve `TransitionIntent`s. Sustituir el proveedor
(fake → OpenAI → Anthropic) no toca el Kernel, el Engine, los reducers ni
el grafo — es exactamente la propiedad que el guardián de P13 verifica
(ADR-0005 §7).

Cada capacidad implementa su propio `FakeLLMProvider` (la lógica de
"cómo interpretar el prompt" es específica del dominio de esa capacidad);
lo único compartido es el contrato.
"""

from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    """Contrato mínimo: un prompt entra, texto sale."""

    modelo: str
    version: str

    def generar(self, prompt: str) -> str: ...
