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
from typing import Any, Callable, Mapping

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

#: Punto de extensión para telemetría OPERATIVA (RFC-0007, alternativa 2 —
#: latencia/tokens dependen del reloj de pared, excluidos a propósito del
#: registro científico). `runtime/` nunca importa `app/`: quien quiera
#: observar estas llamadas se registra aquí desde afuera (`app/telemetry`,
#: cableado en el arranque de la aplicación). Por defecto no hay ninguno —
#: no-op total, cero costo, cero import de `langsmith`.
ObservadorLLM = Callable[[str, LLMResponse | None, BaseException | None, float], None]
_observador: ObservadorLLM | None = None


def establecer_observador_llm(observador: ObservadorLLM | None) -> None:
    """Registra (o quita) el observador de telemetría operativa. Nunca es
    consultado por la lógica de dominio; es una notificación unidireccional
    y fire-and-forget — jamás puede alterar el resultado de `generar()`."""
    global _observador
    _observador = observador


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

        inicio_total = time.monotonic()
        try:
            respuesta = con_reintentos(
                _llamar,
                excepciones_transitorias=_TRANSITORIAS,
                intentos=self._intentos,
            )
        except Exception as error:
            self._notificar_observador(None, error, inicio_total)
            raise
        self._notificar_observador(respuesta, None, inicio_total)
        return respuesta

    def _notificar_observador(
        self,
        respuesta: LLMResponse | None,
        error: BaseException | None,
        inicio_total: float,
    ) -> None:
        if _observador is None:
            return
        try:
            _observador(
                self.modelo, respuesta, error, (time.monotonic() - inicio_total) * 1000
            )
        except Exception:
            # Telemetria operativa: un fallo del observador jamas debe
            # afectar al runtime (garantia dura, no solo intencion).
            pass
