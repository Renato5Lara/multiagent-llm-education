"""OpenAIProvider — primera implementación REAL de `LLMProvider` (M3 PR-1).

Sobre `llm_provider.con_reintentos` (infraestructura compartida): declara
aquí, y solo aquí, qué excepciones del SDK de OpenAI son transitorias.
Sin conocimiento de dominio — igual que cualquier `FakeLLMProvider`, el
runtime no distingue si `generar()` vino de una tabla estática o de una
llamada de red (P13).

Modo JSON: por defecto usa `response_format={"type": "json_object"}`
(obliga a que la respuesta sea JSON válido, no a que tenga una forma
particular — la validación de campos sigue siendo responsabilidad de
`ejecutar_roundtrip`, última línea de defensa). Cuando una capacidad
declare un JSON Schema propio, `esquema` activa Structured Outputs sin
cambiar esta clase — el diseño ya lo admite, aunque ninguna capacidad lo
usa todavía (PR-1 no inventa esquemas que nadie pidió).
"""

from __future__ import annotations

import os
import time
from typing import Any, Mapping

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)

from runtime.domain.shared.llm import LLMResponse
from runtime.domain.shared.llm_provider import con_reintentos

load_dotenv()

_TRANSITORIAS: tuple[type[Exception], ...] = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    InternalServerError,
)


class OpenAIProvider:
    """`version` identifica esta implementación de proveedor (mecanismo
    de obtención, RFC-0007 H5) — no el snapshot del modelo, que OpenAI no
    garantiza estable entre llamadas; `modelo` es el nombre solicitado.

    `temperature=0` por defecto (M3 PR-2, hallazgo empírico): con
    temperature por defecto de la API, Diagnosticar-LLM contradecía la
    política scoring-v1 de forma no reproducible entre llamadas
    idénticas. Sobrescribible por capacidad/experimento; ninguna lo hace
    todavía."""

    version = "openai-chat-v1"

    def __init__(
        self,
        modelo: str = "gpt-4o-mini",
        *,
        api_key: str | None = None,
        esquema: Mapping[str, Any] | None = None,
        cliente: OpenAI | None = None,
        intentos: int = 3,
        temperature: float = 0,
    ):
        self.modelo = modelo
        self._esquema = esquema
        self._intentos = intentos
        self._temperature = temperature
        self._cliente = cliente or OpenAI(
            api_key=api_key or os.environ["OPENAI_API_KEY"]
        )

    def generar(self, prompt: str) -> LLMResponse:
        def _llamar() -> LLMResponse:
            inicio = time.monotonic()
            response_format: Mapping[str, Any] = (
                {"type": "json_schema", "json_schema": self._esquema}
                if self._esquema is not None
                else {"type": "json_object"}
            )
            respuesta = self._cliente.chat.completions.create(
                model=self.modelo,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_format,
                temperature=self._temperature,
            )
            latencia_ms = (time.monotonic() - inicio) * 1000
            eleccion = respuesta.choices[0]
            uso = (
                {
                    "prompt_tokens": respuesta.usage.prompt_tokens,
                    "completion_tokens": respuesta.usage.completion_tokens,
                    "total_tokens": respuesta.usage.total_tokens,
                }
                if respuesta.usage is not None
                else None
            )
            return LLMResponse(
                texto=eleccion.message.content,
                usage=uso,
                latencia_ms=latencia_ms,
                finish_reason=eleccion.finish_reason,
            )

        return con_reintentos(
            _llamar,
            excepciones_transitorias=_TRANSITORIAS,
            intentos=self._intentos,
        )
