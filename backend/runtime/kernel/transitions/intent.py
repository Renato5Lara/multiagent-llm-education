"""TransitionIntent — el deseo de transicionar, aún sin autoridad
(RFC-0004 §1, regla de autoridad).

Un intent es un dato, no un actor: no expone ninguna operación de
aplicación. La autoridad de mutar pertenece exclusivamente al Kernel,
mediante los reducers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from runtime.kernel.state.entries import Capacidad


@dataclass(frozen=True, slots=True)
class TransitionIntent:
    """{productor, entradas, base} del RFC-0004: `operacion` nombra el
    reducer destino y `argumentos` son las entradas propuestas."""

    productor: Capacidad | str  # capacidad, boundary o kernel (deliberaciones)
    operacion: str
    argumentos: Mapping[str, Any]
    base: int  # versión del estado que el productor leyó (observabilidad)
