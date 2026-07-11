"""M3 PR-2 — Diagnosticar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, memoria del
proyecto): con el prompt de PR-1 (que pedía "dominada" ANTES que
"razonamiento") y temperature por defecto de la API, Diagnosticar-LLM
contradecía la política scoring-v1 hasta la mitad de las veces — en un
caso, el propio campo `razonamiento` concluía correctamente y el campo
`dominada` decía lo contrario en la MISMA respuesta.

Corregido reordenando el prompt (razonamiento → errores → dominada →
confianza, razonar antes de concluir) y fijando `temperature=0` en
`OpenAIProvider`. Este archivo es la evidencia: 10 corridas reales
verificando que el CONTRATO (P13) se sostiene, más un barrido de
`errores` a ambos lados del umbral de `scoring-v1` verificando que el
VEREDICTO de dominio también se sostiene — no solo la forma del claim.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.diagnosticar import FakeLLMProvider, producir_llm
from runtime.domain.diagnosticar.productor import _UMBRAL_ERRORES
from runtime.kernel.state.entries import (
    Capacidad,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)


def _estado_con_errores(errores: int) -> LearningState:
    fact = FactEntry(
        id=EntryId(1, 1),
        autor=Capacidad.EVALUAR,
        contenido={
            "competencia": "COMP-2",
            "items_incorrectos": list(range(errores)),
        },
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    return LearningState(
        identidad=Identidad(
            session_id=f"s-m3-pr2-{errores}",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
        facts=(fact,),
        transicion=1,
    )


def _assert_contrato(intent) -> None:
    assert intent.operacion == "registrar_claim"
    assert intent.argumentos["autor"] is Capacidad.DIAGNOSTICAR
    assert intent.argumentos["tipo"] is TipoClaim.INTERPRETACION
    assert intent.argumentos["asunto"] == "dominio(COMP-2)"
    assert intent.argumentos["respaldo"] == (EntryId(1, 1),)
    assert isinstance(intent.argumentos["confianza"], Decimal)
    assert intent.argumentos["provenance"].origen == OrigenProvenance.LLM
    assert "dominada" in intent.argumentos["afirmacion"]
    assert "errores" in intent.argumentos["afirmacion"]


class TestM3_PR2_EstabilidadDelContrato:
    def test_diez_corridas_reales_mismo_contrato_fake_y_openai(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_errores(3)
        for _ in range(10):
            (intent_fake,) = producir_llm(estado, proveedor=FakeLLMProvider())
            (intent_real,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato(intent_fake)
            _assert_contrato(intent_real)
        # El contrato es idéntico en las 10 corridas (P13); el contenido
        # puede diferir libremente — lo que NO puede es la forma.


class TestM3_PR2_VeredictoConsistenteConLaPolitica:
    @pytest.mark.parametrize("errores", [0, 1, _UMBRAL_ERRORES, _UMBRAL_ERRORES + 1, 5])
    def test_dominada_coincide_con_scoring_v1(self, errores: int):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_errores(errores)
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        esperado = errores < _UMBRAL_ERRORES
        assert intent.argumentos["afirmacion"]["dominada"] == esperado, (
            f"errores={errores}: la política scoring-v1 esperaba "
            f"dominada={esperado}, el LLM real respondió "
            f"{intent.argumentos['afirmacion']['dominada']} — regresión "
            f"del hallazgo de PR-2 (razonamiento/conclusión desalineados)."
        )
