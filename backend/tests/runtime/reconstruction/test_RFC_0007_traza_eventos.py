"""RFC-0007 §2.1 (Trazas) — la secuencia de transiciones de una sesión,
con sus eventos, derivada del log persistido, jamás de una segunda
tubería de instrumentación.

`reconstruccion.py::reconstruir()` ya recalculaba los eventos de cada
transición para la verificación de integridad (R3, RFC-0008); esta suite
demuestra que `reconstruir_con_traza()` expone esos mismos eventos por
transición en vez de descartarlos, y que `reconstruir()` sigue
produciendo exactamente el mismo `LearningState` que antes (no debe
haber regresión en el envoltorio).

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
    reconstruir,
    reconstruir_con_traza,
)
from runtime.kernel.events import (
    ClaimRegistrado,
    DeliberacionRegistrada,
    EntradaSupersedida,
    FactRegistrado,
)
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    Resuelta,
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
    not _pg_disponible(), reason="PostgreSQL no disponible (RFC-0007 exige BD real)"
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
    esquema = f"runtime_test_{os.getpid()}_traza"
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
    return resultado.estado, registros + (registro,), resultado.eventos


def _construir_historia(almacen, identidad):
    """Fact → dos claims en tensión → deliberación — 4 transiciones,
    3 de las 7 formas de evento (FactRegistrado, ClaimRegistrado x2,
    DeliberacionRegistrada), suficiente para probar la traza sin repetir
    las 8 transiciones ya cubiertas por test_R3."""
    almacen.abrir_sesion(identidad)
    estado = LearningState(identidad=identidad, contexto={"ruta": "condicionales"})
    registros: tuple[RegistroTransicion, ...] = ()
    eventos_por_transicion: list[tuple] = []

    estado, registros, eventos = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
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
    eventos_por_transicion.append(eventos)
    fact_id = estado.facts[0].id

    estado, registros, eventos = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.REMEDIAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.REMEDIAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "reforzar"},
                "respaldo": (fact_id,),
                "confianza": Decimal("0.82"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    eventos_por_transicion.append(eventos)
    remediar_id = estado.claims[-1].id

    estado, registros, eventos = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor=Capacidad.ORIENTAR,
            operacion="registrar_claim",
            argumentos={
                "autor": Capacidad.ORIENTAR,
                "tipo": TipoClaim.PROPUESTA,
                "asunto": "siguiente-paso(sesion)",
                "afirmacion": {"accion": "avanzar-con-andamiaje"},
                "respaldo": (fact_id,),
                "confianza": Decimal("0.65"),
                "provenance": Provenance.de(OrigenProvenance.REGLA, id="orientacion-v1"),
            },
            base=estado.transicion,
        ),
    )
    eventos_por_transicion.append(eventos)
    orientar_id = estado.claims[-1].id

    estado, registros, eventos = _aplicar_y_persistir(
        almacen,
        identidad,
        estado,
        registros,
        TransitionIntent(
            productor="kernel",
            operacion="registrar_deliberacion",
            argumentos={
                "participantes": (remediar_id, orientar_id),
                "resultado": Resuelta(
                    regla="mayor-confianza-declarada",
                    aceptados=(remediar_id,),
                    confianza=Decimal("0.82"),
                ),
            },
            base=estado.transicion,
        ),
    )
    eventos_por_transicion.append(eventos)

    return estado, registros, tuple(eventos_por_transicion)


class TestRFC0007_TrazaEventos:
    def test_traza_expone_los_mismos_eventos_que_el_reducer_emitio(self, almacen):
        identidad = _identidad("s-rfc0007-traza")
        estado_original, registros, eventos_emitidos = _construir_historia(almacen, identidad)
        leidos = almacen.leer(identidad.session_id)

        estado_reconstruido, traza = reconstruir_con_traza(
            identidad, contexto={"ruta": "condicionales"}, registros=leidos
        )

        assert estado_reconstruido == estado_original
        assert len(traza) == len(registros) == len(eventos_emitidos)
        assert tuple(paso.transicion for paso in traza) == tuple(
            registro.transicion for registro in registros
        )
        assert tuple(paso.eventos for paso in traza) == eventos_emitidos

        assert isinstance(traza[0].eventos[0], FactRegistrado)
        assert isinstance(traza[1].eventos[0], ClaimRegistrado)
        assert isinstance(traza[2].eventos[0], ClaimRegistrado)
        # La deliberación resuelve descartando al rival (orientar): el
        # rival supersedido se registra antes que la deliberación misma
        # (CONCEPT-0002 §3 — descartar es parte de seleccionar).
        assert isinstance(traza[3].eventos[0], EntradaSupersedida)
        assert isinstance(traza[3].eventos[1], DeliberacionRegistrada)

    def test_reconstruir_sin_traza_no_cambia_de_comportamiento(self, almacen):
        """Regresión: el envoltorio `reconstruir()` debe seguir devolviendo
        exactamente el mismo LearningState que antes de introducir la traza."""
        identidad = _identidad("s-rfc0007-sin-traza")
        estado_original, registros, _ = _construir_historia(almacen, identidad)
        leidos = almacen.leer(identidad.session_id)

        estado_reconstruido = reconstruir(
            identidad, contexto={"ruta": "condicionales"}, registros=leidos
        )

        assert estado_reconstruido == estado_original
