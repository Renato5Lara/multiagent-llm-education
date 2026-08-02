"""S3 — `consultar_consenso`: lee las métricas de consenso de una
sesión sin registrar ningún hecho nuevo (RFC-0010 regla 2; RFC-0007
§2.2, fila "Consenso").

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
    consultar_consenso,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones, MetricasConsenso
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
    nombre = f"runtime_s3_consenso_test_{os.getpid()}"
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


class TestS3_ConsultarConsenso:
    def test_sesion_nueva_sin_evidencia_es_consenso_vacio(self, almacen, almacen_memoria):
        metricas = consultar_consenso(
            _peticion_abrir("s-s3-consenso-nueva"), almacen, almacen_memoria
        )
        assert metricas == MetricasConsenso(
            convocatorias=0, no_convocatorias=0,
            resueltas=0, aplazadas=0, escaladas=0,
            margenes_resolucion=(), confianza_resolucion=(),
            longitud_cadenas_reconvocacion=(),
        )

    def test_no_registra_ningun_hecho_nuevo(self, almacen, almacen_memoria):
        consultar_consenso(_peticion_abrir("s-s3-consenso-sin-escribir"), almacen, almacen_memoria)
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-consenso-sin-escribir"), almacen, almacen_memoria
        )
        assert almacen.leer(identidad.session_id) == ()

    def test_consenso_es_forma_valida_con_evidencia_real(self, almacen, almacen_memoria):
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-consenso-con-evidencia"), almacen, almacen_memoria
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

        metricas = consultar_consenso(
            _peticion_abrir("s-s3-consenso-con-evidencia"), almacen, almacen_memoria
        )

        # `registrar_hecho` corre el walkthrough real (LLM real, ADR-0005
        # §3) — el contenido exacto no es lo que esta pieza verifica (eso
        # lo cubren los tests de dominio/deliberación); aquí solo la
        # forma de las métricas derivadas.
        assert metricas.convocatorias >= 0
        assert metricas.no_convocatorias >= 0
        assert metricas.resueltas + metricas.aplazadas + metricas.escaladas == metricas.convocatorias
        assert all(c >= 0 for c in metricas.confianza_resolucion)
        assert all(n > 0 for n in metricas.longitud_cadenas_reconvocacion)

    def test_es_idempotente_no_duplica_transiciones(self, almacen, almacen_memoria):
        identidad = abrir_sesion(
            _peticion_abrir("s-s3-consenso-idempotente"), almacen, almacen_memoria
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
        consultar_consenso(_peticion_abrir("s-s3-consenso-idempotente"), almacen, almacen_memoria)
        consultar_consenso(_peticion_abrir("s-s3-consenso-idempotente"), almacen, almacen_memoria)
        assert len(almacen.leer(identidad.session_id)) == antes
