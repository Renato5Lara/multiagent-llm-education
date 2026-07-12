"""S3 — `consultar_estado`: lee el LearningState completo de una sesión
sin registrar ningún hecho nuevo (RFC-0010 regla 2; RFC-0002 §1).

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
    consultar_estado,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.kernel.state.entries import Capacidad
from runtime.kernel.state.state import LearningState
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
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_s3_estado_test_{os.getpid()}"
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


class TestS3_ConsultarEstado:
    def test_sesion_nueva_sin_evidencia_es_estado_vacio(self, almacen, almacen_memoria):
        estado = consultar_estado(_peticion_abrir("s-s3-estado-nueva"), almacen, almacen_memoria)
        assert isinstance(estado, LearningState)
        assert estado.facts == ()
        assert estado.claims == ()
        assert estado.transicion == 0

    def test_no_registra_ningun_hecho_nuevo(self, almacen, almacen_memoria):
        consultar_estado(_peticion_abrir("s-s3-estado-sin-escribir"), almacen, almacen_memoria)
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-estado-sin-escribir"), almacen, almacen_memoria
        )
        assert almacen.leer(identidad.session_id) == ()

    def test_refleja_facts_y_claims_de_un_hecho_previo(self, almacen, almacen_memoria):
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-estado-con-evidencia"), almacen, almacen_memoria
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

        estado = consultar_estado(
            _peticion_abrir("s-s3-estado-con-evidencia"), almacen, almacen_memoria
        )
        assert len(estado.facts) == 1
        assert estado.facts[0].autor == "boundary"
        assert any(c.autor is Capacidad.ADAPTAR for c in estado.claims)
        assert estado.transicion == len(almacen.leer(identidad.session_id))
