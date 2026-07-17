"""Ciclo adaptativo continuo — el sistema cambia de estrategia cuando
la evidencia lo justifica (mitad restante de RFC-0006 Parte G;
CONCEPT-0002 §5: nunca reapertura, siempre entradas nuevas; decisión
del tesista 2026-07-13: cascada de supersede sobre lo prospectivo).

La cadena completa que este archivo protege:

    re-evaluación → interpretación nueva → tensión D1 → deliberación
    (gana la evidencia nueva) → cascada (caen las propuestas cuyo suelo
    fue corregido; lo retrospectivo — veredictos, modelos — se conserva)
    → re-propuesta sobre el paisaje nuevo → decisión nueva que
    SUPERSEDE a la anterior → re-adaptación → Entrega actualizada.

Contra Postgres real + LangGraph real.
"""

import os

import psycopg2
import pytest

from runtime.boundary.outbound.entregas import proyectar_entrega
from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.entries import (
    Capacidad,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
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


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
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
    nombre = f"runtime_reestrategia_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


class TestCambioDeEstrategia:
    def test_la_evidencia_de_dominio_cambia_reforzar_por_avanzar(self, esquema):
        """El recorrido del producto: al estudiante débil se le decide
        reforzar; re-evalúa con éxito en una invocación posterior y el
        sistema — solo, sin intervención — cambia la estrategia a
        avanzar y re-adapta la experiencia."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-reestrategia-1")

        final_1 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        entrega_1 = proyectar_entrega(final_1["estado"])
        decision_1 = next(
            d for d in final_1["estado"].decisiones if d.vigencia.vigente
        )
        assert decision_1.contenido["accion"] == "reforzar"
        assert entrega_1.diseno["profundidad"] == "fundamentos"

        final_2 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3]))
        estado = final_2["estado"]

        # La decisión vieja no se borra: queda supersedida (P14).
        vieja = estado.buscar(decision_1.id)
        assert not vieja.vigencia.vigente

        vigentes = [d for d in estado.decisiones if d.vigencia.vigente]
        assert len(vigentes) == 1
        assert vigentes[0].contenido["accion"] == "avanzar-con-andamiaje"

        # La Entrega (S1) refleja la estrategia nueva — lo que el
        # estudiante recibe cambió con su evidencia.
        entrega_2 = proyectar_entrega(estado)
        assert entrega_2.diseno["profundidad"] == "aplicacion"
        assert entrega_2.diseno["modalidad"] == "mixta"

        # Y la nueva estrategia nace pendiente de validación (INV-12):
        # el ciclo sigue vigilándose a sí mismo.
        assert vigentes[0].estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION

    def test_evidencia_que_confirma_no_cambia_la_estrategia(self, esquema):
        """Anti-churn: una re-evaluación que CONFIRMA la debilidad (sigue
        con ≥2 errores) no reconvoca nada — la interpretación nueva y la
        vieja coinciden (dominada=False ambas), la D1 se resuelve, y la
        re-propuesta de Remediar produce la misma acción: la decisión
        vigente final sigue siendo reforzar."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-reestrategia-2")

        ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        final_2 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4]))
        estado = final_2["estado"]

        vigentes = [d for d in estado.decisiones if d.vigencia.vigente]
        assert len(vigentes) == 1
        assert vigentes[0].contenido["accion"] == "reforzar"
        entrega = proyectar_entrega(estado)
        assert entrega.diseno["profundidad"] == "fundamentos"

    def test_tercera_invocacion_sin_evidencia_no_altera_nada(self, esquema):
        """Estabilidad del punto fijo: reanudar sin evidencia nueva tras
        un cambio de estrategia no produce transiciones nuevas."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-reestrategia-3")

        ejecutar_walkthrough(almacen, identidad, _evaluacion([3, 4, 8]))
        final_2 = ejecutar_walkthrough(almacen, identidad, _evaluacion([3]))
        transicion_2 = final_2["estado"].transicion

        final_3 = ejecutar_walkthrough(almacen, identidad, hechos_del_mundo=())
        assert final_3["estado"].transicion == transicion_2
