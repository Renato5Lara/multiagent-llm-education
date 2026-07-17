"""S3 — `consultar_replay`: lee el estado acumulado por transición de una
sesión sin registrar ningún hecho nuevo (RFC-0010 regla 2; RFC-0008 §3).

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.boundary import (
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    consultar_replay,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.kernel.state.entries import OrigenProvenance

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
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0005 §3 exige BD real)"
)


def _peticion_abrir(session_id: str, student_id: str = "maria") -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id=student_id,
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_s3_replay_test_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def almacen(esquema):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    return almacen


@pytest.fixture
def almacen_memoria(esquema):
    almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
    almacen_memoria.preparar()
    return almacen_memoria


class TestS3_ConsultarReplay:
    def test_sesion_nueva_sin_evidencia_es_replay_vacio(self, almacen, almacen_memoria):
        replay = consultar_replay(_peticion_abrir("s-s3-replay-nueva"), almacen, almacen_memoria)
        assert replay == ()

    def test_no_registra_ningun_hecho_nuevo(self, almacen, almacen_memoria):
        consultar_replay(_peticion_abrir("s-s3-replay-sin-escribir"), almacen, almacen_memoria)
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-replay-sin-escribir"), almacen, almacen_memoria
        )
        assert almacen.leer(identidad.session_id) == ()

    def test_replay_es_acumulado_y_creciente_por_transicion(self, almacen, almacen_memoria):
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-replay-con-evidencia"), almacen, almacen_memoria
        )
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )

        replay = consultar_replay(
            _peticion_abrir("s-s3-replay-con-evidencia"), almacen, almacen_memoria
        )
        registros = almacen.leer(identidad.session_id)

        assert len(replay) == len(registros)
        assert tuple(paso.transicion for paso in replay) == tuple(
            registro.transicion for registro in registros
        )
        # Cada paso solo puede acumular entradas, nunca perderlas: el
        # conteo de facts+claims+deliberaciones+decisiones no decrece.
        conteos = [
            len(p.estado.facts) + len(p.estado.claims)
            + len(p.estado.deliberaciones) + len(p.estado.decisiones)
            for p in replay
        ]
        assert conteos == sorted(conteos)
        assert conteos[-1] > 0
        # El último paso coincide con el estado final real de la sesión.
        assert replay[-1].estado.transicion == len(registros)

    def test_es_idempotente_no_duplica_transiciones(self, almacen, almacen_memoria):
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-replay-idempotente"), almacen, almacen_memoria
        )
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-2", "items_incorrectos": [1, 2]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )
        antes = len(almacen.leer(identidad.session_id))
        consultar_replay(_peticion_abrir("s-s3-replay-idempotente"), almacen, almacen_memoria)
        consultar_replay(_peticion_abrir("s-s3-replay-idempotente"), almacen, almacen_memoria)
        assert len(almacen.leer(identidad.session_id)) == antes
