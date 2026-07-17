"""M3 PR-6 — Tutorizar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior
("incorrectos=N total=M. Clasifica la señal conductual... Responde
JSON.") no especificaba forma — el modelo nunca devolvió el campo
`senal` (usó `clasificacion`, o estructuras completamente distintas).
Contra un proveedor real, `ejecutar_roundtrip` lanzaba `ValueError`
(ADR-0004 E-2) el 100% de las veces — mismo patrón de forma que
PR-2/3/4/5.

Hallazgo adicional, más grave que en Evaluar (PR-5): con la misma
evidencia que usa la regla (`incorrectos=3, total=6`), el modelo
devolvió `"frustracion"` donde la regla (`_senal()`,
`deteccion-conductual-v1`) exige `"confusion"` — el modelo no solo
falla en forma, contradice el umbral del dominio. En otro caso devolvió
vocabulario en inglés (`"frustration"`, `"fluency"`) fuera del
vocabulario cerrado que el guardián P13 protege.

`senal` es una función pura de datos ya presentes en el estado
(`incorrectos`/`total`, del fact de Evaluar) — igual que Evaluar con su
conteo. Fix: (1) forma del prompt explícita; (2) grounding — el
roundtrip valida solo forma/disponibilidad del proveedor; `senal` se
construye siempre con `_senal()` (reutilizada de `productor.py`, mismo
patrón de reuso que `diagnosticar/productor_llm.py` con
`_UMBRAL_ERRORES`) — nunca con lo que devuelve el modelo.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

from runtime.domain.shared.llm import LLMResponse
from runtime.domain.tutorizar import producir, producir_llm
from runtime.kernel.reducers import Aplicado, registrar_fact
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)


def _estado_con_evaluacion(incorrectos: list[int], total: int) -> LearningState:
    estado = LearningState(
        identidad=Identidad(
            session_id="s-m3-pr6",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
    )
    resultado = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={
            "competencia": "COMP-2",
            "items_incorrectos": incorrectos,
            "items_totales": total,
        },
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(resultado, Aplicado)
    return resultado.estado


def _assert_contrato_y_grounding(intent, senal_esperada: str) -> None:
    assert intent.operacion == "registrar_fact"
    contenido = intent.argumentos["contenido"]
    assert set(contenido) == {
        "senal",
        "fact_origen",
        "items_incorrectos",
        "items_totales",
    }
    # El fact debe coincidir con el umbral determinista, sin importar
    # qué haya dicho el modelo — grounding, no confianza en el LLM.
    assert contenido["senal"] == senal_esperada


class TestM3_PR6_TutorizarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        # Mismos números que expusieron la deriva semántica en el
        # sondeo: la regla exige "confusion".
        estado = _estado_con_evaluacion([3, 4, 8], 6)
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato_y_grounding(intent, "confusion")


class TestM3_PR6_EstabilidadDelContratoYDelVocabulario:
    def test_diez_corridas_reales_mismo_contrato_y_grounding(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        for _ in range(10):
            estado = _estado_con_evaluacion([3, 4, 8], 6)
            (intent_real,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato_y_grounding(intent_real, "confusion")


class TestM3_PR6_GroundingContraUnProveedorQueContradiceElDominio:
    def test_fact_ignora_senal_que_contradice_el_umbral_de_la_regla(self):
        """No requiere red. Reproduce exactamente el hallazgo del sondeo
        real: con incorrectos=3/total=6 la regla exige "confusion", pero
        el modelo real respondió "frustracion". Si el fact reflejara la
        respuesta del proveedor (regresión al bug de origen), esta
        prueba fallaría."""

        class ProveedorQueContradiceElUmbral:
            modelo = "fake-contradice-v1"
            version = "1"

            def generar(self, prompt: str) -> LLMResponse:
                return LLMResponse(
                    texto='{"razonamiento": "opinión del modelo", '
                    '"senal": "frustracion"}'
                )

        estado = _estado_con_evaluacion([3, 4, 8], 6)
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(
            estado, proveedor=ProveedorQueContradiceElUmbral()
        )
        _assert_contrato_y_grounding(intent_llm, "confusion")
        assert (
            intent_llm.argumentos["contenido"] == intent_regla.argumentos["contenido"]
        )

    def test_fact_ignora_vocabulario_fuera_del_contrato(self):
        """Reproduce el segundo hallazgo del sondeo: el modelo respondió
        vocabulario en inglés ("frustration"/"fluency"), fuera del
        vocabulario cerrado que protege el guardián P13. El fact debe
        seguir siendo el de la regla, nunca el texto libre del modelo."""

        class ProveedorQueRompeElVocabulario:
            modelo = "fake-vocabulario-roto-v1"
            version = "1"

            def generar(self, prompt: str) -> LLMResponse:
                return LLMResponse(
                    texto='{"razonamiento": "reasoning", "senal": "frustration"}'
                )

        estado = _estado_con_evaluacion([1, 2, 3], 3)  # regla exige "frustracion"
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(
            estado, proveedor=ProveedorQueRompeElVocabulario()
        )
        _assert_contrato_y_grounding(intent_llm, "frustracion")
        assert (
            intent_llm.argumentos["contenido"] == intent_regla.argumentos["contenido"]
        )
