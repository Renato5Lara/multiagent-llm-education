"""Sprint 3.4 — segundo y tercer productor conectados: Remediar y
Orientar. Con los tres (Diagnosticar + Remediar + Orientar) en LLM, la
tensión D2 completa ("reforzar" vs "avanzar-con-andamiaje") se origina
en evidencia LLM en AMBOS lados por primera vez — el consenso ya no
compara 0.82 contra 0.75, compara dos propuestas razonadas por el
modelo.

`registrar_hecho` (E2) SIN ningún parámetro de productor explícito —
exactamente como lo invoca `app/api/routes/students.py` en producción.

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
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Resuelta, TipoClaim

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
    nombre = f"runtime_rem_ori_llm_vivo_{os.getpid()}"
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


class TestRemediarOrientarLLMEnVivo:
    def test_la_tension_d2_se_origina_en_evidencia_llm_de_ambos_lados(
        self, almacen, almacen_memoria
    ):
        identidad = abrir_sesion(_peticion_abrir("s-rem-ori-llm-vivo"), almacen, almacen_memoria)
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

        propuestas = {
            c.autor: c
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA
            and c.autor in (Capacidad.REMEDIAR, Capacidad.ORIENTAR)
        }
        assert set(propuestas) == {Capacidad.REMEDIAR, Capacidad.ORIENTAR}
        for claim in propuestas.values():
            assert claim.provenance.origen == OrigenProvenance.LLM
            assert claim.afirmacion.get("razonamiento")  # razonado, no una plantilla

        deliberacion = next(
            d for d in estado.deliberaciones if isinstance(d.resultado, Resuelta)
        )
        assert set(deliberacion.participantes) == {
            propuestas[Capacidad.REMEDIAR].id,
            propuestas[Capacidad.ORIENTAR].id,
        }
        decision = estado.decisiones[0]
        assert decision.origen == deliberacion.id
        # El ganador es uno de los dos — el consenso decidió, no una
        # constante: la afirmación viene del claim aceptado.
        ganador = estado.buscar(deliberacion.resultado.aceptados[0])
        assert decision.contenido == dict(ganador.afirmacion) or (
            decision.contenido.get("accion") == ganador.afirmacion.get("accion")
        )

    def test_remediar_no_reproponer_tras_perder_limpio_con_llm_real(
        self, almacen, almacen_memoria
    ):
        """El fix de `palabra_en_pie` (af9a438) sostenido contra un
        proveedor real: reanudar sin evidencia nueva no debe producir
        una segunda propuesta de quien perdió la D2."""
        identidad = abrir_sesion(_peticion_abrir("s-rem-ori-churn-vivo"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
                origen=OrigenProvenance.INSTRUMENTO,
            ),
            almacen,
            almacen_memoria,
        )
        estado_1 = reconstruir(identidad, {}, almacen.leer(identidad.session_id))
        remediar_ids_1 = {c.id for c in estado_1.claims if c.autor is Capacidad.REMEDIAR}

        identidad = abrir_sesion(_peticion_abrir("s-rem-ori-churn-vivo"), almacen, almacen_memoria)
        registrar_hecho(
            PeticionHechoDelMundo(
                identidad=identidad,
                contenido={},
                origen=OrigenProvenance.TELEMETRIA,
            ),
            almacen,
            almacen_memoria,
        )
        estado_2 = reconstruir(identidad, {}, almacen.leer(identidad.session_id))
        remediar_ids_2 = {c.id for c in estado_2.claims if c.autor is Capacidad.REMEDIAR}
        # contenido vacío no produce evidencia evaluable — sin paisaje
        # nuevo, palabra_en_pie sigue bloqueando: ninguna propuesta
        # NUEVA de Remediar (haya ganado o perdido la D2 original).
        assert remediar_ids_2 == remediar_ids_1
