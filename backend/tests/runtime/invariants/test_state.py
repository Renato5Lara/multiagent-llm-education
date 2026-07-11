"""Suite de invariantes — el Aggregate Root (RFC-0003 §2, INV-1/2/3)."""

import dataclasses
from decimal import Decimal

import pytest

from runtime.kernel.state import (
    BOUNDARY,
    Capacidad,
    ClaimEntry,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
    TipoClaim,
    Vigencia,
)
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-001",
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado(**kwargs) -> LearningState:
    base = dict(identidad=_identidad(), contexto={"ruta": "condicionales"})
    base.update(kwargs)
    return LearningState(**base)


def _fact(transicion: int = 1) -> FactEntry:
    return FactEntry(
        id=EntryId(transicion, 1),
        autor=BOUNDARY,
        contenido={"tiempo_seg": 35},
        provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
    )


class TestINV_1_Identidad:
    def test_identidad_completa_obligatoria(self):
        with pytest.raises(ValueError, match="INV-1"):
            Identidad(
                session_id="s-001",
                student_id="maria",
                version_student_model="v7",
                version_banco="banco-v2",
                version_politica="politica-v1",
                spec_version="",
            )


class TestINV_2_Inmutabilidad:
    def test_el_estado_es_congelado(self):
        estado = _estado()
        with pytest.raises(dataclasses.FrozenInstanceError):
            estado.transicion = 5  # type: ignore[misc]

    def test_la_identidad_es_congelada(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _identidad().spec_version = "otra"  # type: ignore[misc]


class TestINV_3_AppendOnly:
    def test_las_secciones_historicas_son_tuplas(self):
        estado = _estado(facts=(_fact(),))
        assert isinstance(estado.facts, tuple)
        with pytest.raises(AttributeError):
            estado.facts.append(_fact(2))  # type: ignore[attr-defined]

    def test_P14_una_transicion_produce_un_estado_nuevo_sin_tocar_el_anterior(self):
        # P14: la historia jamás se reescribe — cada estado sigue intacto.
        antes = _estado()
        despues = dataclasses.replace(
            antes, facts=antes.facts + (_fact(),), transicion=1
        )
        assert antes.facts == ()
        assert antes.transicion == 0
        assert len(despues.facts) == 1


class TestINV_5_ConsultasDeVigencia:
    def test_buscar_por_id(self):
        fact = _fact()
        estado = _estado(facts=(fact,), transicion=1)
        assert estado.buscar(fact.id) is fact
        assert estado.buscar(EntryId(9, 9)) is None

    def test_es_vigente_distingue_supersedidas(self):
        vigente = _fact()
        supersedido = FactEntry(
            id=EntryId(2, 1),
            autor=BOUNDARY,
            contenido={"tiempo_seg": 99},
            provenance=Provenance.de(OrigenProvenance.TELEMETRIA),
            vigencia=Vigencia(superseded_por=vigente.id),
        )
        estado = _estado(facts=(supersedido, vigente), transicion=2)
        assert estado.es_vigente(vigente.id)
        assert not estado.es_vigente(supersedido.id)
        assert not estado.es_vigente(EntryId(9, 9))

    def test_es_vigente_cubre_claims(self):
        fact = _fact()
        claim = ClaimEntry(
            id=EntryId(2, 1),
            autor=Capacidad.DIAGNOSTICAR,
            tipo=TipoClaim.INTERPRETACION,
            asunto="dominio(COMP-2)",
            afirmacion={"dominada": False},
            respaldo=(fact.id,),
            confianza=Decimal("0.78"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
        )
        estado = _estado(facts=(fact,), claims=(claim,), transicion=2)
        assert estado.es_vigente(claim.id)
