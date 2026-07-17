"""Sprint 3.4 — el primer productor LLM conectado al walkthrough vivo:
Diagnosticar. `registrar_hecho` (E2) SIN ningún parámetro de productor
explícito — exactamente como lo invoca `app/api/routes/students.py` en
producción — debe interpretar la evidencia con `OpenAIProvider`, no con
la regla. `runtime/boundary/inbound/productores.py` es lo único que
decide esto; el resto del Boundary no cambió una línea.

Se salta sin `OPENAI_API_KEY` (mismo criterio que M3).
"""

from __future__ import annotations

import os

import psycopg2
import pytest
from dotenv import load_dotenv

from runtime.boundary import (
    Entrega,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones, reconstruir
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, TipoClaim

load_dotenv()

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


pytestmark = [
    pytest.mark.skipif(not _pg_disponible(), reason="PostgreSQL no disponible"),
    pytest.mark.skipif(
        not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
    ),
]


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
    nombre = f"runtime_diag_llm_vivo_{os.getpid()}"
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


class TestDiagnosticarLLMEnVivo:
    def test_registrar_hecho_sin_overrides_usa_el_llm_real(self, almacen, almacen_memoria):
        identidad = abrir_sesion(_peticion_abrir("s-diag-llm-vivo"), almacen, almacen_memoria)
        entrega = registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )
        assert isinstance(entrega, Entrega)
        assert entrega.diseno is not None  # el ciclo completó hasta Adaptar

        registros = almacen.leer(identidad.session_id)
        estado = reconstruir(identidad, {}, registros)
        interpretacion = next(
            c
            for c in estado.claims
            if c.autor is Capacidad.DIAGNOSTICAR and c.tipo is TipoClaim.INTERPRETACION
        )
        assert interpretacion.provenance.origen == OrigenProvenance.LLM
        assert interpretacion.afirmacion["dominada"] is False  # 3 errores, umbral=2
        # razonamiento real del modelo, no la plantilla de la regla
        assert interpretacion.afirmacion.get("razonamiento")

    def test_diagnostica_las_dos_competencias_del_mapa_completo(self, almacen, almacen_memoria):
        """Regresión del fix de guardia: dos hechos, dos competencias
        interpretadas — no solo la primera."""
        identidad = abrir_sesion(_peticion_abrir("s-diag-llm-mapa"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-1", "items_incorrectos": [1]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )
        identidad = abrir_sesion(_peticion_abrir("s-diag-llm-mapa"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-3", "items_incorrectos": [1, 2, 3]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )
        registros = almacen.leer(identidad.session_id)
        estado = reconstruir(identidad, {}, registros)
        interpretaciones = {
            c.asunto: c
            for c in estado.claims
            if c.autor is Capacidad.DIAGNOSTICAR and c.tipo is TipoClaim.INTERPRETACION
        }
        assert set(interpretaciones) == {"dominio(COMP-1)", "dominio(COMP-3)"}
        assert all(
            c.provenance.origen == OrigenProvenance.LLM for c in interpretaciones.values()
        )
