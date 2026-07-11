"""Suite de invariantes — reducer de claims (RFC-0003 §4; INV-5).

Primera invariante validada CONTRA EL ESTADO: el respaldo debe apuntar a
entradas vigentes en el momento de aplicar (RFC-0004 §1, paso 4).
"""

import dataclasses
from decimal import Decimal

from runtime.kernel.events import ClaimRegistrado, TransicionRechazada
from runtime.kernel.reducers import Aplicado, Rechazado, registrar_claim, registrar_fact
from runtime.kernel.state import (
    BOUNDARY,
    Capacidad,
    EntryId,
    OrigenProvenance,
    Provenance,
    TipoClaim,
    Vigencia,
)
from runtime.kernel.state.state import Identidad, LearningState


def _estado_con_fact() -> tuple[LearningState, EntryId]:
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
    resultado = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(resultado, Aplicado)
    return resultado.estado, resultado.estado.facts[0].id


def _registrar(estado: LearningState, **kwargs) -> object:
    base = dict(
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
    )
    base.update(kwargs)
    return registrar_claim(estado, **base)


class TestINV_5_RegistrarClaim:
    def test_claim_con_respaldo_vigente_aplicado(self):
        estado, fact_id = _estado_con_fact()
        resultado = _registrar(estado, respaldo=(fact_id,))
        assert isinstance(resultado, Aplicado)
        assert resultado.estado.transicion == 2
        evento = resultado.eventos[0]
        assert isinstance(evento, ClaimRegistrado)
        assert evento.asunto == "dominio(COMP-2)"

    def test_respaldo_inexistente_rechazado_contra_el_estado(self):
        estado, _ = _estado_con_fact()
        resultado = _registrar(estado, respaldo=(EntryId(9, 9),))
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-5"
        assert "T-000009/e9" in resultado.motivo
        assert isinstance(resultado.eventos[0], TransicionRechazada)

    def test_respaldo_supersedido_rechazado(self):
        # La validación es contra el estado ACTUAL, no contra la vista
        # que leyó el productor (RFC-0004 §1, paso 4).
        estado, fact_id = _estado_con_fact()
        supersedido = dataclasses.replace(
            estado.facts[0], vigencia=Vigencia(superseded_por=EntryId(2, 1))
        )
        estado_cambiado = dataclasses.replace(estado, facts=(supersedido,))
        resultado = _registrar(estado_cambiado, respaldo=(fact_id,))
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-5"

    def test_invalidez_estructural_reporta_su_norma(self):
        # ADR-0004 E-1: el contenido inválido de una propuesta es rechazo
        # registrado con la norma correcta — jamás excepción.
        estado, fact_id = _estado_con_fact()
        resultado = _registrar(
            estado, respaldo=(fact_id,), confianza=Decimal("1.5")
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "A1"

    def test_P14_el_estado_anterior_queda_intacto(self):
        estado, fact_id = _estado_con_fact()
        _registrar(estado, respaldo=(fact_id,))
        assert estado.claims == ()
        assert estado.transicion == 1
