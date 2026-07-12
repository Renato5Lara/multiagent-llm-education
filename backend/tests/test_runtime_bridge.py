"""Épica 2 — `runtime_bridge.registrar_evidencia_evaluacion`: el primer
puente real entre evidencia de evaluación de la plataforma y una
decisión del runtime LangGraph (ADR-0010).

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

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


@pytest.fixture(autouse=True)
def _runtime_env(monkeypatch):
    esquema = f"runtime_bridge_test_{os.getpid()}"
    monkeypatch.setenv("RUNTIME_DATABASE_URL", _URL)
    monkeypatch.setenv("RUNTIME_DATABASE_SCHEMA", esquema)
    from app.services.runtime_connection import almacenes

    almacenes.cache_clear()
    yield
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {esquema} CASCADE")
    almacenes.cache_clear()


def test_evidencia_de_evaluacion_produce_una_entrega_de_adaptar():
    from app.services.runtime_bridge import registrar_evidencia_evaluacion
    from runtime.boundary import Entrega

    entrega = registrar_evidencia_evaluacion(
        student_id="maria",
        course_id="fundamentos-programacion",
        titulo_modulo="Condicionales",
        items_incorrectos=[0, 2, 3],
    )
    assert isinstance(entrega, Entrega)
    assert entrega.asunto is not None
    assert entrega.diseno is not None


def test_competencia_registrada_es_el_slug_del_modulo_no_comp_n():
    from app.services.runtime_bridge import registrar_evidencia_evaluacion
    from runtime.engine.checkpoint import reconstruir
    from runtime.kernel.state.state import Identidad
    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )

    registrar_evidencia_evaluacion(
        student_id="maria",
        course_id="fundamentos-programacion",
        titulo_modulo="Bucles y Repetición",
        items_incorrectos=[1],
    )

    almacen, _ = almacenes()
    identidad = Identidad(
        session_id="curso:fundamentos-programacion:estudiante:maria",
        student_id="maria",
        version_student_model="0",
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )
    registros = almacen.leer(identidad.session_id)
    estado = reconstruir(identidad, {}, registros)
    fact = next(f for f in estado.facts if "items_incorrectos" in f.contenido)
    assert fact.contenido["competencia"] == "bucles-y-repeticion"


def test_dos_modulos_del_mismo_curso_comparten_la_misma_sesion_de_runtime():
    # session_id determinista por estudiante+curso (no por evaluación):
    # el runtime acumula evidencia de varios módulos en la misma sesión.
    from app.services.runtime_bridge import registrar_evidencia_evaluacion

    registrar_evidencia_evaluacion(
        student_id="juan", course_id="curso-x", titulo_modulo="Funciones",
        items_incorrectos=[],
    )
    entrega_2 = registrar_evidencia_evaluacion(
        student_id="juan", course_id="curso-x", titulo_modulo="Arreglos",
        items_incorrectos=[0, 1],
    )
    # No lanza INV-2: la segunda llamada reanuda la misma identidad de
    # sesión que la primera (mismo estudiante, mismo curso).
    assert entrega_2 is not None


def test_consultar_decision_vigente_sin_evidencia_es_entrega_vacia():
    from app.services.runtime_bridge import consultar_decision_vigente
    from runtime.boundary import Entrega

    entrega = consultar_decision_vigente(student_id="nueva", course_id="curso-x")
    assert entrega == Entrega(asunto=None, diseno=None)


def test_consultar_decision_vigente_refleja_la_ultima_evidencia_registrada():
    from app.services.runtime_bridge import (
        consultar_decision_vigente,
        registrar_evidencia_evaluacion,
    )

    registrar_evidencia_evaluacion(
        student_id="pedro", course_id="curso-y", titulo_modulo="Recursividad",
        items_incorrectos=[0, 1, 2],
    )
    entrega = consultar_decision_vigente(student_id="pedro", course_id="curso-y")
    assert entrega.asunto is not None
    assert entrega.diseno is not None


def test_consultar_decision_vigente_no_registra_ningun_hecho():
    from app.services.runtime_bridge import consultar_decision_vigente
    from app.services.runtime_connection import (
        SPEC_VERSION,
        VERSION_BANCO,
        VERSION_POLITICA,
        almacenes,
    )

    consultar_decision_vigente(student_id="ana", course_id="curso-z")
    consultar_decision_vigente(student_id="ana", course_id="curso-z")
    almacen, _ = almacenes()
    assert almacen.leer("curso:curso-z:estudiante:ana") == ()
