"""M3 PR-7 — Validar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior
("antes=N despues=M. ¿Funcionó? Responde JSON.") no especificaba forma
ni la regla del dominio. Contra un proveedor real, dos problemas
distintos:

1. `confianza` nunca aparecía en la respuesta → `ejecutar_roundtrip`
   lanzaba `ValueError` (ADR-0004 E-2) el 100% de las veces — mismo
   patrón de forma que PR-2/3/4/5/6.
2. Hallazgo más grave, nuevo en M3: a `temperature=0`, el MISMO prompt
   exacto (antes=3, despues=1) produjo tres respuestas DISTINTAS en
   tres llamadas idénticas (`funciono: true`, luego ningún campo
   `funciono`, luego `funciono: false`) — no-determinismo real, no solo
   forma. Además, con antes=3/despues=5 (la decisión empeoró), el
   modelo respondió `funciono: true` en 3/3 — semánticamente incorrecto.

A diferencia de Evaluar/Tutorizar (PR-5/6): Validar produce un CLAIM,
no un fact (RFC-0003 línea 247: "claims de Validar"; el reducer
`validar_decision` construye un `ClaimEntry` con
`TipoClaim.INTERPRETACION`) — así que NO aplica grounding. El fix es
Clase A, mismo patrón que Diagnosticar (PR-2): declarar la regla del
dominio explícitamente en el prompt (regla `validacion-v1`:
`despues < antes` ⇒ funcionó) y fijar la forma
(razonamiento→funciono→confianza). Esto eliminó ambos problemas: 9/9
corridas reales correctas y estables en los tres casos (mejoró/
igual/empeoró) durante la Engineering Review, confirmado aquí con 10
corridas adicionales.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.validar import producir_llm
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
)
from runtime.kernel.state import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-m3-pr7",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision_y_evidencia(items_posteriores: list[int]) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})

    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)

    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)

    r3 = registrar_claim(
        r2.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar"},
        respaldo=(r2.estado.claims[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r3, Aplicado)

    r4 = registrar_decision(
        r3.estado, origen=r3.estado.claims[-1].id, contenido={"accion": "reforzar"}
    )
    assert isinstance(r4, Aplicado)

    r5 = registrar_fact(
        r4.estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": items_posteriores},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r5, Aplicado)
    return r5.estado


def _assert_contrato(intent, funciono_esperado: bool) -> None:
    assert intent.operacion == "validar_decision"
    assert intent.argumentos["autor"] is Capacidad.VALIDAR
    assert isinstance(intent.argumentos["confianza"], Decimal)
    assert intent.argumentos["afirmacion"]["funciono"] is funciono_esperado


class TestM3_PR7_ValidarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_decision_y_evidencia([3])  # antes=3, despues=1
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato(intent, funciono_esperado=True)


class TestM3_PR7_ElPromptEliminaLaDerivaObservada:
    """El hallazgo de esta Engineering Review no fue el ValueError: fue
    que, a temperature=0, el prompt SIN la regla explícita devolvió tres
    respuestas distintas para el mismo prompt exacto (antes=3,
    despues=1 — exactamente el caso reproducido aquí). Esta prueba
    documenta que el prompt corregido — con la regla del dominio
    declarada — elimina esa deriva, no solo la ausencia de excepción."""

    def test_diez_corridas_reales_mismo_veredicto_caso_que_derivaba(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_decision_y_evidencia([3])  # antes=3, despues=1
        for _ in range(10):
            (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato(intent, funciono_esperado=True)


class TestM3_PR7_VeredictoCorrectoEnLosOtrosDosCasos:
    def test_igual_y_empeoro(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        casos = (
            ([3, 4, 8], False),  # antes=3, despues=3 → igual
            ([1, 2, 3, 4, 5], False),  # antes=3, despues=5 → empeoró
        )
        for items_posteriores, funciono_esperado in casos:
            estado = _estado_con_decision_y_evidencia(items_posteriores)
            (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
            _assert_contrato(intent, funciono_esperado=funciono_esperado)
