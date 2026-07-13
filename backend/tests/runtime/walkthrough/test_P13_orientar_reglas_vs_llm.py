"""Guardián de P13 para Orientar (ADR-0005 §7) — mismo patrón que
Diagnosticar y Remediar (tercera capacidad; M2 3/7).
"""

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.domain.orientar import FakeLLMProvider, producir, producir_llm
from runtime.engine.checkpoint import AlmacenTransiciones, verificar
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
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


def _estado_con_interpretacion() -> LearningState:
    interpretacion = ClaimEntry(
        id=EntryId(2, 1),
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False, "errores": 3},
        respaldo=(EntryId(1, 1),),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    return LearningState(
        identidad=_identidad("s-p13-orientar-contrato"),
        contexto={"ruta": "condicionales"},
        claims=(interpretacion,),
        transicion=2,
    )


class TestP13_OrientarContratoCompartido:
    def test_mismo_tipo_asunto_y_forma_de_respaldo(self):
        estado = _estado_con_interpretacion()
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.ORIENTAR
            assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
            assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"
            assert intent.argumentos["respaldo"] == (EntryId(2, 1),)
            assert isinstance(intent.argumentos["confianza"], Decimal)
            assert "accion" in intent.argumentos["afirmacion"]

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM


@pytest.mark.skipif(not _pg_disponible(), reason="PostgreSQL no disponible")
class TestP13_WalkthroughConOrientarIntercambiado:
    @pytest.fixture
    def esquema(self):
        nombre = f"runtime_p13_ori_{os.getpid()}"
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

    def test_el_runtime_no_distingue_orientar_llm_de_regla(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-p13-ori-grafo"),
            self._hecho(),
            productor_orientar=producir_llm,  # ← la ÚNICA diferencia
        )
        estado = final["estado"]

        assert estado.transicion == 7  # PR-5: +Adaptar
        assert len(final["registros"]) == 7
        assert verificar(_identidad("s-p13-ori-grafo"), final["registros"]) is None

        propuesta_orientar = next(
            c
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA and c.autor is Capacidad.ORIENTAR
        )
        assert propuesta_orientar.provenance.origen == OrigenProvenance.LLM

        deliberacion = estado.deliberaciones[0]
        assert isinstance(deliberacion.resultado, Resuelta)
        decision = estado.decisiones[0]
        assert decision.origen == deliberacion.id

    def test_todas_las_tres_capacidades_llm_simultaneamente(self, esquema):
        # M2 exige: cada una intercambiable INDEPENDIENTEMENTE. Aquí las
        # tres a la vez — el grafo tampoco distingue la combinación.
        from runtime.domain.diagnosticar import producir_llm as diag_llm
        from runtime.domain.remediar import producir_llm as rem_llm

        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-p13-todas-llm"),
            self._hecho(),
            productor_diagnostico=diag_llm,
            productor_remediar=rem_llm,
            productor_orientar=producir_llm,
        )
        estado = final["estado"]
        assert estado.transicion == 7  # PR-5: +Adaptar
        assert verificar(_identidad("s-p13-todas-llm"), final["registros"]) is None
        assert all(
            c.provenance.origen == OrigenProvenance.LLM
            for c in estado.claims
            if c.autor in (Capacidad.DIAGNOSTICAR, Capacidad.REMEDIAR, Capacidad.ORIENTAR)
        )
        assert isinstance(estado.deliberaciones[0].resultado, Resuelta)
        assert estado.decisiones[0].origen == estado.deliberaciones[0].id
