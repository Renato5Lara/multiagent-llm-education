"""Suite de invariantes — supersesión (INV-3: corregir es superseder)."""

from decimal import Decimal

from runtime.kernel.events import ClaimRegistrado, EntradaSupersedida
from runtime.kernel.reducers import (
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_fact,
    superseder_claim,
    superseder_fact,
)
from runtime.kernel.state import (
    Capacidad,
    EntryId,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState


def _base() -> LearningState:
    return LearningState(
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


def _con_fact_y_claim() -> tuple[LearningState, EntryId, EntryId]:
    r1 = registrar_fact(
        _base(),
        autor=Capacidad.EVALUAR,
        contenido={"items_incorrectos": [3, 4, 8]},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    fact_id = r1.estado.facts[0].id
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False, "confianza_declarada": "0.78"},
        respaldo=(fact_id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
    )
    assert isinstance(r2, Aplicado)
    return r2.estado, fact_id, r2.estado.claims[0].id


def _superseder(estado: LearningState, claim_id: EntryId, fact_id: EntryId):
    return superseder_claim(
        estado,
        objetivo=claim_id,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": True},
        respaldo=(fact_id,),
        confianza=Decimal("0.9"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
    )


class TestINV_3_Supersesion:
    def test_corregir_es_superseder_jamas_editar(self):
        estado, fact_id, claim_id = _con_fact_y_claim()
        resultado = _superseder(estado, claim_id, fact_id)
        assert isinstance(resultado, Aplicado)
        nuevo = resultado.estado
        # La anterior queda — marcada, no borrada.
        anterior = nuevo.buscar(claim_id)
        assert anterior is not None
        assert not anterior.vigencia.vigente
        # La nueva es vigente y la marca apunta a ella.
        assert anterior.vigencia.superseded_por == nuevo.claims[-1].id
        assert nuevo.es_vigente(nuevo.claims[-1].id)
        # Dos eventos: la supersesión y el registro.
        assert isinstance(resultado.eventos[0], EntradaSupersedida)
        assert isinstance(resultado.eventos[1], ClaimRegistrado)

    def test_P14_el_estado_anterior_conserva_la_entrada_vigente(self):
        estado, fact_id, claim_id = _con_fact_y_claim()
        _superseder(estado, claim_id, fact_id)
        assert estado.es_vigente(claim_id)  # la historia previa, intacta

    def test_objetivo_inexistente_rechazado(self):
        estado, fact_id, _ = _con_fact_y_claim()
        resultado = _superseder(estado, EntryId(9, 9), fact_id)
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-3"

    def test_no_se_supersede_dos_veces(self):
        estado, fact_id, claim_id = _con_fact_y_claim()
        primera = _superseder(estado, claim_id, fact_id)
        assert isinstance(primera, Aplicado)
        segunda = _superseder(primera.estado, claim_id, fact_id)
        assert isinstance(segunda, Rechazado)
        assert segunda.invariante == "INV-3"

    def test_superseder_fact_con_fact(self):
        estado, fact_id, _ = _con_fact_y_claim()
        resultado = superseder_fact(
            estado,
            objetivo=fact_id,
            autor=Capacidad.EVALUAR,
            contenido={"items_incorrectos": [3, 4]},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
        )
        assert isinstance(resultado, Aplicado)
        assert not resultado.estado.buscar(fact_id).vigencia.vigente


class TestINV_8_FactsSoloPorFacts:
    def test_un_claim_no_supersede_un_fact(self):
        # INV-8: un fact solo puede ser cuestionado por nuevos facts.
        estado, fact_id, _ = _con_fact_y_claim()
        resultado = _superseder(estado, fact_id, fact_id)
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-8"

    def test_un_fact_no_supersede_un_claim(self):
        estado, _, claim_id = _con_fact_y_claim()
        resultado = superseder_fact(
            estado,
            objetivo=claim_id,
            autor=Capacidad.EVALUAR,
            contenido={},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
        )
        assert isinstance(resultado, Rechazado)
        assert resultado.invariante == "INV-3"
