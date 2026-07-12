"""RFC-0008 §3, modo Reconstrucción ("recorrer la secuencia persistida de
estados") — Épica 4, Replay Cognitivo. Distinto de la traza (RFC-0007
§2.1, solo eventos): aquí cada eslabón lleva el `LearningState` completo
tal como quedó después de esa transición.

`_reconstruir_pasos` es el único recorrido de la historia; esta suite
demuestra que `reconstruir_con_replay()` proyecta ese recorrido en
estados por transición, y que el refactor no cambió el comportamiento ya
cubierto por `reconstruir()`/`reconstruir_con_traza()` (test_R3 y
test_RFC_0007_traza_eventos, ambos sin modificar).

Sin dobles (ADR-0005 §3): PostgreSQL real, esquema temporal por corrida.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.engine.checkpoint import (
    AlmacenTransiciones,
    RegistroTransicion,
    encadenar,
    reconstruir_con_replay,
)
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_fact
from runtime.kernel.state.entries import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState
from runtime.kernel.transitions import TransitionIntent

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)

_OPERACIONES = {"registrar_fact": registrar_fact, "registrar_claim": registrar_claim}


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _pg_disponible(), reason="PostgreSQL no disponible (RFC-0008 exige BD real)"
)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def almacen():
    esquema = f"runtime_test_{os.getpid()}_replay"
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    yield almacen
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA {esquema} CASCADE")


def _aplicar_y_persistir(almacen, identidad, estado, registros, intent: TransitionIntent):
    resultado = _OPERACIONES[intent.operacion](estado, **intent.argumentos)
    assert isinstance(resultado, Aplicado)
    registro = encadenar(
        identidad, registros, {"intent": intent, "eventos": resultado.eventos}
    )
    almacen.persistir(registro)
    return resultado.estado, registros + (registro,)


def _construir_historia(almacen, identidad):
    """Fact → claim — 2 transiciones, suficiente para probar que el
    estado de cada paso es ACUMULATIVO (T2 contiene el fact de T1 más el
    claim nuevo), no una foto aislada de esa sola transición."""
    almacen.abrir_sesion(identidad)
    estado = LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
    registros: tuple[RegistroTransicion, ...] = ()

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {"competencia": "COMP-2", "items_incorrectos": [3]},
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )
    fact_id = estado.facts[0].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.DIAGNOSTICAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.DIAGNOSTICAR,
                "tipo": TipoClaim.INTERPRETACION,
                "asunto": "dominio(COMP-2)",
                "afirmacion": {"dominada": False},
                "respaldo": (fact_id,),
                "confianza": Decimal("0.78"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
            },
            base=estado.transicion,
        ),
    )
    return estado, registros


class TestRFC0008_ReplayEstado:
    def test_replay_expone_el_estado_acumulado_por_transicion(self, almacen):
        identidad = _identidad("s-rfc0008-replay")
        estado_final, registros = _construir_historia(almacen, identidad)
        leidos = almacen.leer(identidad.session_id)

        estado_reconstruido, replay = reconstruir_con_replay(
            identidad, contexto={"ruta": "condicionales"}, registros=leidos
        )

        assert estado_reconstruido == estado_final
        assert len(replay) == 2

        # T1: solo el fact, todavía sin claims (estado ACUMULADO hasta T1).
        assert len(replay[0].estado.facts) == 1
        assert len(replay[0].estado.claims) == 0
        assert replay[0].transicion == 1

        # T2: el fact de T1 sigue presente, más el claim nuevo — no una
        # foto aislada de la transición 2.
        assert len(replay[1].estado.facts) == 1
        assert len(replay[1].estado.claims) == 1
        assert replay[1].transicion == 2
        assert replay[1].estado == estado_final

    def test_replay_de_sesion_vacia_es_secuencia_vacia(self, almacen):
        identidad = _identidad("s-rfc0008-replay-vacio")
        almacen.abrir_sesion(identidad)

        estado, replay = reconstruir_con_replay(
            identidad, contexto={"ruta": "condicionales"}, registros=()
        )

        assert replay == ()
        assert estado == LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
