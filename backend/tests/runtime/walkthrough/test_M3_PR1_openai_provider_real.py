"""M3 PR-1 — el proveedor real, verificado contra la API de verdad.

`OpenAIProvider` cumple el contrato `LLMResponse` — no interpreta nada de
dominio, solo demuestra que la infraestructura de red/JSON mode/
reintentos funciona de punta a punta. La verificación específica de una
capacidad (Diagnosticar) contra el proveedor real vive en
`test_M3_PR2_diagnosticar_openai_real.py` — este archivo es
capacidad-agnóstico (infraestructura, PR-1), no domain-specific (PR-2).

Se salta sin `OPENAI_API_KEY` — no corre en CI sin credenciales (mismo
patrón que `_pg_disponible()` para PostgreSQL).
"""

from __future__ import annotations

import json
import os

import pytest
from dotenv import load_dotenv

from runtime.domain.shared.llm import LLMResponse

load_dotenv()
_TIENE_CREDENCIAL = bool(os.environ.get("OPENAI_API_KEY"))

pytestmark = pytest.mark.skipif(
    not _TIENE_CREDENCIAL, reason="OPENAI_API_KEY no configurada"
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
