"""Suite de invariantes — los sobres (RFC-0003 §3, INV-4/INV-5, A1)."""

from decimal import Decimal

import pytest

from runtime.kernel.state import (
    BOUNDARY,
    Capacidad,
    ClaimEntry,
    DeliberacionEntry,
    EntryId,
    FactEntry,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
    Vigencia,
)


def _prov(origen: OrigenProvenance = OrigenProvenance.TELEMETRIA) -> Provenance:
    return Provenance.de(origen)


def _fact(entrada: int = 1, autor=BOUNDARY) -> FactEntry:
    return FactEntry(
        id=EntryId(1, entrada),
        autor=autor,
        contenido={"tiempo_seg": 35},
        provenance=_prov(),
    )


def _claim(**kwargs) -> ClaimEntry:
    base = dict(
        id=EntryId(2, 1),
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(EntryId(1, 1),),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
    )
    base.update(kwargs)
    return ClaimEntry(**base)


class TestINV_4_Facts:
    def test_un_fact_jamas_lleva_respaldo_por_construccion(self):
        # INV-4: la asimetría es estructural — el campo no existe.
        assert not hasattr(_fact(), "respaldo")

    def test_el_boundary_autora_hechos_del_mundo(self):
        assert _fact(autor=BOUNDARY).autor == BOUNDARY

    def test_una_capacidad_autora_facts(self):
        assert _fact(autor=Capacidad.EVALUAR).autor is Capacidad.EVALUAR

    def test_autor_arbitrario_rechazado(self):
        with pytest.raises(ValueError, match="INV-4"):
            _fact(autor="frontend")


class TestINV_5_Claims:
    def test_claim_valido(self):
        claim = _claim()
        assert claim.vigencia.vigente

    def test_el_boundary_jamas_autora_claims(self):
        # Grieta A: el mundo aporta hechos; solo las capacidades interpretan.
        with pytest.raises(ValueError, match="INV-5"):
            _claim(autor=BOUNDARY)

    def test_claim_sin_respaldo_rechazado(self):
        with pytest.raises(ValueError, match="INV-5"):
            _claim(respaldo=())

    def test_claim_sin_asunto_rechazado(self):
        with pytest.raises(ValueError, match="asunto"):
            _claim(asunto="")

    def test_A1_confianza_acotada(self):
        with pytest.raises(ValueError, match="A1"):
            _claim(confianza=Decimal("1.2"))

    def test_ADR_0001_confianza_decimal_exacta(self):
        # ADR-0001 §4: jamás coma flotante binaria en confianzas.
        with pytest.raises(ValueError, match="decimal"):
            _claim(confianza=0.78)


class TestADR_0001_IdsDeterministas:
    def test_formato_canonico_adr_0001(self):
        assert str(EntryId(42, 1)) == "T-000042/e1"

    def test_parse_ida_y_vuelta(self):
        original = EntryId(42, 3)
        assert EntryId.parse(str(original)) == original

    def test_fuera_de_rango_rechazado(self):
        with pytest.raises(ValueError):
            EntryId(-1, 1)


class TestINV_3_Vigencia:
    def test_corregir_es_superseder_jamas_editar(self):
        # INV-3/P14: la corrección es una nueva entrada que supersede.
        supersedida = Vigencia(superseded_por=EntryId(3, 1))
        assert not supersedida.vigente
        assert Vigencia().vigente


class TestP8_Deliberacion:
    def test_sin_desacuerdo_posible_no_se_convoca(self):
        # P8: el ceremonial sin desacuerdo posible está prohibido.
        with pytest.raises(ValueError, match="P8"):
            DeliberacionEntry(
                id=EntryId(4, 1),
                participantes=(EntryId(2, 1),),
                resultado=Resuelta(
                    regla="mayor-confianza-efectiva",
                    aceptados=(EntryId(2, 1),),
                    confianza=Decimal("0.9"),
                ),
            )
