"""Mapa completo de interpretaciones (2026-07-13; RFC-0002 R1;
RFC-0006 §5 regla de la raíz; primera mitad de la Parte G).

Diagnosticar interpreta CADA hecho evaluativo (guardia por hecho, mismo
patrón que Tutorizar) y `enrutar` completa el mapa: interpreta toda la
evidencia antes de proponer, y sigue capturando/interpretando evidencia
nueva DESPUÉS de la decisión — lo que antes congelaba el paisaje (un
diagnóstico de 8 competencias dejaba 7 mudas: bug de producto).

Límite deliberado (mitad restante de Parte G): las interpretaciones
posteriores a la decisión NO reabren propuestas ni deliberación —
`registrar_decision` no supersede una decisión previa del mismo asunto,
así que re-proponer crearía una segunda decisión vigente sobre
`siguiente-paso(sesion)`. La re-deliberación con evidencia nueva
(CONCEPT-0002 §5) llega con esa mitad, no aquí.

Contra Postgres real + LangGraph real, igual que la suite canónica.
"""

import os

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.entries import (
    Capacidad,
    OrigenProvenance,
    Provenance,
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


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _hecho(competencia: str, incorrectos: list[int], total: int = 5) -> TransitionIntent:
    return TransitionIntent(
        productor=Capacidad.EVALUAR,
        operacion="registrar_fact",
        argumentos={
            "autor": Capacidad.EVALUAR,
            "contenido": {
                "competencia": competencia,
                "items_incorrectos": incorrectos,
                "items_totales": total,
            },
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        },
        base=0,
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_mapa_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


class TestMapaCompleto:
    def test_tres_hechos_en_una_invocacion_producen_tres_interpretaciones(self, esquema):
        """Regla de la raíz: el mapa se completa ANTES de proponer — las
        3 interpretaciones existen, Remediar/Orientar proponen UNA vez
        sobre siguiente-paso(sesion), una sola deliberación y una sola
        decisión. Las señales de Tutorizar también son 3 (una por hecho)."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-mapa-1"),
            (
                _hecho("bucles", [0, 1, 2]),      # débil
                _hecho("variables", []),           # dominada
                _hecho("condicionales", [0, 1]),   # débil
            ),
        )
        estado = final["estado"]
        interpretaciones = {
            c.asunto: c.afirmacion["dominada"]
            for c in estado.claims
            if c.autor is Capacidad.DIAGNOSTICAR and c.vigencia.vigente
        }
        assert interpretaciones == {
            "dominio(bucles)": False,
            "dominio(variables)": True,
            "dominio(condicionales)": False,
        }
        senales = [
            f for f in estado.facts
            if f.autor is Capacidad.TUTORIZAR and f.vigencia.vigente
        ]
        assert len(senales) == 3
        assert len(estado.deliberaciones) == 1
        assert len(estado.decisiones) == 1

    def test_evidencia_en_invocaciones_separadas_tambien_completa_el_mapa(self, esquema):
        """El caso real del diagnóstico de la plataforma: un hecho por
        invocación. La primera decide; las siguientes YA NO congelan el
        paisaje — cada tema nuevo queda interpretado, sin segunda
        decisión (mitad restante de Parte G)."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-mapa-2")
        for competencia, incorrectos in (
            ("algoritmos", [0, 1, 2]),
            ("variables", []),
            ("funciones", [0, 1]),
        ):
            final = ejecutar_walkthrough(
                almacen, identidad, (_hecho(competencia, incorrectos),)
            )
        estado = final["estado"]
        asuntos = {
            c.asunto
            for c in estado.claims
            if c.autor is Capacidad.DIAGNOSTICAR and c.vigencia.vigente
        }
        assert asuntos == {
            "dominio(algoritmos)", "dominio(variables)", "dominio(funciones)",
        }
        assert len(estado.decisiones) == 1  # jamás una segunda decisión
        propuestas_siguiente_paso = [
            c
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA
            and c.vigencia.vigente
            and c.asunto == "siguiente-paso(sesion)"
        ]
        assert len(propuestas_siguiente_paso) == 1  # sin re-propuestas tras decidir

    def test_hecho_no_evaluable_sigue_sin_ciclar_con_decision_previa(self, esquema):
        """Regresión del precedente GraphRecursionError: tras la
        decisión, una interacción no evaluable (pregunta al tutor) no
        dispara diagnosticar ni cicla — termina en END."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-mapa-3")
        ejecutar_walkthrough(almacen, identidad, (_hecho("bucles", [0, 1]),))
        final = ejecutar_walkthrough(
            almacen,
            identidad,
            (
                TransitionIntent(
                    productor=Capacidad.EVALUAR,
                    operacion="registrar_fact",
                    argumentos={
                        "autor": Capacidad.EVALUAR,
                        "contenido": {"interaccion": "pregunta-tutor", "pregunta": "?"},
                        "provenance": Provenance.de(OrigenProvenance.HUMANO),
                    },
                    base=0,
                ),
            ),
        )
        estado = final["estado"]
        assert len(estado.decisiones) == 1
        interpretaciones = [
            c
            for c in estado.claims
            if c.autor is Capacidad.DIAGNOSTICAR and c.vigencia.vigente
        ]
        assert len(interpretaciones) == 1  # la interacción no se "interpreta"
