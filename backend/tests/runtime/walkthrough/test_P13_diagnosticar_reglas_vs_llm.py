"""Guardián de P13 (ADR-0005 §7): una capacidad cambia de implementación
sin que el contrato — ni el runtime — se enteren.

Dos niveles de evidencia:
(1) comparación de CONTRATO entre producir() y producir_llm() sobre el
    mismo estado — tipo, asunto, forma del respaldo, tipo de confianza;
    JAMÁS el contenido (RFC-0002 §2: la capacidad, no su implementación,
    es lo estable).
(2) el Walkthrough-0001 COMPLETO corriendo con DiagnosticarLLM en el
    lugar de DiagnosticarReglas — mismo grafo, mismo scheduler, mismos
    reducers, mismo checkpoint — para demostrar que el runtime no lo
    distingue.
"""

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.domain.diagnosticar import FakeLLMProvider, producir, producir_llm
from runtime.engine.checkpoint import AlmacenTransiciones, verificar
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.entries import (
    Capacidad,
    EntryId,
    FactEntry,
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


def _pg_disponible() -> bool:
    try:
        psycopg2.connect(_URL, connect_timeout=3).close()
        return True
    except Exception:
        return False


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_fact() -> LearningState:
    fact = FactEntry(
        id=EntryId(1, 1),
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    return LearningState(
        identidad=_identidad("s-p13-contrato"),
        contexto={"ruta": "condicionales"},
        facts=(fact,),
        transicion=1,
    )


class TestP13_ContratoCompartido:
    def test_mismo_tipo_asunto_y_forma_de_respaldo(self):
        estado = _estado_con_fact()
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.DIAGNOSTICAR
            assert intent.argumentos["tipo"] is TipoClaim.INTERPRETACION
            assert intent.argumentos["asunto"] == "dominio(COMP-2)"
            assert intent.argumentos["respaldo"] == (EntryId(1, 1),)
            assert isinstance(intent.argumentos["confianza"], Decimal)

        # La única diferencia contractual ES el origen — por diseño.
        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_el_contenido_puede_diferir_libremente(self):
        # El contrato no exige contenido idéntico — solo forma idéntica.
        estado = _estado_con_fact()
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())
        # Ambos concuerdan aquí porque el fake espeja la regla — pero el
        # test no lo EXIGE; solo lo permite. La forma es lo verificado.
        assert set(intent_regla.argumentos["afirmacion"]) <= {
            "dominada",
            "errores",
        }
        assert "razonamiento" in intent_llm.argumentos["afirmacion"]


@pytest.mark.skipif(not _pg_disponible(), reason="PostgreSQL no disponible")
class TestP13_WalkthroughConCapacidadIntercambiada:
    @pytest.fixture
    def esquema(self):
        nombre = f"runtime_p13_{os.getpid()}"
        yield nombre
        with psycopg2.connect(_URL) as conexion, conexion.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {nombre} CASCADE")

    def _hecho(self) -> tuple[TransitionIntent, ...]:
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

    def test_el_runtime_no_distingue_la_capacidad_llm_de_la_regla(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-p13-grafo"),
            self._hecho(),
            productor_diagnostico=producir_llm,  # ← la ÚNICA diferencia
        )
        estado = final["estado"]

        # Mismas propiedades estructurales que test_walkthrough_0001:
        # mismo número de transiciones, misma forma de tensión,
        # deliberación, decisión — el contenido puede variar, la FORMA no.
        assert estado.transicion == 7  # PR-5: +Adaptar
        assert len(final["registros"]) == 7
        assert verificar(_identidad("s-p13-grafo"), final["registros"]) is None

        interpretacion = next(
            c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION
        )
        assert interpretacion.autor is Capacidad.DIAGNOSTICAR
        assert interpretacion.provenance.origen == OrigenProvenance.LLM  # ← cambió

        deliberacion = estado.deliberaciones[0]
        assert len(deliberacion.participantes) == 2
        assert isinstance(deliberacion.resultado, Resuelta)

        decision = estado.decisiones[0]
        assert decision.origen == deliberacion.id
        assert decision.asunto == "siguiente-paso(sesion)"
