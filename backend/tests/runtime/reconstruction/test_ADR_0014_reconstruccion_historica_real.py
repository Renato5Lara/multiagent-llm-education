"""ADR-0014 — regresión encontrada por validación funcional E2E real
(RuntimeConsole, docente, navegador real, 2026-08-04): reconstruir una
sesión REAL de Postgres con transiciones de deliberación anteriores a
este commit fallaba con `HTTP 500` ("R3: ... no reconstruye bit a
bit"). Causa: `canonical.py::_plano()` serializaba `Resuelta.margen`/
`Aplazada.margen` en `None` como `"margen":null` al re-canonicalizar
durante la reconstrucción — el bytes original (escrito antes de
ADR-0014) nunca tuvo esa clave.

Esta suite NO usa un esquema de prueba aislado (a diferencia del resto
de `tests/runtime/reconstruction/`) — apunta deliberadamente al esquema
`runtime` real, en modo SOLO LECTURA (`AlmacenTransiciones.leer`,
jamás `.persistir`), porque el defecto que reproduce solo existe contra
bytes genuinamente anteriores al cambio. Ninguna entidad real se muta
(feedback_never_mutate_real_entities_for_e2e).
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones, reconstruir_con_traza

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0014 exige BD real)"
)


def _sesion_con_deliberacion_mas_antigua() -> str | None:
    """La sesión real con más transiciones que contenga al menos una
    `registrar_deliberacion` — maximiza la probabilidad de tocar una
    transición escrita antes de ADR-0014 sin depender de una fecha
    hardcodeada (la base de datos de desarrollo puede resetearse)."""
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "SELECT session_id, count(*) FROM runtime.runtime_transitions"
            " WHERE convert_from(canonico, 'UTF8') LIKE '%\"operacion\":"
            "\"registrar_deliberacion\"%'"
            " GROUP BY session_id ORDER BY count(*) DESC LIMIT 1"
        )
        fila = cursor.fetchone()
        return fila[0] if fila else None


class TestReconstruccionHistoricaReal:
    def test_sesion_real_con_deliberaciones_reconstruye_sin_error(self):
        session_id = _sesion_con_deliberacion_mas_antigua()
        if session_id is None:
            pytest.skip(
                "sin sesiones reales con deliberación en esta base de datos "
                "(entorno recién sembrado, no es una falla de ADR-0014)"
            )

        almacen = AlmacenTransiciones(_URL, esquema="runtime")
        identidad = almacen.identidad_existente(session_id)
        assert identidad is not None
        registros = almacen.leer(session_id)
        assert len(registros) > 0

        # No debe lanzar RuntimeError("R3: ... no reconstruye bit a bit").
        estado, traza = reconstruir_con_traza(identidad, {}, registros)

        assert estado.transicion == registros[-1].transicion
        assert len(traza) == len(registros)
