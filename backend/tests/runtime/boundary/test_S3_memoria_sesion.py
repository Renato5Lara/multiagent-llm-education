"""S3 — `consultar_memoria`: lee la versión de memoria que la sesión ya
tiene fijada (INV-1/INV-2), nunca "la más reciente" (RFC-0010 regla 2;
RFC-0005 §2).

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
    consultar_memoria,
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


def _peticion_abrir(session_id: str, student_id: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id=student_id,
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_s3_memoria_test_{os.getpid()}"
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


class TestS3_ConsultarMemoria:
    def test_estudiante_sin_memoria_consolidada_es_N0(self, almacen, almacen_memoria):
        memoria = consultar_memoria(
            _peticion_abrir("s-s3-memoria-nueva", "estudiante-sin-historia"),
            almacen,
            almacen_memoria,
        )
        assert memoria is None

    def test_no_registra_ningun_hecho_nuevo(self, almacen, almacen_memoria):
        consultar_memoria(
            _peticion_abrir("s-s3-memoria-sin-escribir", "otro-estudiante"),
            almacen,
            almacen_memoria,
        )
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-memoria-sin-escribir", "otro-estudiante"),
            almacen,
            almacen_memoria,
        )
        assert almacen.leer(identidad.session_id) == ()

    def test_sesion_nueva_lee_la_version_consolidada_por_la_sesion_previa(
        self, almacen, almacen_memoria
    ):
        student_id = "estudiante-con-historia"

        identidad_previa = abrir_sesion(
            _peticion_abrir("s-s3-memoria-previa", student_id), almacen, almacen_memoria
        )
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad_previa,
                contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                origen=OrigenProvenance.INSTRUMENTO,
                cerrar_sesion=True,
            ),
            almacen,
            almacen_memoria,
        )

        # Nueva sesión del MISMO estudiante: INV-1 fija version_student_model
        # a la que acaba de consolidarse (numero_version_vigente).
        memoria = consultar_memoria(
            _peticion_abrir("s-s3-memoria-siguiente", student_id), almacen, almacen_memoria
        )

        assert memoria is not None
        assert memoria.student_id == student_id
        assert memoria.session_id == "s-s3-memoria-previa"
        assert memoria.catalogo  # RFC-0005 §2: el catálogo de proyectar_salidas
