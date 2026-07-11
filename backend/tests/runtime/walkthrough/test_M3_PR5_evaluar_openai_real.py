"""M3 PR-5 — Evaluar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior
("items_incorrectos=[...] total=N. Confirma el conteo. Responde JSON.")
no especificaba forma — 8/8 sondeos reales devolvieron el campo `total`
en vez de `items_totales`, y además el modelo malinterpretó la
semántica de `total` (lo comparó contra la cantidad de incorrectos y
declaró `"conteo_correcto": false`). Contra un proveedor real,
`ejecutar_roundtrip` lanzaba `ValueError` (ADR-0004 E-2) el 100% de las
veces — mismo patrón de forma que Diagnosticar/Remediar/Orientar
(PR-2/3/4).

Hallazgo adicional, distinto de las tres capacidades anteriores y más
importante que el formato: Evaluar produce un FACT, no un claim
(RFC-0002 fila Evaluar; RFC-0003 §1, "un fact solo puede ser cuestionado
por un nuevo fact — nunca por una opinión"). El código anterior
construía el `contenido` del fact con `respuesta["items_incorrectos"]`/
`respuesta["items_totales"]` — lo que dijera el modelo —, no con el
conteo determinista ya calculado por `producir_llm` a partir de
`respuestas`. Eso contradecía el propio docstring de `provider.py`
("el proveedor no interpreta nada nuevo: confirma un conteo ya
determinado") y abría la puerta a que una alucinación del modelo se
registrara como observación objetiva.

Fix: (1) forma del prompt explícita (razonamiento → items_incorrectos →
items_totales, con la semántica de `items_totales` aclarada), igual
patrón que PR-2/3/4; (2) grounding — el roundtrip solo valida que el
proveedor responde con la forma esperada; el `contenido` del fact se
construye siempre con los valores deterministas ya calculados, nunca
con los que devuelve el modelo.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from runtime.domain.evaluar import producir, producir_llm
from runtime.domain.shared.llm import LLMResponse
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)

_RESPUESTAS = {1: True, 2: True, 3: False, 4: False, 5: True, 8: False}


def _estado() -> LearningState:
    return LearningState(
        identidad=Identidad(
            session_id="s-m3-pr5",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
    )


def _assert_contrato_y_grounding(intent) -> None:
    assert intent.operacion == "registrar_fact"
    contenido = intent.argumentos["contenido"]
    assert set(contenido) == {"competencia", "items_incorrectos", "items_totales"}
    # El fact debe coincidir con el cálculo determinista, sin importar
    # qué haya dicho el modelo — grounding, no confianza en el LLM.
    assert contenido["items_incorrectos"] == [3, 4, 8]
    assert contenido["items_totales"] == 6


class TestM3_PR5_EvaluarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado()
        # Antes del fix esto lanzaba ValueError (ADR-0004 E-2) el 100%
        # de las veces — la sola ausencia de excepción ya es evidencia.
        (intent,) = producir_llm(
            estado, _RESPUESTAS, competencia="COMP-2", proveedor=OpenAIProvider()
        )
        _assert_contrato_y_grounding(intent)


class TestM3_PR5_EstabilidadDelContratoYDelVocabulario:
    def test_diez_corridas_reales_mismo_contrato_y_grounding(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        for _ in range(10):
            estado = _estado()
            (intent_real,) = producir_llm(
                estado,
                _RESPUESTAS,
                competencia="COMP-2",
                proveedor=OpenAIProvider(),
            )
            _assert_contrato_y_grounding(intent_real)


class TestM3_PR5_GroundingContraUnProveedorQueAlucina:
    def test_fact_ignora_valores_divergentes_del_proveedor(self):
        """No requiere red: demuestra el grounding con un proveedor fake
        que devuelve deliberadamente un conteo distinto al real — si el
        fact reflejara la respuesta del modelo (regresión al bug de
        origen), esta prueba fallaría."""

        class ProveedorQueAlucina:
            modelo = "fake-alucinado-v1"
            version = "1"

            def generar(self, prompt: str) -> LLMResponse:
                return LLMResponse(
                    texto=(
                        '{"razonamiento": "conteo distinto", '
                        '"items_incorrectos": [1, 2], "items_totales": 99}'
                    )
                )

        estado = _estado()
        (intent_regla,) = producir(estado, _RESPUESTAS, competencia="COMP-2")
        (intent_llm,) = producir_llm(
            estado, _RESPUESTAS, competencia="COMP-2", proveedor=ProveedorQueAlucina()
        )
        _assert_contrato_y_grounding(intent_llm)
        assert (
            intent_llm.argumentos["contenido"]
            == intent_regla.argumentos["contenido"]
        )
