"""Guardián de P13 para Validar (ADR-0005 §7) — quinta capacidad.

Primera vez que el productor consume la cadena causal completa:
decisión → propuesta → interpretación → fact original, más el fact
posterior de Evaluar. Puro-de-estado, sin parámetros externos.
"""

from decimal import Decimal

from runtime.domain.validar import FakeLLMProvider, producir, producir_llm
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
)
from runtime.kernel.state import (
    Capacidad,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-p13-validar",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision_y_evidencia(mejoro: bool) -> LearningState:
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

    items_posteriores = [3] if mejoro else [3, 4, 8]
    r5 = registrar_fact(
        r4.estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": items_posteriores},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r5, Aplicado)
    return r5.estado


class TestP13_ValidarContratoCompartido:
    def test_mismo_operacion_asunto_y_forma_de_respaldo(self):
        estado = _estado_con_decision_y_evidencia(mejoro=True)
        decision_id = estado.decisiones[0].id
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "validar_decision"
            assert intent.argumentos["autor"] is Capacidad.VALIDAR
            assert intent.argumentos["decision_id"] == decision_id
            assert intent.argumentos["asunto"] == f"efecto({decision_id})"
            assert decision_id in intent.argumentos["respaldo"]
            assert isinstance(intent.argumentos["confianza"], Decimal)
            assert "funciono" in intent.argumentos["afirmacion"]

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_ambas_versiones_coinciden_en_el_veredicto(self):
        # El contrato no lo exige, pero ambas cuentan sobre la MISMA
        # evidencia (P12) — deben coincidir aquí.
        mejoro = _estado_con_decision_y_evidencia(mejoro=True)
        empeoro = _estado_con_decision_y_evidencia(mejoro=False)
        (regla_si,) = producir(mejoro)
        (llm_si,) = producir_llm(mejoro, proveedor=FakeLLMProvider())
        (regla_no,) = producir(empeoro)
        (llm_no,) = producir_llm(empeoro, proveedor=FakeLLMProvider())
        assert regla_si.argumentos["afirmacion"]["funciono"] is True
        assert llm_si.argumentos["afirmacion"]["funciono"] is True
        assert regla_no.argumentos["afirmacion"]["funciono"] is False
        assert llm_no.argumentos["afirmacion"]["funciono"] is False

    def test_sin_evidencia_posterior_no_dispara(self):
        # Puro-de-estado (P12): si la evidencia no existe, no se inventa.
        estado = LearningState(
            identidad=_identidad(), contexto={"ruta": "condicionales"}
        )
        assert producir(estado) == ()
        assert producir_llm(estado) == ()

    def test_decision_ya_validada_no_vuelve_a_disparar(self):
        from runtime.kernel.reducers import validar_decision

        estado = _estado_con_decision_y_evidencia(mejoro=True)
        (intent,) = producir(estado)
        resultado = validar_decision(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        assert (
            resultado.estado.decisiones[0].estado_validacion
            is EstadoValidacion.VALIDADA
        )
        assert producir(resultado.estado) == ()
