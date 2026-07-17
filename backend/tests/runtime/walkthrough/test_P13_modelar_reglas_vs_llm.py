"""Guardián de P13 para Modelar (ADR-0005 §7) — sexta capacidad.

Además del contrato compartido, verifica la exigencia explícita del
tesista: toda afirmación de Modelar debe ser completamente trazable
hacia el claim de Validar que la originó (P6).
"""

from decimal import Decimal

from runtime.domain.modelar import FakeLLMProvider, producir, producir_llm
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state import (
    Capacidad,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-p13-modelar",
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


class TestP13_ModelarContratoCompartido:
    def test_mismo_operacion_asunto_y_forma_de_respaldo(self):
        estado = _estado_con_veredicto(funciono=True)
        validacion_id = next(
            c.id for c in estado.claims if c.autor is Capacidad.VALIDAR
        )
        (intent_regla,) = producir(estado)
        (intent_llm,) = producir_llm(estado, proveedor=FakeLLMProvider())

        for intent in (intent_regla, intent_llm):
            assert intent.operacion == "registrar_claim"
            assert intent.argumentos["autor"] is Capacidad.MODELAR
            assert intent.argumentos["tipo"] is TipoClaim.INTERPRETACION
            assert intent.argumentos["asunto"] == "modelo-estudiante(COMP-2)"
            assert intent.argumentos["respaldo"] == (validacion_id,)
            assert isinstance(intent.argumentos["confianza"], Decimal)

        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM

    def test_trazabilidad_completa_hacia_validar_y_la_decision(self):
        # Exigencia explícita del tesista: cada afirmación de Modelar debe
        # poder recorrerse hasta el claim de Validar que la originó — y
        # desde ahí, hasta la decisión (P6).
        estado = _estado_con_veredicto(funciono=True)
        (intent,) = producir(estado)
        resultado = registrar_claim(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        claim_modelar = resultado.estado.claims[-1]

        claim_validar = estado.buscar(claim_modelar.respaldo[0])
        assert claim_validar.autor is Capacidad.VALIDAR

        decision = estado.buscar(claim_validar.respaldo[0])
        assert decision is not None
        assert decision.contenido["accion"] == "reforzar"

    def test_refleja_el_veredicto_sin_reinterpretarlo(self):
        positivo = _estado_con_veredicto(funciono=True)
        negativo = _estado_con_veredicto(funciono=False)
        (regla_si,) = producir(positivo)
        (regla_no,) = producir(negativo)
        assert regla_si.argumentos["afirmacion"]["efecto_positivo"] is True
        assert regla_no.argumentos["afirmacion"]["efecto_positivo"] is False

    def test_no_dispara_sin_veredicto_de_validar(self):
        estado = LearningState(
            identidad=_identidad(), contexto={"ruta": "condicionales"}
        )
        assert producir(estado) == ()
        assert producir_llm(estado) == ()

    def test_no_remodela_el_mismo_veredicto_dos_veces(self):
        estado = _estado_con_veredicto(funciono=True)
        (intent,) = producir(estado)
        resultado = registrar_claim(estado, **intent.argumentos)
        assert isinstance(resultado, Aplicado)
        assert producir(resultado.estado) == ()
