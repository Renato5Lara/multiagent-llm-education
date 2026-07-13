"""RFC-0006/4b, Parte E sobre el grafo real — LangGraph + Postgres.

Complementa `tests/runtime/deliberation/test_parteE_aplazamiento_provisional.py`
(que prueba la mecánica pura): aquí se prueba lo que solo el grafo puede
probar — que un aplazamiento real NO produce `GraphRecursionError` (el
precedente que motivó las guardias PR-2..PR-5), que la sesión termina en
`END` esperando evidencia, que con `urgente=True` el walkthrough continúa
solo hasta Adaptar, y que una `Aplazada` sobrevive el round-trip de
persistencia/reconstrucción (RFC-0008 §3) sin duplicarse al reanudar.

La política con δ real no existe en producción (v1 tiene delta=0, que
hace la Parte E estructuralmente inalcanzable): se registra una política
de prueba vía monkeypatch — el mecanismo es real, la configuración es
del test (mismo criterio que las Partes C/D usan a nivel mecánica).
"""

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.engine.checkpoint import AlmacenTransiciones
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.deliberation.mecanica import REGLA_PROVISIONAL
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    OrigenProvenance,
    Provenance,
    Resuelta,
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

_VERSION_POLITICA_TEST = "parteE-delta-test"

_POLITICA_DELTA_REAL = Politica(
    peso_refuerzo=Decimal("0"),
    peso_refutacion=Decimal("0"),
    peso_decaimiento=Decimal("0"),
    theta=Decimal("0"),
    # Ningún margen entre dos confianzas de regla reales alcanza 0.99:
    # garantiza que la tensión D2 viva (Remediar vs Orientar sobre
    # "siguiente-paso(sesion)") caiga en la rama de la Parte E.
    delta=Decimal("0.99"),
)


@pytest.fixture(autouse=True)
def _politica_de_prueba(monkeypatch):
    monkeypatch.setitem(POLITICAS, _VERSION_POLITICA_TEST, _POLITICA_DELTA_REAL)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica=_VERSION_POLITICA_TEST,
        spec_version="foundation-2026-07-10",
    )


def _hecho_del_mundo() -> tuple[TransitionIntent, ...]:
    return (
        TransitionIntent(
            productor=Capacidad.EVALUAR,
            operacion="registrar_fact",
            argumentos={
                "autor": Capacidad.EVALUAR,
                "contenido": {
                    "competencia": "COMP-2",
                    "items_incorrectos": [3, 4, 8],
                },
                "provenance": Provenance.de(
                    OrigenProvenance.INSTRUMENTO, banco="v2"
                ),
            },
            base=0,
        ),
    )


@pytest.fixture
def esquema():
    nombre = f"runtime_parte_e_{os.getpid()}"
    yield nombre
    with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")


class TestAplazamientoEnElGrafo:
    def test_margen_insuficiente_termina_en_end_sin_ciclar(self, esquema):
        """El riesgo estructural de la Parte E: una deliberación sin
        decisión derivable no puede enrutar a "decidir" (ciclo) ni
        reconvocarse (duplicados). Que este test termine ya prueba que
        no hubo `GraphRecursionError`; lo demás verifica el paisaje."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen, _identidad("s-parteE-aplaza"), _hecho_del_mundo()
        )
        estado = final["estado"]
        aplazadas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Aplazada)
        ]
        assert len(aplazadas) == 1  # una sola — sin reconvocatoria espuria
        assert estado.decisiones == ()  # espera evidencia, no decide a ciegas
        # los rivales siguen vigentes esperando la evidencia declarada
        for ref in aplazadas[0].participantes:
            assert estado.buscar(ref).vigencia.vigente

    def test_reanudar_preserva_la_aplazada_sin_duplicarla(self, esquema):
        """Round-trip RFC-0008 §3: la `Aplazada` persistida se
        reconstruye tal cual al reanudar, y la reanudación sin evidencia
        nueva no vuelve a convocar (la reconvocatoria es Parte F)."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        identidad = _identidad("s-parteE-reanuda")
        ejecutar_walkthrough(almacen, identidad, _hecho_del_mundo())

        final = ejecutar_walkthrough(almacen, identidad, hechos_del_mundo=())
        estado = final["estado"]
        aplazadas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Aplazada)
        ]
        assert len(aplazadas) == 1
        assert "siguiente-paso(sesion)" in aplazadas[0].resultado.evidencia_faltante
        assert estado.decisiones == ()

    def test_urgente_resuelve_provisional_y_el_walkthrough_continua(self, esquema):
        """CONCEPT-0002 §4: "la provisionalidad es para el estudiante" —
        con alguien esperando en la pantalla, el mismo paisaje que antes
        se aplazó ahora deriva decisión provisional y Adaptar continúa
        solo, exactamente como tras una resolución plena."""
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-parteE-urgente"),
            _hecho_del_mundo(),
            urgente=True,
        )
        estado = final["estado"]
        resueltas = [
            d for d in estado.deliberaciones if isinstance(d.resultado, Resuelta)
        ]
        assert len(resueltas) == 1
        assert resueltas[0].resultado.regla == REGLA_PROVISIONAL
        assert len(estado.decisiones) == 1
        assert any(
            c.autor is Capacidad.ADAPTAR and c.vigencia.vigente
            for c in estado.claims
        )
