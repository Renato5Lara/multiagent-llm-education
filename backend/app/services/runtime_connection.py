"""Conexión compartida de `app/` hacia el runtime (ADR-0009 §2.4, §6).

Único lugar que abre `AlmacenTransiciones`/`AlmacenMemoria` — cualquier
módulo de `app/` que necesite invocar `runtime.boundary` reutiliza
`almacenes()`, nunca abre su propia instancia (ADR-0009 §5 criterio 2).
"""

from __future__ import annotations

import os
from functools import lru_cache

from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones

#: Baseline fijo hasta que `runtime/policy/` formalice el versionado de
#: política y banco (Épica 5, RFC-0006). No existe todavía un catálogo
#: real entre el cual elegir — inventar un contrato para elegirlo
#: fabricaría una capacidad inexistente (ADR-0009 §4, límite explícito).
VERSION_BANCO = "v1"
VERSION_POLITICA = "v2"
SPEC_VERSION = "foundation-2026-07-10"

@lru_cache(maxsize=1)
def almacenes() -> tuple[AlmacenTransiciones, AlmacenMemoria]:
    """Perezosa (primer uso, no import de este módulo): igual que el
    resto de la app, Postgres solo se exige a quien de verdad ejecuta
    una petición — importar un módulo que use el runtime no debe exigir
    Postgres arriba (evita romper la colección de tests que no lo
    tocan, p. ej. los que usan SQLite). Sin estado mutable propio (cada
    método abre y cierra su propia conexión psycopg2): compartir la
    instancia entre requests concurrentes del threadpool de FastAPI es
    seguro.

    Las variables de entorno se leen aquí dentro, no a nivel de módulo:
    `app.services.runtime_connection` se importa (vía `app.main`) mucho
    antes de que un test pueda hacer `monkeypatch.setenv(...)` — leerlas
    al importar las habría fijado permanentemente al valor por defecto,
    ignorando cualquier override posterior (bug real encontrado en la
    Épica 2: los tests de `/api/runtime/*` "aislaban" un esquema
    temporal que nunca se usaba de verdad, y el esquema real
    `runtime` acumulaba sesiones de prueba entre corridas)."""
    url = os.environ.get(
        "RUNTIME_DATABASE_URL",
        "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
    )
    esquema = os.environ.get("RUNTIME_DATABASE_SCHEMA", "runtime")
    almacen = AlmacenTransiciones(url, esquema=esquema)
    almacen_memoria = AlmacenMemoria(url, esquema=esquema)
    almacen.preparar()
    almacen_memoria.preparar()
    return almacen, almacen_memoria
