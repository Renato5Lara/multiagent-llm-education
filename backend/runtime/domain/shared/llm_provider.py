"""Infraestructura común a proveedores LLM REALES (M3).

Sin conocimiento de ningún proveedor concreto (OpenAI, Claude, Ollama...):
cada implementación declara qué excepciones de SU PROPIO SDK son
transitorias. Esto es lo que varios proveedores reales comparten de
verdad — timeout/reintentos — a diferencia de `FakeLLMProvider`, cuya
lógica de "cómo interpretar el prompt" sí es específica de cada
capacidad (ver `llm.py`).

Clasificación ADR-0004: una falla transitoria de red es E-3
(infraestructura) — se reintenta un número acotado de veces y, si
persiste, se propaga tal cual (jamás se disfraza de rechazo de dominio
E-1, jamás se silencia E-4).
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")


def con_reintentos(
    llamar: Callable[[], T],
    *,
    excepciones_transitorias: tuple[type[Exception], ...],
    intentos: int = 3,
    espera_base_s: float = 1.0,
) -> T:
    """Reintenta `llamar` ante fallas transitorias, con backoff exponencial.

    Cualquier excepción fuera de `excepciones_transitorias` (credenciales
    inválidas, prompt rechazado, etc.) se propaga en el primer intento —
    no es una falla de red, es un error real que reintentar no arregla.
    """
    ultimo_error: Exception | None = None
    for intento in range(intentos):
        try:
            return llamar()
        except excepciones_transitorias as error:
            ultimo_error = error
            if intento < intentos - 1:
                time.sleep(espera_base_s * (2**intento))
    assert ultimo_error is not None
    raise ultimo_error
