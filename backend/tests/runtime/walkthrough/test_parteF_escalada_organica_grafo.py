"""RFC-0006/5, Parte F sobre el grafo real — LangGraph + Postgres.

Complementa `tests/runtime/deliberation/test_parteF_escalada_organica.py`
(mecánica pura): aquí se prueba lo que solo el grafo puede probar — que
una `Escalada` orgánica no produce `GraphRecursionError`, que aparece en
S2 (`consultar_escaladas_pendientes`) SIN sembrado manual (el motivo
original de la Parte F según ROADMAP-RFC-0006: "hasta esta parte, S2
sigue sin tener nada real que mostrar sin sembrado manual"), y que la
resolución del docente (E3, `resolver_escalada`) cierra el ciclo
completo: el walkthrough continúa hasta Adaptar y la Entrega refleja la
autoridad humana.

La política con reservas/δ real no existe en producción (v1 las hace
estructuralmente inalcanzables): se registran políticas de prueba vía
monkeypatch — el mecanismo es real, la configuración es del test (mismo
criterio que la Parte E en
`test_parteE_walkthrough_aplazamiento.py`).

Los números no son arbitrarios: los productores de reglas declaran
confianzas fijas (Diagnosticar 0.78, Remediar 0.82, Orientar 0.75), así
que el margen D2 real es 0.07 y el margen D1 real es 0.00 — con
δ=0.10 ninguna de las dos tensiones discrimina jamás, que es
exactamente el paisaje que la vía del límite necesita.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.boundary import PeticionAbrirSesion, consultar_escaladas_pendientes
from runtime.boundary.inbound.escalada import REGLA_DECISION_HUMANA, resolver_escalada
from runtime.boundary.outbound.entregas import proyectar_entrega
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad
from runtime.kernel.transitions import TransitionIntent

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
    not _pg_disponible(), reason="PostgreSQL no disponible"
)

_VERSION_RESERVA = "parteF-reserva-test"
_VERSION_LIMITE = "parteF-limite-test"

_POLITICA_RESERVA = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    asuntos_reservados=frozenset({"siguiente-paso(sesion)"}),
)

_POLITICA_LIMITE = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    # mayor que el margen D2 real (0.07) y que el D1 real (0.00): ninguna
    # tensión discrimina — la cadena de aplazadas es inevitable.
    delta=Decimal("0.10"),
    limite_reconvocatoria=1,
)


@pytest.fixture(autouse=True)
def _politicas_de_prueba(monkeypatch):
    monkeypatch.setitem(POLITICAS, _VERSION_RESERVA, _POLITICA_RESERVA)
    monkeypatch.setitem(POLITICAS, _VERSION_LIMITE, _POLITICA_LIMITE)


def _identidad(session_id: str, version_politica: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="0",
        version_banco="banco-v2",
        version_politica=version_politica,
        spec_version="foundation-2026-07-10",
    )


def _peticion(session_id: str, version_politica: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id="maria",
        version_banco="banco-v2",
        version_politica=version_politica,
        spec_version="foundation-2026-07-10",
    )


def _evaluacion(incorrectos: list[int]) -> tuple[TransitionIntent, ...]:
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": "COMP-2",
                    "items_incorrectos": incorrectos,
                },
                "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
            },
            base=0,
        ),
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_parte_f_grafo_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


@pytest.fixture
def almacenes(esquema):
    almacen = AlmacenTransiciones(_URL, esquema=esquema)
    almacen.preparar()
    almacen_memoria = AlmacenMemoria(_URL, esquema=esquema)
    almacen_memoria.preparar()
    return almacen, almacen_memoria


class TestViaReservaEnElGrafo:
    def test_la_tension_reservada_escala_sola_y_llega_a_s2(self, almacenes):
        """El recorrido que la Parte F le debía a S2: la evidencia entra,
        la tensión D2 (Remediar 0.82 vs Orientar 0.75) nace sobre un
        asunto reservado, y la escalada aparece en
        `consultar_escaladas_pendientes` sin que nadie la siembre. Que
        este test termine ya prueba que no hubo `GraphRecursionError`."""
        almacen, almacen_memoria = almacenes
        identidad = _identidad("s-parteF-reserva", _VERSION_RESERVA)

        final = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        estado = final["estado"]

        escaladas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Escalada)
        ]
        assert len(escaladas) == 1
        assert escaladas[0].resultado.destinatario == "docente"
        # la mecánica no decidió lo reservado (RFC-0009 §3)
        assert estado.decisiones == ()
        # escalar no descarta: el docente selecciona entre lo que la
        # escalada puso sobre la mesa (P15, E3)
        for ref in escaladas[0].participantes:
            assert estado.buscar(ref).vigencia.vigente

        pendientes = consultar_escaladas_pendientes(
            _peticion("s-parteF-reserva", _VERSION_RESERVA),
            almacen,
            almacen_memoria,
        )
        assert [d.id for d in pendientes] == [escaladas[0].id]

    def test_la_urgencia_no_devuelve_la_autoridad_reservada(self, almacenes):
        """Anti-bypass en el grafo (RFC-0009 §3): ni con un estudiante
        esperando en la pantalla la mecánica resuelve lo reservado."""
        almacen, _ = almacenes
        identidad = _identidad("s-parteF-reserva-urgente", _VERSION_RESERVA)

        final = ejecutar_walkthrough(
            almacen, identidad, _evaluacion([3, 4, 8]), urgente=True
        )
        estado = final["estado"]
        assert any(
            isinstance(d.resultado, Escalada) for d in estado.deliberaciones
        )
        assert estado.decisiones == ()

    def test_reanudar_preserva_la_escalada_sin_duplicarla(self, almacenes):
        """Round-trip RFC-0008 §3: la `Escalada` persistida se
        reconstruye tal cual, y reanudar sin evidencia nueva no vuelve a
        convocar ni re-escala (la tensión escalada jamás vuelve a ser
        bloqueante — solo el docente la cierra)."""
        almacen, _ = almacenes
        identidad = _identidad("s-parteF-reserva-reanuda", _VERSION_RESERVA)
        primera = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))

        final = ejecutar_walkthrough(almacen, identidad, hechos_del_mundo=())
        estado = final["estado"]
        assert estado.transicion == primera["estado"].transicion
        escaladas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Escalada)
        ]
        assert len(escaladas) == 1

    def test_la_resolucion_del_docente_cierra_el_ciclo_hasta_adaptar(self, almacenes):
        """E3 sobre una escalada orgánica: el docente elige la propuesta
        de Remediar, la deliberación `decision-humana` deriva la decisión
        (INV-6: aceptó una PROPUESTA), Adaptar continúa solo y la Entrega
        refleja la autoridad humana. S2 queda vacía: nada pendiente."""
        almacen, almacen_memoria = almacenes
        identidad = _identidad("s-parteF-reserva-e3", _VERSION_RESERVA)
        final = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        estado = final["estado"]
        escalada = next(
            d for d in estado.deliberaciones if isinstance(d.resultado, Escalada)
        )
        remediar = next(
            ref
            for ref in escalada.participantes
            if estado.buscar(ref).autor is Capacidad.REMEDIAR
        )

        entrega = resolver_escalada(
            identidad,
            escalada_id=escalada.id,
            claim_elegido=remediar,
            human_reason="refuerzo dirigido antes de avanzar",
            almacen=almacen,
            almacen_memoria=almacen_memoria,
        )

        assert entrega.diseno["profundidad"] == "fundamentos"

        final_2 = ejecutar_walkthrough(almacen, identidad, hechos_del_mundo=())
        estado_2 = final_2["estado"]
        humana = next(
            d
            for d in estado_2.deliberaciones
            if isinstance(d.resultado, Resuelta)
            and d.resultado.regla == REGLA_DECISION_HUMANA
        )
        assert humana.enlaza_a == escalada.id
        decisiones = [d for d in estado_2.decisiones if d.vigencia.vigente]
        assert len(decisiones) == 1
        assert decisiones[0].contenido["accion"] == "reforzar"
        assert decisiones[0].origen == humana.id
        assert any(
            c.autor is Capacidad.ADAPTAR and c.vigencia.vigente
            for c in estado_2.claims
        )

        pendientes = consultar_escaladas_pendientes(
            _peticion("s-parteF-reserva-e3", _VERSION_RESERVA),
            almacen,
            almacen_memoria,
        )
        assert pendientes == ()


class TestViaLimiteEnElGrafo:
    def test_la_evidencia_contradictoria_agota_la_cadena_y_escala(self, almacenes):
        """La cadena orgánica completa a través de TRES invocaciones
        reales del walkthrough (nadie siembra nada):

        1. eval [3,4,8] → tensión D2 (margen 0.07 < δ) → Aplazada.
        2. eval [3] → interpretación nueva contradice (dominada=True vs
           False, ambas 0.78) → tensión D1 (margen 0 < δ) → Aplazada:
           nace la cabeza de la cadena D1.
        3. eval [3,4] → tercera interpretación cambia el paisaje D1 →
           reconvocatoria `enlaza_a` la cabeza; el margen sigue sin
           discriminar y la cadena ya acumula `limite_reconvocatoria=1`
           aplazadas → `Escalada` ("ninguna deliberación puede diferirse
           para siempre", RFC-0006 §4) — visible en S2 sin sembrado."""
        almacen, almacen_memoria = almacenes
        identidad = _identidad("s-parteF-limite", _VERSION_LIMITE)

        ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        final_2 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3]))
        aplazada_d1 = next(
            d
            for d in final_2["estado"].deliberaciones
            if isinstance(d.resultado, Aplazada)
            and final_2["estado"].buscar(d.participantes[0]).tipo
            is TipoClaim.INTERPRETACION
        )

        final_3 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4]))
        estado = final_3["estado"]

        escaladas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Escalada)
        ]
        assert len(escaladas) == 1
        assert escaladas[0].enlaza_a == aplazada_d1.id
        # los tres rivales interpretativos siguen sobre la mesa (P15)
        assert len(escaladas[0].participantes) == 3

        pendientes = consultar_escaladas_pendientes(
            _peticion("s-parteF-limite", _VERSION_LIMITE),
            almacen,
            almacen_memoria,
        )
        assert [d.id for d in pendientes] == [escaladas[0].id]

    def test_el_docente_zanja_la_contradiccion_y_el_sistema_se_readapta(
        self, almacenes
    ):
        """E3 sobre la escalada D1: el docente elige la interpretación
        `dominada=True`; la resolución humana descarta a las rivales, la
        cascada tumba las propuestas cuyo suelo cayó (2026-07-13), la
        re-propuesta única de Orientar deriva decisión directa (D3) y el
        estudiante recibe `avanzar-con-andamiaje` — el ciclo adaptativo
        continúa después de la autoridad humana, no se detiene en ella."""
        almacen, almacen_memoria = almacenes
        identidad = _identidad("s-parteF-limite-e3", _VERSION_LIMITE)
        ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        ejecutar_walkthrough(almacen, identidad, _evaluacion([3]))
        final = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4]))
        estado = final["estado"]
        escalada = next(
            d for d in estado.deliberaciones if isinstance(d.resultado, Escalada)
        )
        dominada = next(
            ref
            for ref in escalada.participantes
            if estado.buscar(ref).afirmacion.get("dominada") is True
        )

        entrega = resolver_escalada(
            identidad,
            escalada_id=escalada.id,
            claim_elegido=dominada,
            human_reason="la re-evaluación limpia pesa más",
            almacen=almacen,
            almacen_memoria=almacen_memoria,
        )

        assert entrega.diseno["profundidad"] == "aplicacion"

        final_2 = ejecutar_walkthrough(almacen, identidad, hechos_del_mundo=())
        estado_2 = final_2["estado"]
        decisiones = [d for d in estado_2.decisiones if d.vigencia.vigente]
        assert len(decisiones) == 1
        assert decisiones[0].contenido["accion"] == "avanzar-con-andamiaje"

        pendientes = consultar_escaladas_pendientes(
            _peticion("s-parteF-limite-e3", _VERSION_LIMITE),
            almacen,
            almacen_memoria,
        )
        assert pendientes == ()
