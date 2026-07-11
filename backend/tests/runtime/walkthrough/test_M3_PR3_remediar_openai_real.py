"""M3 PR-3 — Remediar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior ("¿Qué acción de remediación
recomiendas? Responde JSON.") no especificaba ninguna forma. 8/8
sondeos reales devolvieron una estructura anidada
`{"recomendacion": {"accion": "...", "detalles": {...}}}` — nunca los
campos `accion`/`confianza` en el nivel raíz que `ejecutar_roundtrip`
exige. Contra un proveedor real, Remediar-LLM lanzaba
`ValueError: ADR-0004 E-2` el 100% de las veces.

Causa raíz: la regla de Remediar SIEMPRE propone literalmente
`"reforzar"` (espacio de un solo valor, sin alternativa) — el prompt
nunca se lo decía al modelo, así que no había vocabulario que respetar.
Corregido especificando la forma (razonamiento → accion → confianza,
mismo patrón de PR-2) y restringiendo `accion` al único valor que la
regla ya usa — no es vocabulario nuevo, es hacer explícito lo que la
regla ya impone.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.remediar import FakeLLMProvider, producir_llm
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
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
        identidad=Identidad(
            session_id="s-m3-pr3",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
        claims=(interpretacion,),
        transicion=2,
    )


def _assert_contrato(intent) -> None:
    assert intent.operacion == "registrar_claim"
    assert intent.argumentos["autor"] is Capacidad.REMEDIAR
    assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
    assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"
    assert intent.argumentos["respaldo"] == (EntryId(2, 1),)
    assert isinstance(intent.argumentos["confianza"], Decimal)
    assert intent.argumentos["provenance"].origen == OrigenProvenance.LLM
    assert "accion" in intent.argumentos["afirmacion"]


class TestM3_PR3_RemediarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_interpretacion()
        # Antes del fix esto lanzaba ValueError (ADR-0004 E-2) el 100%
        # de las veces — la sola ausencia de excepción ya es evidencia.
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato(intent)


class TestM3_PR3_EstabilidadDelContratoYDelVocabulario:
    def test_diez_corridas_reales_mismo_contrato_y_accion_reforzar(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_interpretacion()
        for _ in range(10):
            (intent_fake,) = producir_llm(estado, proveedor=FakeLLMProvider())
            (intent_real,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato(intent_fake)
            _assert_contrato(intent_real)
            # El vocabulario de la regla es un espacio de un solo valor
            # (productor.py: siempre "reforzar") — P13 exige que la
            # versión LLM lo respete, no que lo reinvente.
            assert intent_real.argumentos["afirmacion"]["accion"] == "reforzar"
