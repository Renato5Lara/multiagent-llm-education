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

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True, slots=True)
class LLMResponse:
    """Respuesta cruda de un proveedor (M3): `texto` es lo único que
    `ejecutar_roundtrip` interpreta hoy; `usage`/`latencia_ms`/
    `finish_reason` quedan disponibles para observabilidad futura
    (RFC-0007 H5: "método de obtención" en provenance) SIN que ninguna
    capacidad los lea todavía — no persisten en el estado, no son
    Domain Events (telemetría operativa, no evidencia)."""

    texto: str
    usage: Mapping[str, int] | None = None
    latencia_ms: float | None = None
    finish_reason: str | None = None


class LLMProvider(Protocol):
    """Contrato mínimo: un prompt entra, una `LLMResponse` sale."""

    modelo: str
    version: str

    def generar(self, prompt: str) -> LLMResponse: ...
