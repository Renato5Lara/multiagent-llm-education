"""Suite de invariantes — reducer de decisiones (INV-6, INV-12).

Solo la forma: origen único y válido, asunto/confianza derivados,
pendiente-de-validación al nacer. Nada de consenso (RFC-0006, futuro).
"""

import dataclasses
from decimal import Decimal

from runtime.kernel.events import DecisionRegistrada
from runtime.kernel.reducers import (
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
)
from runtime.kernel.state import (
    Capacidad,
    DeliberacionEntry,
    EntryId,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
    Resuelta,
    Aplazada,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _estado_con_propuesta(tipo: TipoClaim = TipoClaim.PROPUESTA):
    estado = LearningState(
        identidad=Identidad(
            session_id="s-001",
            student_id="maria",
            version_student_model="v7",
            version_banco="banco-v2",
            version_politica="politica-v1",
            spec_version="foundation-2026-07-10",
        ),
        contexto={"ruta": "condicionales"},
    )
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.REMEDIAR,
        tipo=tipo,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar-condicionales"},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.LLM, modelo="m", version="1"),
    )
    assert isinstance(r2, Aplicado)
    return r2.estado, r2.estado.claims[0].id


class TestINV_6_RegistrarDecision:
    def test_decision_desde_claim_propuesta_unico(self):
        estado, propuesta_id = _estado_con_propuesta()
        resultado = registrar_decision(
            estado, origen=propuesta_id, contenido={"entregar": "refuerzo"}
        )
        assert isinstance(resultado, Aplicado)
        decision = resultado.estado.decisiones[0]
        # Asunto y confianza derivados del origen — el llamador no los declara.
        assert decision.asunto == "siguiente-paso(sesion)"
        assert decision.confianza == Decimal("0.82")
        # INV-12: nace pendiente de validación.
        assert decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION
        assert isinstance(resultado.eventos[0], DecisionRegistrada)

    def test_origen_inexistente_rechazado(self):
        estado, _ = _estado_con_propuesta()
        resultado = registrar_decision(
            estado, origen=EntryId(9, 9), contenido={}
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-6"

    def test_una_interpretacion_no_produce_decision(self):
        estado, claim_id = _estado_con_propuesta(tipo=TipoClaim.INTERPRETACION)
        resultado = registrar_decision(estado, origen=claim_id, contenido={})
        assert isinstance(resultado, Rechazado)
        assert "interpretación" in resultado.motivo

    def test_un_fact_no_produce_decision(self):
        estado, _ = _estado_con_propuesta()
        resultado = registrar_decision(
            estado, origen=estado.facts[0].id, contenido={}
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-6"

    def test_decision_desde_deliberacion_resuelta(self):
        estado, propuesta_id = _estado_con_propuesta()
        deliberacion = DeliberacionEntry(
            id=EntryId(3, 1),
            participantes=(propuesta_id, EntryId(9, 9)),
            resultado=Resuelta(
                regla="mayor-confianza-efectiva",
                aceptados=(propuesta_id,),
                confianza=Decimal("0.74"),
            ),
        )
        con_deliberacion = dataclasses.replace(
            estado, deliberaciones=(deliberacion,), transicion=3
        )
        resultado = registrar_decision(
            con_deliberacion, origen=deliberacion.id, contenido={}
        )
        assert isinstance(resultado, Aplicado)
        decision = resultado.estado.decisiones[0]
        # La confianza es la de la RESOLUCIÓN, no la del claim (INV-7).
        assert decision.confianza == Decimal("0.74")
        assert decision.asunto == "siguiente-paso(sesion)"

    def test_una_deliberacion_aplazada_no_produce_decision(self):
        estado, propuesta_id = _estado_con_propuesta()
        aplazada = DeliberacionEntry(
            id=EntryId(3, 1),
            participantes=(propuesta_id, EntryId(9, 9)),
            resultado=Aplazada(evidencia_faltante="resultado de refuerzo"),
        )
        con_aplazada = dataclasses.replace(
            estado, deliberaciones=(aplazada,), transicion=3
        )
        resultado = registrar_decision(
            con_aplazada, origen=aplazada.id, contenido={}
        )
        assert isinstance(resultado, Rechazado)
        assert "aplazada" in resultado.motivo

    def test_P14_el_estado_anterior_queda_intacto(self):
        estado, propuesta_id = _estado_con_propuesta()
        registrar_decision(estado, origen=propuesta_id, contenido={})
        assert estado.decisiones == ()
