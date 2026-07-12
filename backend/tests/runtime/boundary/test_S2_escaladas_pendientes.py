"""S2 — `consultar_escaladas_pendientes`: la notificación dedicada de
RFC-0010 §2 ("aviso al docente de que una deliberación espera su
autoridad"), distinta de leer `/estado` y filtrar en el frontend.

Sin dobles (ADR-0005 §3): PostgreSQL real, LangGraph real.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.boundary import PeticionAbrirSesion, consultar_escaladas_pendientes
from runtime.boundary.inbound.escalada import resolver_escalada
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones, encadenar
from runtime.kernel.reducers import registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Capacidad,
    Escalada,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState
from runtime.kernel.transitions import TransitionIntent

_URL = os.environ.get(
    "RUNTIME_TEST_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)

_OPERACIONES = {
    "registrar_fact": registrar_fact,
    "registrar_claim": registrar_claim,
    "registrar_deliberacion": registrar_deliberacion,
}


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


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="0",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_s2_escaladas_test_{os.getpid()}"
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


def _aplicar_y_persistir(almacen, identidad, estado, registros, intent):
    resultado = _OPERACIONES[intent.operacion](estado, **intent.argumentos)
    assert resultado.__class__.__name__ == "Aplicado"
    registro = encadenar(identidad, registros, {"intent": intent, "eventos": resultado.eventos})
    almacen.persistir(registro)
    return resultado.estado, registros + (registro,)


def _sembrar_escalada(almacen, identidad):
    """Misma técnica de test_E3_resolver_escalada.py: fact → interpretación
    → tensión → deliberación ESCALADA construida directamente (RFC-0006
    §4 no implementado todavía)."""
    almacen.abrir_sesion(identidad)
    estado = LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
    registros = ()

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.EVALUAR, operacion="registrar_fact",
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
            productor=Capacidad.DIAGNOSTICAR, operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.DIAGNOSTICAR, "tipo": TipoClaim.INTERPRETACION,
                "asunto": "dominio(COMP-2)", "afirmacion": {"dominada": False, "errores": 1},
                "respaldo": (fact_id,), "confianza": Decimal("0.75"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
            },
            base=estado.transicion,
        ),
    )
    interpretacion_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.REMEDIAR, operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.REMEDIAR, "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)", "afirmacion": {"accion": "reforzar"},
                "respaldo": (interpretacion_id,), "confianza": Decimal("0.60"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    remediar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor=Capacidad.ORIENTAR, operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.ORIENTAR, "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)", "afirmacion": {"accion": "avanzar-con-andamiaje"},
                "respaldo": (interpretacion_id,), "confianza": Decimal("0.58"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    orientar_id = estado.claims[-1].id

    estado, registros = _aplicar_y_persistir(
        almacen, identidad, estado, registros,
        TransitionIntent(
            productor="kernel", operacion="registrar_deliberacion",
            argumentos={
                "participantes": (remediar_id, orientar_id),
                "resultado": Escalada(destinatario="docente"),
            },
            base=estado.transicion,
        ),
    )
    escalada_id = estado.deliberaciones[-1].id
    return escalada_id, remediar_id


class TestS2_ConsultarEscaladasPendientes:
    def test_sesion_sin_escaladas_es_vacia(self, almacen, almacen_memoria):
        escaladas = consultar_escaladas_pendientes(
            _peticion_abrir("s-s2-sin-escaladas"), almacen, almacen_memoria
        )
        assert escaladas == ()

    def test_no_registra_ningun_hecho_nuevo(self, almacen, almacen_memoria):
        consultar_escaladas_pendientes(
            _peticion_abrir("s-s2-sin-escribir"), almacen, almacen_memoria
        )
        assert almacen.leer("s-s2-sin-escribir") == ()

    def test_devuelve_la_escalada_abierta(self, almacen, almacen_memoria):
        identidad = _identidad("s-s2-abierta")
        escalada_id, _remediar_id = _sembrar_escalada(almacen, identidad)

        escaladas = consultar_escaladas_pendientes(
            _peticion_abrir("s-s2-abierta"), almacen, almacen_memoria
        )
        assert len(escaladas) == 1
        assert escaladas[0].id == escalada_id

    def test_una_escalada_resuelta_deja_de_estar_pendiente(self, almacen, almacen_memoria):
        identidad = _identidad("s-s2-resuelta")
        escalada_id, remediar_id = _sembrar_escalada(almacen, identidad)

        resolver_escalada(
            identidad,
            escalada_id=escalada_id,
            claim_elegido=remediar_id,
            human_reason=None,
            almacen=almacen,
            almacen_memoria=almacen_memoria,
        )

        escaladas = consultar_escaladas_pendientes(
            _peticion_abrir("s-s2-resuelta"), almacen, almacen_memoria
        )
        assert escaladas == ()
