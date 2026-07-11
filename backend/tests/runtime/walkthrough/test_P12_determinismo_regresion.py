"""Regresión de determinismo del scheduler (P12, A3).

No es un RFC ni un ADR: es la red que detecta cualquier cambio futuro que
introduzca un orden accidental distinto (recomendación del tesista,
2026-07-11). Dos amenazas, dos pruebas:

* ``test_...en_proceso...``: 100 ejecuciones en el mismo proceso →
  atrapa no-determinismo por reloj, azar o uuid (A3).
* ``test_...bajo_hashseed...``: la MISMA historia bajo semillas de hash
  distintas (subprocesos) → atrapa una dependencia accidental del orden
  de un ``set``/``dict`` en el enrutamiento, que un solo proceso jamás
  revelaría.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
)
from runtime.kernel.state.state import Identidad
from runtime.kernel.transitions import TransitionIntent

_BACKEND = Path(__file__).resolve().parents[3]
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


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-det",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _hecho() -> tuple[TransitionIntent, ...]:
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )


def _firma(registros) -> list:
    return [(r.transicion, r.hash) for r in registros]


def _reiniciar(esquema: str) -> None:
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"SET search_path TO {esquema}")
        cursor.execute("TRUNCATE runtime_transitions, runtime_sessions")


@pytest.fixture
def esquema():
    nombre = f"runtime_det_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


class TestP12_RegresionDeterminismo:
    def test_cien_ejecuciones_en_proceso_identicas(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        referencia = None
        for _ in range(100):
            _reiniciar(esquema)
            final = ejecutar_walkthrough(almacen, _identidad(), _hecho())
            firma = _firma(final["registros"])
            decision = final["estado"].decisiones[0]
            marca = (firma, decision.contenido["accion"], str(decision.confianza))
            if referencia is None:
                referencia = marca
            else:
                assert marca == referencia
        assert referencia is not None
        assert len(referencia[0]) == 7  # siete transiciones, siempre (PR-5: +Adaptar)


_SCRIPT = textwrap.dedent(
    """
    import json, os, sys
    sys.path.insert(0, os.environ["RUNTIME_BACKEND"])
    import psycopg2
    from runtime.engine.checkpoint import AlmacenTransiciones
    from runtime.engine.graph import ejecutar_walkthrough
    from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance
    from runtime.kernel.state.state import Identidad
    from runtime.kernel.transitions import TransitionIntent

    url, esquema = os.environ["RUNTIME_URL"], os.environ["RUNTIME_ESQUEMA"]
    identidad = Identidad(
        session_id="s-det", student_id="maria", version_student_model="v7",
        version_banco="banco-v2", version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )
    hecho = (TransitionIntent(
        productor=Capacidad.EVALUAR, operacion="registrar_fact",
        argumentos={"autor": Capacidad.EVALUAR,
            "contenido": {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2")},
        base=0),)
    almacen = AlmacenTransiciones(url, esquema=esquema)
    almacen.preparar()
    final = ejecutar_walkthrough(almacen, identidad, hecho)
    print(json.dumps([[r.transicion, r.hash] for r in final["registros"]]))
    """
)


class TestP12_DeterminismoBajoHashSeed:
    def test_la_misma_historia_bajo_semillas_distintas(self, esquema):
        firmas = []
        for indice, semilla in enumerate(("0", "1", "42", "123456789")):
            sub_esquema = f"{esquema}_{indice}"
            entorno = dict(
                os.environ,
                PYTHONHASHSEED=semilla,
                RUNTIME_BACKEND=str(_BACKEND),
                RUNTIME_URL=_URL,
                RUNTIME_ESQUEMA=sub_esquema,
            )
            try:
                salida = subprocess.run(
                    [sys.executable, "-c", _SCRIPT],
                    env=entorno,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                assert salida.returncode == 0, salida.stderr
                firmas.append(salida.stdout.strip())
            finally:
                with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
                    cursor.execute(f"DROP SCHEMA IF EXISTS {sub_esquema} CASCADE")
        # Cuatro semillas de hash, una sola historia: el enrutamiento no
        # depende del orden de ningún set/dict (P12).
        assert len(set(firmas)) == 1
