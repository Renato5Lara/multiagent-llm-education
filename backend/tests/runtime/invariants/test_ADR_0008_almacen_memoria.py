"""M4 PR-4 — AlmacenMemoria y kernel/memory (ADR-0008).

Alcance de PR-4, deliberadamente: solo la infraestructura de
almacenamiento. Sin wiring en `ejecutar_walkthrough`, sin señal de
cierre, sin RFC-0010 — eso es PR-5 (ADR-0008 §2.4).

Sin dobles (ADR-0005 §3): PostgreSQL real, esquema temporal por corrida.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenMemoria
from runtime.kernel.memory import VersionMemoria, preparar_version, validar_version
from runtime.kernel.state.state import Identidad

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
    not _pg_disponible(), reason="PostgreSQL no disponible (ADR-0008 exige BD real)"
)


def _identidad(session_id: str, student_id: str = "maria") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id=student_id,
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


_CATALOGO_VALIDO = {
    "modelo_propuesto": ({"competencia": "COMP-2", "efecto_positivo": True},),
    "ruta_actualizada": "condicionales",
    "deuda_abierta": (),
    "resumen_destilado": {
        "competencias_evaluadas": ("COMP-2",),
        "decisiones_totales": 1,
        "decisiones_validadas": 1,
    },
}


@pytest.fixture
def esquema():
    nombre = f"runtime_memoria_test_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def almacen(esquema):
    almacen = AlmacenMemoria(_URL, esquema=esquema)
    almacen.preparar()
    return almacen


class TestKernelMemory_PreparaYValida:
    def test_preparar_version_envuelve_salidas_sin_transformarlas(self):
        identidad = _identidad("s-pr4-preparar")
        version = preparar_version(identidad, _CATALOGO_VALIDO)
        assert version.student_id == "maria"
        assert version.session_id == "s-pr4-preparar"
        assert version.catalogo == _CATALOGO_VALIDO  # sin transformación (ADR-0008 §4)

    def test_validar_version_acepta_el_catalogo_cerrado_de_rfc_0005(self):
        version = preparar_version(_identidad("s-pr4-validar-ok"), _CATALOGO_VALIDO)
        validar_version(version)  # no debe lanzar

    def test_validar_version_rechaza_forma_incompleta(self):
        incompleto = dict(_CATALOGO_VALIDO)
        del incompleto["deuda_abierta"]
        version = preparar_version(_identidad("s-pr4-validar-falta"), incompleto)
        with pytest.raises(ValueError, match="ADR-0008"):
            validar_version(version)

    def test_validar_version_rechaza_clave_ajena_al_catalogo_cerrado(self):
        con_clave_extra = dict(_CATALOGO_VALIDO, campo_inventado="no debería existir")
        version = preparar_version(_identidad("s-pr4-validar-extra"), con_clave_extra)
        with pytest.raises(ValueError, match="ADR-0008"):
            validar_version(version)


class TestADR_0008_AlmacenMemoria:
    def test_cargar_sin_versiones_devuelve_none(self, almacen):
        assert almacen.cargar("estudiante-nuevo") is None

    def test_consolidar_asigna_version_1_a_la_primera(self, almacen):
        version = preparar_version(_identidad("s-pr4-v1"), _CATALOGO_VALIDO)
        numero = almacen.consolidar(version)
        assert numero == 1

    def test_consolidar_incrementa_por_estudiante(self, almacen):
        v1 = preparar_version(_identidad("s-pr4-inc-1"), _CATALOGO_VALIDO)
        v2 = preparar_version(_identidad("s-pr4-inc-2"), _CATALOGO_VALIDO)
        assert almacen.consolidar(v1) == 1
        assert almacen.consolidar(v2) == 2

    def test_consolidar_no_mezcla_estudiantes_distintos(self, almacen):
        # Criterio de aceptación 1 (ADR-0008 §5): la numeración es por
        # student_id, no global.
        v_maria = preparar_version(_identidad("s-pr4-maria", "maria"), _CATALOGO_VALIDO)
        v_juan = preparar_version(_identidad("s-pr4-juan", "juan"), _CATALOGO_VALIDO)
        assert almacen.consolidar(v_maria) == 1
        assert almacen.consolidar(v_juan) == 1  # otro estudiante, arranca en 1 también

    def test_cargar_devuelve_la_version_vigente_mas_reciente(self, almacen):
        identidad_1 = _identidad("s-pr4-vigente-1")
        identidad_2 = _identidad("s-pr4-vigente-2")
        almacen.consolidar(preparar_version(identidad_1, _CATALOGO_VALIDO))
        otro_catalogo = dict(_CATALOGO_VALIDO, ruta_actualizada="funciones")
        almacen.consolidar(preparar_version(identidad_2, otro_catalogo))

        cargada = almacen.cargar("maria")
        assert isinstance(cargada, VersionMemoria)
        assert cargada.session_id == "s-pr4-vigente-2"
        assert cargada.catalogo["ruta_actualizada"] == "funciones"

    def test_criterio_de_aceptacion_3_nunca_se_edita_una_version_anterior(
        self, almacen, esquema
    ):
        # ADR-0008 §5 (3): consolidar dos veces produce dos versiones,
        # nunca sobreescribe la primera — verificado leyendo ambas.
        identidad_1 = _identidad("s-pr4-inmutable-1")
        identidad_2 = _identidad("s-pr4-inmutable-2")
        almacen.consolidar(preparar_version(identidad_1, _CATALOGO_VALIDO))
        otro_catalogo = dict(_CATALOGO_VALIDO, ruta_actualizada="funciones")
        almacen.consolidar(preparar_version(identidad_2, otro_catalogo))

        with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
            cursor.execute(f"SET search_path TO {esquema}")
            cursor.execute(
                "SELECT version, session_id FROM memory_versions"
                " WHERE student_id = %s ORDER BY version",
                ("maria",),
            )
            filas = cursor.fetchall()
        assert filas == [(1, "s-pr4-inmutable-1"), (2, "s-pr4-inmutable-2")]

    def test_pk_impide_reemplazo_silencioso_de_una_version(self, almacen, esquema):
        # Backstop de SQL (pregunta 5 del contrato): la unicidad la
        # garantiza la clave primaria, no solo la lógica de Python.
        with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
            cursor.execute(f"SET search_path TO {esquema}")
            cursor.execute(
                "INSERT INTO memory_versions"
                " (student_id, version, session_id, catalogo)"
                " VALUES (%s, %s, %s, %s::jsonb)",
                ("maria", 1, "s-manual", '{"x": 1}'),
            )
            conexion.commit()
            with pytest.raises(psycopg2.errors.UniqueViolation):
                cursor.execute(
                    "INSERT INTO memory_versions"
                    " (student_id, version, session_id, catalogo)"
                    " VALUES (%s, %s, %s, %s::jsonb)",
                    ("maria", 1, "s-otro-intento", '{"y": 2}'),
                )

    def test_consolidar_dos_veces_la_misma_sesion_se_rechaza_sin_tocar_la_tabla(
        self, almacen, esquema
    ):
        # M4 PR-5: ADR-0008 §5 criterio 1 — una sesión consolida como
        # máximo una vez. La condición se descubrió al wirear PR-5 (la
        # implementación de PR-4 no la hacía cumplir); corregida aquí.
        # No basta con que lance la excepción: el almacenamiento debe
        # quedar exactamente igual que antes del segundo intento.
        version = preparar_version(_identidad("s-pr5-duplicado"), _CATALOGO_VALIDO)
        assert almacen.consolidar(version) == 1

        with pytest.raises(ValueError, match="ya fue consolidada"):
            almacen.consolidar(version)

        with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
            cursor.execute(f"SET search_path TO {esquema}")
            cursor.execute(
                "SELECT version FROM memory_versions WHERE student_id = %s",
                ("maria",),
            )
            filas = cursor.fetchall()
        assert filas == [(1,)]  # ni una fila más, ni una versión 2
