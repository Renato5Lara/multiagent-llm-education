"""Cablea la telemetría operativa al arrancar la aplicación (RFC-0007,
alternativa 2). Único lugar donde `app/` "alcanza hacia adentro" de
`runtime/` para registrar el observador — `runtime/` en sí no importa
nada de `app/` (ver `runtime/domain/shared/llm_openai.py`).

Llamar una sola vez, en `app/main.py`, al arrancar. Si la telemetría está
deshabilitada, no hace nada (ni siquiera importa `langsmith`).
"""

from __future__ import annotations

from app.telemetry.config import HABILITADO


def inicializar() -> None:
    if not HABILITADO:
        return
    from runtime.domain.shared import llm_openai

    from app.telemetry.spans_operativos import registrar_llamada_llm

    llm_openai.establecer_observador_llm(registrar_llamada_llm)
