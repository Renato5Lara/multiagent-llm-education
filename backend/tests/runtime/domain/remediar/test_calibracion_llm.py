"""Calibración de confianza declarada de Remediar-LLM — ADR-0013. Pura,
sin Postgres, sin LLM real: aísla el cálculo de `evidence_strength` sobre
la evidencia real que la propuesta respalda (mismo patrón que
tests/runtime/domain/diagnosticar/test_calibracion.py)."""

from decimal import Decimal

from runtime.domain.remediar import FakeLLMProvider, producir_llm
from runtime.domain.shared.calibracion import evidence_strength
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_evidencia(errores: int, total: int) -> LearningState:
    fact = FactEntry(
        id=EntryId(1, 1),
        autor=Capacidad.EVALUAR,
        contenido={
            "competencia": "COMP-2",
            "items_incorrectos": list(range(errores)),
            "items_totales": total,
        },
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    interpretacion = ClaimEntry(
        id=EntryId(2, 1),
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": errores < 2, "errores": errores},
        respaldo=(fact.id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    return LearningState(
        identidad=_identidad(f"s-remediar-calib-{errores}-{total}"),
        contexto={},
        facts=(fact,),
        claims=(interpretacion,),
        transicion=2,
    )


class TestRemediarConfianzaCalibrada:
    def test_confianza_es_evidence_strength_no_valor_crudo_del_llm(self):
        """FakeLLMProvider siempre declara "0.85" — si la confianza final
        coincidiera, sería el valor crudo sin calibrar. Debe coincidir en
        cambio con `evidence_strength(errores, total)` (ADR-0013 §2.2)."""
        estado = _estado_con_evidencia(errores=3, total=4)
        (intent,) = producir_llm(estado, proveedor=FakeLLMProvider())
        esperado = evidence_strength(soporte=3, total=4)
        assert intent.argumentos["confianza"] == esperado
        assert intent.argumentos["confianza"] != Decimal("0.85")

    def test_severidad_distinta_produce_confianza_distinta(self):
        """Hallazgo de Auditoría 5 a corregir: con el camino sin calibrar,
        Remediar-LLM variaba menos entre severidades distintas que entre
        corridas de la MISMA evidencia. Calibrado, un fallo más severo
        debe declarar más confianza en "reforzar"."""
        estado_leve = _estado_con_evidencia(errores=2, total=8)
        estado_severo = _estado_con_evidencia(errores=7, total=8)
        (intent_leve,) = producir_llm(estado_leve, proveedor=FakeLLMProvider())
        (intent_severo,) = producir_llm(estado_severo, proveedor=FakeLLMProvider())
        assert (
            intent_severo.argumentos["confianza"]
            > intent_leve.argumentos["confianza"]
        )

    def test_sin_fact_respaldando_degrada_a_cero_sin_crashear(self):
        """Contrato sintético (mismo patrón que
        test_P13_remediar_reglas_vs_llm.py): `respaldo` apunta a un
        EntryId que no existe en el estado — `estado.buscar` devuelve
        `None`, la calibración debe degradar a 0, nunca lanzar."""
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
        estado = LearningState(
            identidad=_identidad("s-remediar-sin-fact"),
            contexto={},
            claims=(interpretacion,),
            transicion=2,
        )
        (intent,) = producir_llm(estado, proveedor=FakeLLMProvider())
        assert intent.argumentos["confianza"] == Decimal("0")
