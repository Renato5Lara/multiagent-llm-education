"""Calibración de confianza declarada de Orientar-LLM — ADR-0013. Pura,
sin Postgres, sin LLM real: aísla el cálculo de `evidence_strength` sobre
la evidencia real que la propuesta respalda (mismo patrón que
tests/runtime/domain/remediar/test_calibracion_llm.py)."""

from decimal import Decimal

from runtime.domain.orientar import FakeLLMProvider, producir_llm
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
        identidad=_identidad(f"s-orientar-calib-{errores}-{total}"),
        contexto={},
        facts=(fact,),
        claims=(interpretacion,),
        transicion=2,
    )


class TestOrientarConfianzaCalibrada:
    def test_confianza_es_evidence_strength_sobre_aciertos_no_valor_crudo(self):
        """"avanzar-con-andamiaje" es optimista sobre el DOMINIO: la
        fuerza se mide sobre aciertos/total (total-errores), no sobre
        errores/total como en Remediar (ADR-0013 §2.2)."""
        estado = _estado_con_evidencia(errores=1, total=4)  # 3 aciertos de 4
        (intent,) = producir_llm(estado, proveedor=FakeLLMProvider())
        esperado = evidence_strength(soporte=3, total=4)
        assert intent.argumentos["confianza"] == esperado

    def test_deja_de_ser_constante_ante_dominada_true_vs_false(self):
        """Hallazgo central de Auditoría 5: Orientar-LLM declaraba 0.85
        en 9/9 corridas, sin distinguir `dominada: True` de `False`.
        Calibrado, dominio fuerte (pocos errores) debe declarar más
        confianza que dominio débil (muchos errores), sobre la misma
        `total`."""
        estado_domina = _estado_con_evidencia(errores=0, total=8)  # 8/8 aciertos
        estado_falla = _estado_con_evidencia(errores=7, total=8)  # 1/8 aciertos
        (intent_domina,) = producir_llm(estado_domina, proveedor=FakeLLMProvider())
        (intent_falla,) = producir_llm(estado_falla, proveedor=FakeLLMProvider())
        assert (
            intent_domina.argumentos["confianza"]
            > intent_falla.argumentos["confianza"]
        )

    def test_sin_fact_respaldando_degrada_a_cero_sin_crashear(self):
        """Contrato sintético (mismo patrón que
        test_P13_orientar_reglas_vs_llm.py): `respaldo` apunta a un
        EntryId que no existe en el estado — debe degradar a 0, nunca
        lanzar."""
        interpretacion = ClaimEntry(
            id=EntryId(2, 1),
            autor=Capacidad.DIAGNOSTICAR,
            tipo=TipoClaim.INTERPRETACION,
            asunto="dominio(COMP-2)",
            afirmacion={"dominada": True, "errores": 0},
            respaldo=(EntryId(1, 1),),
            confianza=Decimal("0.78"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
        )
        estado = LearningState(
            identidad=_identidad("s-orientar-sin-fact"),
            contexto={},
            claims=(interpretacion,),
            transicion=2,
        )
        (intent,) = producir_llm(estado, proveedor=FakeLLMProvider())
        assert intent.argumentos["confianza"] == Decimal("0")
