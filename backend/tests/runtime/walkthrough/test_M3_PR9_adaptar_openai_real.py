"""M3 PR-9 — Adaptar con proveedor real (OpenAI).

Hallazgo que motiva este PR (Engineering Review exclusiva previa, sondeo
empírico antes de tocar código): el prompt anterior
("Diseña la experiencia (modalidad, profundidad)... Responde JSON.") no
especificaba forma ni vocabulario. Dos problemas distintos:

1. Forma: 3/3 sondeos reales anidaron todo bajo "experiencia": {...} —
   nunca modalidad/profundidad/confianza en la raíz. ValueError
   (ADR-0004 E-2) el 100% de las veces — mismo patrón que PR-2..8.
2. Hallazgo más grave que cualquiera de las 8 PR anteriores: el modelo
   interpretó "modalidad" como modalidad de ESTUDIO
   (presencial/virtual/semi-presencial) — una taxonomía de canal de
   entrega que NO EXISTE en este dominio — en vez de FORMATO DE
   REPRESENTACIÓN (visual/textual/mixta/...). No es una mala traducción
   del vocabulario correcto (como "frustration" en Tutorizar, PR-6): es
   un eje de razonamiento completamente distinto. El guardián P13 de
   Adaptar (`test_P13_adaptar_reglas_vs_llm.py`) no lo detecta — su
   lista `_PROHIBIDO` solo bloquea fugas de recursos físicos
   (url/.pdf/recurso_id...), no vocabulario de modalidad.

Adaptar confirma la familia CLAIM (TipoClaim.PROPUESTA, RFC-0002: "con
las alternativas que evaluó") — sin grounding posible: a diferencia de
Validar/Modelar no existe un único valor correcto que anclar,
DISENO_POR_ACCION es un respaldo fijo y el propósito genuino de esta
versión es explorar diseño dentro del vocabulario del dominio. Fix:
declarar el vocabulario cerrado explícitamente en el prompt (mismo
patrón que restringió `accion` en Remediar/PR-3 y `senal` en
Tutorizar/PR-6, aplicado aquí a tres campos: modalidad, profundidad,
alternativas_descartadas) + forma exacta ordenada.

Este test no solo verifica que aparece el vocabulario correcto — verifica
explícitamente que NO aparece el vocabulario ajeno descubierto durante
la Engineering Review (presencial/virtual/semi-presencial/...), como
evidencia ejecutable del hallazgo.

Se salta sin `OPENAI_API_KEY`.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest
from dotenv import load_dotenv

from runtime.domain.adaptar import producir_llm
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_decision, registrar_fact
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState

load_dotenv()
pytestmark = pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY"), reason="OPENAI_API_KEY no configurada"
)

_VOCABULARIO_MODALIDAD = {
    "visual",
    "textual",
    "mixta",
    "guiado",
    "practica",
    "autonomo",
    "solo-texto",
    "ejemplo-codigo",
}
_VOCABULARIO_PROFUNDIDAD = {"fundamentos", "aplicacion"}

# Taxonomía de modalidad de ESTUDIO que el sondeo real produjo antes del
# fix — ajena por completo al dominio (que no distingue canal de entrega,
# solo formato de representación). Ningún valor de aquí debe aparecer.
_VOCABULARIO_PROHIBIDO = {
    "presencial",
    "virtual",
    "semipresencial",
    "semi-presencial",
    "hibrido",
    "híbrido",
    "remoto",
    "online",
}


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-m3-pr9",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision(accion: str) -> LearningState:
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
        afirmacion={"accion": accion},
        respaldo=(r2.estado.claims[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r3, Aplicado)
    r4 = registrar_decision(
        r3.estado, origen=r3.estado.claims[-1].id, contenido={"accion": accion}
    )
    assert isinstance(r4, Aplicado)
    return r4.estado


def _assert_contrato_y_vocabulario(intent) -> None:
    assert intent.operacion == "registrar_claim"
    assert intent.argumentos["autor"] is Capacidad.ADAPTAR
    assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
    assert isinstance(intent.argumentos["confianza"], Decimal)
    afirmacion = intent.argumentos["afirmacion"]

    assert afirmacion["modalidad"] in _VOCABULARIO_MODALIDAD
    assert afirmacion["profundidad"] in _VOCABULARIO_PROFUNDIDAD
    assert len(afirmacion["alternativas_descartadas"]) >= 1
    for alt in afirmacion["alternativas_descartadas"]:
        assert alt["modalidad"] in _VOCABULARIO_MODALIDAD

    # El hallazgo de la Engineering Review, hecho ejecutable: ningún
    # valor de la taxonomía ajena (modalidad de estudio) debe colarse,
    # ni en la propuesta principal ni en las alternativas descartadas.
    valores_producidos = {afirmacion["modalidad"]} | {
        alt["modalidad"] for alt in afirmacion["alternativas_descartadas"]
    }
    interseccion = valores_producidos & _VOCABULARIO_PROHIBIDO
    assert not interseccion, (
        f"Adaptar produjo vocabulario de modalidad de ESTUDIO ajeno al "
        f"dominio: {interseccion}"
    )


class TestM3_PR9_AdaptarSinValueError:
    def test_ejecutar_roundtrip_no_falla_contra_el_proveedor_real(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        estado = _estado_con_decision("reforzar")
        (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
        _assert_contrato_y_vocabulario(intent)


class TestM3_PR9_VocabularioCerradoEstable:
    def test_nueve_corridas_reales_sin_vocabulario_ajeno(self):
        from runtime.domain.shared.llm_openai import OpenAIProvider

        casos = ("reforzar", "avanzar-con-andamiaje")
        for accion in casos:
            estado = _estado_con_decision(accion)
            for _ in range(3):
                (intent,) = producir_llm(estado, proveedor=OpenAIProvider())
                _assert_contrato_y_vocabulario(intent)
