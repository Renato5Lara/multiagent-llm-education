"""M3 PR-1 — el proveedor real, verificado contra la API de verdad.

Dos niveles de evidencia (mismo criterio que los guardianes P13 ya
existentes, ADR-0005 §7):

(1) `OpenAIProvider` cumple el contrato `LLMResponse` — no interpreta
    nada de dominio, solo demuestra que la infraestructura de red/JSON
    mode/reintentos funciona de punta a punta.
(2) el mismo productor (`domain.diagnosticar.producir_llm`) sobre el
    MISMO estado, una vez con `FakeLLMProvider` y una vez con
    `OpenAIProvider` — produce el mismo CONTRATO de claim (tipo, asunto,
    forma de respaldo, tipo de confianza, origen=LLM). El contenido
    puede diferir libremente (P13); la forma no.

Ambos tests hacen una llamada real de red y se saltan sin
`OPENAI_API_KEY` — no corren en CI sin credenciales (mismo patrón que
`_pg_disponible()` para PostgreSQL).
"""

from __future__ import annotations

import json
import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.diagnosticar import FakeLLMProvider, producir_llm
from runtime.domain.shared.llm import LLMResponse
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
_TIENE_CREDENCIAL = bool(os.environ.get("OPENAI_API_KEY"))

pytestmark = pytest.mark.skipif(
    not _TIENE_CREDENCIAL, reason="OPENAI_API_KEY no configurada"
)


def _estado_con_fact() -> LearningState:
    fact = FactEntry(
        id=EntryId(1, 1),
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    return LearningState(
        identidad=Identidad(
            session_id="s-m3-pr1",
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


class TestM3_OpenAIProviderContrato:
    def test_generar_devuelve_una_LLMResponse_con_json_valido(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        proveedor = OpenAIProvider()
        respuesta = proveedor.generar(
            'Responde únicamente JSON con la forma {"eco": "hola"}.'
        )
        assert isinstance(respuesta, LLMResponse)
        datos = json.loads(respuesta.texto)
        assert "eco" in datos
        assert respuesta.usage is not None
        assert respuesta.usage["total_tokens"] > 0
        assert respuesta.latencia_ms is not None and respuesta.latencia_ms > 0
        assert respuesta.finish_reason is not None


class TestM3_P13_FakeVsOpenAI_Diagnosticar:
    def test_mismo_productor_mismo_contrato_fake_y_openai(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_fact()
        (intent_fake,) = producir_llm(estado, proveedor=FakeLLMProvider())
        (intent_real,) = producir_llm(estado, proveedor=OpenAIProvider())

        for intent in (intent_fake, intent_real):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.DIAGNOSTICAR
            assert intent.argumentos["tipo"] is TipoClaim.INTERPRETACION
            assert intent.argumentos["asunto"] == "dominio(COMP-2)"
            assert intent.argumentos["respaldo"] == (EntryId(1, 1),)
            assert isinstance(intent.argumentos["confianza"], Decimal)
            assert intent.argumentos["provenance"].origen == OrigenProvenance.LLM
            assert "dominada" in intent.argumentos["afirmacion"]
            assert "errores" in intent.argumentos["afirmacion"]

        # Lo único que el contrato NO exige es contenido idéntico — la
        # prueba científica de P13 es la forma, no el veredicto.
