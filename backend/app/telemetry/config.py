"""Configuración de la telemetría operativa (RFC-0007, alternativa 2).

Mismo esquema de nombres que lee el SDK instalado (`langsmith==0.8.4`,
`utils.get_env_var`, verificado leyendo el paquete real): namespace
`LANGSMITH_` con fallback a `LANGCHAIN_` por compatibilidad. No se
reimplementa nada del SDK aquí — solo se replica su misma precedencia
para decidir, sin importar `langsmith` todavía, si vale la pena hacerlo.
"""

from __future__ import annotations

import os


def _leer(nombre: str) -> str:
    return os.getenv(f"LANGSMITH_{nombre}") or os.getenv(f"LANGCHAIN_{nombre}") or ""


def _habilitado() -> bool:
    valor = _leer("TRACING_V2") or _leer("TRACING")
    return valor.strip().lower() == "true"


#: Único interruptor real. Si es False, ningún módulo de `telemetry/`
#: debe importar `langsmith` ni intentar red — todo se vuelve no-op.
HABILITADO = _habilitado()

PROYECTO = _leer("PROJECT") or "upao-mas-edu-demo"
