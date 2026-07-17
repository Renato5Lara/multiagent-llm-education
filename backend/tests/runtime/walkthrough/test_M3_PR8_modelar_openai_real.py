"""M3 PR-8 — Modelar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review previa, sondeo empírico
antes de tocar código): el prompt anterior
("competencia=X funciono=true/false. ¿Qué implica esto para el modelo
del estudiante? Responde JSON.") no especificaba forma ni la regla del
dominio. 3/3 sondeos reales anidaron la respuesta en una estructura
libre inventada (`implicaciones.modelo_estudiante` con claves como
`competencia_adquirida`, `nivel_de_dominio`, `recomendaciones`) — nunca
los campos `efecto_positivo`/`confianza` que `ejecutar_roundtrip`
exige. `ValueError` (ADR-0004 E-2) el 100% de las veces — mismo patrón
de forma que PR-2/3/4/5/6/7.

Modelar produce un CLAIM (mismo criterio de M3 PR-7: el tipo de sobre
decide la familia, no la derivabilidad) — no aplica grounding. Es el
caso más extremo de la familia claim: la regla ni siquiera aplica un
umbral, copia literalmente `funciono` en `efecto_positivo` (ver
`productor.py` y el guardián P13
`test_refleja_el_veredicto_sin_reinterpretarlo`, que hoy solo cubre la
versión regla). Fix: Clase A, mismo patrón que Diagnosticar/Validar —
declarar la regla explícitamente en el prompt (`efecto_positivo` DEBE
igualar `funciono` — Modelar no reinterpreta el veredicto de Validar,
solo su implicación) y fijar la forma
(razonamiento→efecto_positivo→confianza).

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.modelar import producir_llm
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-m3-pr8",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_veredicto(funciono: bool) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})

    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar"},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    r3 = registrar_decision(
        r2.estado, origen=r2.estado.claims[0].id, contenido={"accion": "reforzar"}
    )
    r4 = validar_decision(
        r3.estado,
        decision_id=r3.estado.decisiones[0].id,
        autor=Capacidad.VALIDAR,
        asunto=f"efecto({r3.estado.decisiones[0].id})",
        afirmacion={"competencia": "COMP-2", "funciono": funciono},
        respaldo=(r3.estado.decisiones[0].id,),
        confianza=Decimal("0.80"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="validacion-v1"),
    )
    assert isinstance(r4, Aplicado)
    return r4.estado


def _assert_contrato(intent, efecto_esperado: bool) -> None:
    assert intent.operacion == "registrar_claim"
    assert intent.argumentos["autor"] is Capacidad.MODELAR
    assert intent.argumentos["tipo"] is TipoClaim.INTERPRETACION
    assert isinstance(intent.argumentos["confianza"], Decimal)
    assert intent.argumentos["afirmacion"]["efecto_positivo"] is efecto_esperado


class TestM3_PR8_ModelarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_veredicto(funciono=True)
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato(intent, efecto_esperado=True)


class TestM3_PR8_LaVersionLLMTampocoReinterpretaElVeredicto:
    """El guardián P13 (`test_refleja_el_veredicto_sin_reinterpretarlo`)
    exige esta propiedad solo para `producir()`. Esta prueba la extiende
    al proveedor real: Modelar no modifica el resultado de Validar,
    únicamente lo interpreta — `efecto_positivo` debe seguir siendo
    exactamente `funciono`, sin importar el razonamiento que el modelo
    construya alrededor."""

    def test_diez_corridas_reales_efecto_positivo_igual_a_funciono(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        for funciono in (True, False):
            estado = _estado_con_veredicto(funciono=funciono)
            for _ in range(5):
                (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
                _assert_contrato(intent, efecto_esperado=funciono)
