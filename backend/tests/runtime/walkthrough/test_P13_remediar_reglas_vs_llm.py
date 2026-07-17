"""Guardián de P13 para Remediar (ADR-0005 §7) — mismo patrón que
Diagnosticar (test_P13_diagnosticar_reglas_vs_llm.py).
"""

import os
from decimal import Decimal

import psycopg2
import pytest

from runtime.domain.remediar import FakeLLMProvider, producir, producir_llm
from runtime.engine.checkpoint import AlmacenTransiciones, verificar
from runtime.engine.graph import ejecutar_walkthrough
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_deliberacion, registrar_fact
from runtime.kernel.state.entries import (
    Capacidad,
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
    from runtime.kernel.state.entries import ClaimEntry

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
        identidad=_identidad("s-p13-remediar-contrato"),
        contexto={"ruta": "condicionales"},
        claims=(interpretacion,),
        transicion=2,
    )


class TestP13_RemediarContratoCompartido:
    def test_mismo_tipo_asunto_y_forma_de_respaldo(self):
        estado = _estado_con_interpretacion()
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.REMEDIAR
            assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
            assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"
            assert intent.argumentos["respaldo"] == (EntryId(2, 1),)
            assert isinstance(intent.argumentos["confianza"], Decimal)
            assert "accion" in intent.argumentos["afirmacion"]

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM


class TestP13_RemediarAntiChurn:
    """Regresión real encontrada al conectar Remediar-LLM al Sprint 3.4:
    `producir_llm` usaba `ya_propuse = any(vigente)` — una guardia más
    laxa que `palabra_en_pie` de la versión regla. Tras perder una D2
    limpiamente (el vencedor sigue vigente), la propuesta de Remediar
    deja de estar vigente, así que `ya_propuse` pasaba a False y el
    productor LLM volvía a proponer en la siguiente activación SIN
    evidencia nueva — exactamente el churn que `palabra_en_pie` existe
    para evitar (anti-churn, ciclo adaptativo continuo 2026-07-13)."""

    def _estado_remediar_perdio_limpio(self) -> LearningState:
        estado = LearningState(
            identidad=_identidad("s-p13-remediar-churn"),
            contexto={"ruta": "condicionales"},
        )
        r = registrar_fact(
            estado,
            autor=Capacidad.EVALUAR,
            contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        r = registrar_claim(
            estado,
            autor=Capacidad.DIAGNOSTICAR,
            tipo=TipoClaim.INTERPRETACION,
            asunto="dominio(COMP-2)",
            afirmacion={"dominada": False, "errores": 3},
            respaldo=(estado.facts[0].id,),
            confianza=Decimal("0.78"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        interpretacion_id = estado.claims[-1].id

        r = registrar_claim(
            estado,
            autor=Capacidad.REMEDIAR,
            tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)",
            afirmacion={"accion": "reforzar"},
            respaldo=(interpretacion_id,),
            confianza=Decimal("0.60"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        remediar_id = estado.claims[-1].id

        r = registrar_claim(
            estado,
            autor=Capacidad.ORIENTAR,
            tipo=TipoClaim.PROPUESTA,
            asunto="siguiente-paso(sesion)",
            afirmacion={"accion": "avanzar-con-andamiaje"},
            respaldo=(interpretacion_id,),
            confianza=Decimal("0.90"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="ruta-v1"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        orientar_id = estado.claims[-1].id

        r = registrar_deliberacion(
            estado,
            participantes=(remediar_id, orientar_id),
            resultado=Resuelta(
                regla="mayor-confianza-declarada",
                aceptados=(orientar_id,),
                confianza=Decimal("0.90"),
            ),
        )
        assert isinstance(r, Aplicado)
        return r.estado

    def test_no_reproponer_tras_perder_limpio(self):
        estado = self._estado_remediar_perdio_limpio()
        remediar_vigente = next(
            c for c in estado.claims if c.autor is Capacidad.REMEDIAR
        )
        assert not remediar_vigente.vigencia.vigente  # perdió, quedó supersedido

        assert producir(estado) == ()  # la regla ya lo garantizaba
        assert producir_llm(estado, proveedor=FakeLLMProvider()) == ()


@pytest.mark.skipif(not _pg_disponible(), reason="PostgreSQL no disponible")
class TestP13_WalkthroughConRemediarIntercambiado:
    @pytest.fixture
    def esquema(self):
        nombre = f"runtime_p13_rem_{os.getpid()}"
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

    def test_el_runtime_no_distingue_remediar_llm_de_regla(self, esquema):
        almacen = AlmacenTransiciones(_URL, esquema=esquema)
        almacen.preparar()
        final = ejecutar_walkthrough(
            almacen,
            _identidad("s-p13-rem-grafo"),
            self._hecho(),
            productor_remediar=producir_llm,  # ← la ÚNICA diferencia
        )
        estado = final["estado"]

        assert estado.transicion == 7  # PR-5: +Adaptar
        assert len(final["registros"]) == 7
        assert verificar(_identidad("s-p13-rem-grafo"), final["registros"]) is None

        propuesta_remediar = next(
            c
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA and c.autor is Capacidad.REMEDIAR
        )
        assert propuesta_remediar.provenance.origen == OrigenProvenance.LLM

        deliberacion = estado.deliberaciones[0]
        assert isinstance(deliberacion.resultado, Resuelta)
        decision = estado.decisiones[0]
        assert decision.origen == deliberacion.id
