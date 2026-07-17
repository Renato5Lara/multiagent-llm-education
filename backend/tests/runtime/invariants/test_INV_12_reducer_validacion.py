"""Suite de invariantes — reducer de validación (INV-12).

El veredicto de Validar: marca la decisión y registra el claim,
atómicamente. Exactamente dos estados terminales (validada /
no-observada) — nada más existe en el modelo congelado (RFC-0003).
"""

from decimal import Decimal

from runtime.kernel.events import ClaimRegistrado, DecisionValidada
from runtime.kernel.reducers import (
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_decision,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state import (
    Capacidad,
    EntryId,
    EstadoValidacion,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-validar",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_decision_pendiente() -> tuple[LearningState, EntryId]:
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
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar"},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r2, Aplicado)
    r3 = registrar_decision(
        r2.estado, origen=r2.estado.claims[0].id, contenido={"accion": "reforzar"}
    )
    assert isinstance(r3, Aplicado)
    return r3.estado, r3.estado.decisiones[0].id


def _veredicto(estado: LearningState, decision_id: EntryId, funciono: bool):
    return validar_decision(
        estado,
        decision_id=decision_id,
        autor=Capacidad.VALIDAR,
        asunto=f"efecto({decision_id})",
        afirmacion={"funciono": funciono},
        respaldo=(decision_id,),
        confianza=Decimal("0.80"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="validacion-v1"),
    )


class TestINV_12_ValidarDecision:
    def test_marca_validada_y_registra_el_claim_atomicamente(self):
        estado, decision_id = _estado_con_decision_pendiente()
        resultado = _veredicto(estado, decision_id, funciono=True)
        assert isinstance(resultado, Aplicado)
        nuevo = resultado.estado
        decision = nuevo.buscar(decision_id)
        assert decision.estado_validacion is EstadoValidacion.VALIDADA
        assert isinstance(resultado.eventos[0], ClaimRegistrado)
        assert isinstance(resultado.eventos[1], DecisionValidada)
        assert resultado.eventos[1].entry_id == decision_id

    def test_exactamente_dos_estados_terminales(self):
        # No existe "rechazada" ni "vencida" — el veredicto es CONTENIDO
        # del claim, no un tercer valor de EstadoValidacion.
        estado, decision_id = _estado_con_decision_pendiente()
        funciono = _veredicto(estado, decision_id, funciono=True)
        no_funciono = _veredicto(estado, decision_id, funciono=False)
        assert isinstance(funciono, Aplicado)
        assert isinstance(no_funciono, Aplicado)
        assert funciono.estado.buscar(decision_id).estado_validacion is (
            EstadoValidacion.VALIDADA
        )
        assert no_funciono.estado.buscar(decision_id).estado_validacion is (
            EstadoValidacion.VALIDADA
        )
        # El modelo congelado (RFC-0003 INV-12) tiene exactamente tres
        # valores: el inicial (pendiente) y dos terminales — nada de
        # "rechazada" ni "vencida".
        assert {
            EstadoValidacion.PENDIENTE_DE_VALIDACION,
            EstadoValidacion.VALIDADA,
            EstadoValidacion.NO_OBSERVADA,
        } == set(EstadoValidacion)

    def test_no_se_valida_dos_veces(self):
        estado, decision_id = _estado_con_decision_pendiente()
        primera = _veredicto(estado, decision_id, funciono=True)
        assert isinstance(primera, Aplicado)
        segunda = _veredicto(primera.estado, decision_id, funciono=True)
        assert isinstance(segunda, Rechazado)
        assert segunda.invariante == "INV-12"

    def test_decision_inexistente_rechazada(self):
        estado, _ = _estado_con_decision_pendiente()
        resultado = _veredicto(estado, EntryId(9, 9), funciono=True)
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-12"

    def test_el_respaldo_debe_incluir_la_decision(self):
        estado, decision_id = _estado_con_decision_pendiente()
        resultado = validar_decision(
            estado,
            decision_id=decision_id,
            autor=Capacidad.VALIDAR,
            asunto="efecto(x)",
            afirmacion={"funciono": True},
            respaldo=(),  # no incluye decision_id
            confianza=Decimal("0.8"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="validacion-v1"),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-5"

    def test_P14_el_estado_anterior_queda_pendiente(self):
        estado, decision_id = _estado_con_decision_pendiente()
        _veredicto(estado, decision_id, funciono=True)
        assert (
            estado.buscar(decision_id).estado_validacion
            is EstadoValidacion.PENDIENTE_DE_VALIDACION
        )
