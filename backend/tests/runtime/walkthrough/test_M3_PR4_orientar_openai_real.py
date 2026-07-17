"""M3 PR-4 — Orientar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior ("¿Conviene avanzar al
siguiente objetivo de la ruta? Responde JSON.") no especificaba forma —
8/8 sondeos reales devolvieron
`{"respuesta": {"interpretacion_vigente": true, "avanzar_siguiente_objetivo": false, "razon": "..."}}`,
nunca los campos `accion`/`confianza` de nivel raíz. Contra un proveedor
real, `ejecutar_roundtrip` lanzaba `ValueError` (ADR-0004 E-2) el 100%
de las veces — mismo patrón exacto que Remediar (PR-3).

Hallazgo adicional, más importante que el formato: el modelo interpretó
la pregunta como un juicio propio ("¿conviene avanzar?") y respondió con
una decisión propia (`avanzar_siguiente_objetivo: false`), cuando el
contrato del dominio establece que Orientar únicamente PROPONE — la
decisión entre esta propuesta y la de Remediar le corresponde a la
deliberación del Kernel (RFC-0002 §4, tensión canónica n.º 1). El
prompt desplazaba esa responsabilidad al LLM sin que el código lo
pidiera. Corregido aclarando explícitamente que la salida es una
candidata para la deliberación, no una decisión, además de especificar
la forma (razonamiento → accion → confianza) y restringir `accion` al
único valor que la regla ya usa.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.orientar import FakeLLMProvider, producir_llm
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
            session_id="s-m3-pr4",
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
    assert intent.argumentos["autor"] is Capacidad.ORIENTAR
    assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
    assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"
    assert intent.argumentos["respaldo"] == (EntryId(2, 1),)
    assert isinstance(intent.argumentos["confianza"], Decimal)
    assert intent.argumentos["provenance"].origen == OrigenProvenance.LLM
    assert "accion" in intent.argumentos["afirmacion"]


class TestM3_PR4_OrientarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_interpretacion()
        # Antes del fix esto lanzaba ValueError (ADR-0004 E-2) el 100%
        # de las veces — la sola ausencia de excepción ya es evidencia.
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato(intent)


class TestM3_PR4_EstabilidadDelContratoYDelVocabulario:
    def test_diez_corridas_reales_mismo_contrato_y_accion_avanzar(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_interpretacion()
        for _ in range(10):
            (intent_fake,) = producir_llm(estado, proveedor=FakeLLMProvider())
            (intent_real,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato(intent_fake)
            _assert_contrato(intent_real)
            # Espacio de un solo valor (productor.py: siempre
            # "avanzar-con-andamiaje") — P13 exige que la versión LLM lo
            # respete como PROPUESTA, no que decida por su cuenta.
            assert (
                intent_real.argumentos["afirmacion"]["accion"]
                == "avanzar-con-andamiaje"
            )
