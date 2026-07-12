"""Regresión (Épica 2): `enrutar()` entraba en loop infinito cuando una
interpretación de Diagnosticar decía `dominada=True` — `remediar.
producir()` no propone nada en ese caso, y sin guardia el router volvía
a enrutar a "remediar" indefinidamente hasta el `recursion_limit` de
LangGraph. Descubierto al conectar `runtime_bridge` con evidencia real
(<2 errores, el caso más común y deseable).

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad
from runtime.kernel.transitions import TransitionIntent

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
    not _pg_disponible(), reason="PostgreSQL no disponible"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _hecho_dominado() -> tuple[TransitionIntent, ...]:
    """1 error: por debajo de `_UMBRAL_ERRORES = 2` (diagnosticar) —
    la interpretación resultante dirá `dominada=True`."""
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_fix_remediar_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


def test_dominada_true_no_produce_recursion_error(esquema):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()

    # Antes del fix: esto lanzaba GraphRecursionError.
    final = ejecutar_walkthrough(almacen, _identidad("s-dominada"), _hecho_dominado())
    estado = final["estado"]

    interpretacion = next(
        c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
    )
    assert interpretacion.afirmacion["dominada"] is True

    # Remediar no tenía nada que proponer — no debe aparecer.
    assert not any(c.autor is Capacidad.REMEDIAR for c in estado.claims)

    # Orientar sí propone (su contrato no depende de dominada).
    orientacion = next(c for c in estado.claims if c.autor is Capacidad.ORIENTAR)
    assert orientacion.afirmacion["accion"] == "avanzar-con-andamiaje"


def test_dominada_false_preserva_el_comportamiento_original(esquema):
    # No-regresión: el camino ya probado (≥2 errores) sigue igual.
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    hecho = (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [1, 2]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )
    final = ejecutar_walkthrough(almacen, _identidad("s-no-dominada"), hecho)
    estado = final["estado"]
    interpretacion = next(
        c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
    )
    assert interpretacion.afirmacion["dominada"] is False
    remediacion = next(c for c in estado.claims if c.autor is Capacidad.REMEDIAR)
    assert remediacion.afirmacion["accion"] == "reforzar"
