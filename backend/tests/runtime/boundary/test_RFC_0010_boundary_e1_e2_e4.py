"""Épica 1 — RFC-0010: E1 (abrir), E2 (hechos del mundo) y E4 (cerrar),
más S1 (Entrega) — vía `runtime.boundary`, nunca `BaseAgent` (ADR-0009).

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os

import psycopg2
import pytest

from runtime.boundary import (
    Entrega,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    proyectar_entrega,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.kernel.state.entries import OrigenProvenance
from runtime.kernel.state.state import LearningState
from runtime.kernel.state.state import Identidad as IdentidadKernel

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


#: T1 del Walkthrough-0001 (mismo fixture que
#: tests/runtime/walkthrough/test_walkthrough_0001.py): suficiente para
#: recorrer diagnosticar → deliberar → decidir → adaptar en una sola
#: llamada.
_CONTENIDO_T1 = {"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]}


@pytest.fixture
def esquema():
    nombre = f"runtime_boundary_test_{os.getpid()}"
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


class TestE1_AbrirSesion:
    def test_sesion_nueva_resuelve_version_student_model_0(self, almacen, almacen_memoria):
        identidad = abrir_sesion(_peticion_abrir("s-e1-nueva"), almacen, almacen_memoria)
        assert identidad.session_id == "s-e1-nueva"
        assert identidad.student_id == "maria"
        assert identidad.version_student_model == "0"  # RFC-0005 §1.1, N=0

    def test_sesion_nueva_resuelve_la_version_consolidada_mas_reciente(
        self, almacen, almacen_memoria
    ):
        from runtime.kernel.memory import preparar_version

        catalogo = {
            "modelo_propuesto": (),
            "ruta_actualizada": "condicionales",
            "deuda_abierta": (),
            "resumen_destilado": {},
        }
        version = preparar_version(
            IdentidadKernel(
                session_id="s-e1-sesion-previa",
                student_id="maria",
                version_student_model="0",
                version_banco="banco-v2",
                version_politica="v1",
                spec_version="foundation-2026-07-10",
            ),
            catalogo,
        )
        almacen_memoria.consolidar(version)

        identidad = abrir_sesion(_peticion_abrir("s-e1-siguiente"), almacen, almacen_memoria)
        assert identidad.version_student_model == "1"

    def test_reanudacion_reutiliza_la_identidad_exacta_pese_a_nueva_consolidacion(
        self, almacen, almacen_memoria
    ):
        from runtime.kernel.memory import preparar_version

        # Abre la sesión: fija version_student_model="0".
        identidad_1 = abrir_sesion(_peticion_abrir("s-e1-reanudar"), almacen, almacen_memoria)
        assert identidad_1.version_student_model == "0"

        # Otra sesión del mismo estudiante consolida memoria mientras
        # tanto — "la vigente" ahora sería "1", no "0".
        catalogo = {
            "modelo_propuesto": (),
            "ruta_actualizada": "condicionales",
            "deuda_abierta": (),
            "resumen_destilado": {},
        }
        version = preparar_version(
            IdentidadKernel(
                session_id="s-e1-otra-sesion",
                student_id="maria",
                version_student_model="0",
                version_banco="banco-v2",
                version_politica="v1",
                spec_version="foundation-2026-07-10",
            ),
            catalogo,
        )
        almacen_memoria.consolidar(version)

        # Reanudar "s-e1-reanudar" debe devolver la MISMA identidad
        # ("0"), no la nueva vigente ("1") — R5, INV-2.
        identidad_2 = abrir_sesion(_peticion_abrir("s-e1-reanudar"), almacen, almacen_memoria)
        assert identidad_2 == identidad_1


class TestE2_RegistrarHecho:
    def test_hecho_devuelve_una_entrega_de_adaptar(self, almacen, almacen_memoria):
        identidad = abrir_sesion(_peticion_abrir("s-e2-completa"), almacen, almacen_memoria)
        peticion = PeticionHechoDelMundo(
            identidad=identidad,
            contenido=_CONTENIDO_T1,
            origen=OrigenProvenance.INSTRUMENTO,
        )
        entrega = registrar_hecho(peticion, almacen, almacen_memoria)
        assert isinstance(entrega, Entrega)
        assert entrega.asunto is not None
        assert entrega.diseno is not None

    def test_boundary_nunca_autora_un_claim_solo_el_fact(self, almacen, almacen_memoria):
        # Grieta A / regla 1: el Boundary traduce el hecho crudo, no
        # interpreta — verificado leyendo el fact persistido.
        identidad = abrir_sesion(_peticion_abrir("s-e2-grieta-a"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad, contenido=_CONTENIDO_T1, origen=OrigenProvenance.INSTRUMENTO
            ),
            almacen,
            almacen_memoria,
        )
        from runtime.engine.checkpoint import reconstruir

        registros = almacen.leer(identidad.session_id)
        estado = reconstruir(identidad, {}, registros)
        fact_boundary = next(f for f in estado.facts if f.contenido == _CONTENIDO_T1)
        assert fact_boundary.autor == "boundary"


class TestE4_CerrarSesion:
    def test_cerrar_sesion_consolida_una_version_de_memoria(self, almacen, almacen_memoria):
        identidad = abrir_sesion(_peticion_abrir("s-e4-cerrar"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido=_CONTENIDO_T1,
                origen=OrigenProvenance.INSTRUMENTO,
                cerrar_sesion=True,
            ),
            almacen,
            almacen_memoria,
        )
        vigente = almacen_memoria.cargar("maria")
        assert vigente is not None
        assert vigente.session_id == "s-e4-cerrar"


class TestS1_ProyectarEntrega:
    def test_sin_claims_de_adaptar_la_entrega_es_vacia(self):
        estado = LearningState(
            identidad=IdentidadKernel(
                session_id="s-vacia",
                student_id="maria",
                version_student_model="0",
                version_banco="banco-v2",
                version_politica="v1",
                spec_version="foundation-2026-07-10",
            ),
            contexto={},
        )
        assert proyectar_entrega(estado) == Entrega(asunto=None, diseno=None)
