"""Suite de reconstrucción — serialización canónica (ADR-0001; R3, A3)."""

import json
from decimal import Decimal

import pytest

from runtime.engine.checkpoint import a_canonico
from runtime.kernel.state import (
    Capacidad,
    ClaimEntry,
    EntryId,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)


def _claim(confianza: Decimal) -> ClaimEntry:
    return ClaimEntry(
        id=EntryId(2, 1),
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(EntryId(1, 1),),
        confianza=confianza,
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring"),
    )


class TestADR_0001_Canonico:
    def test_R3_mismo_valor_mismos_bytes(self):
        # El orden de inserción de claves no puede alterar los bytes.
        a = {"b": 1, "a": {"z": "x", "y": (1, 2)}}
        b = {"a": {"y": (1, 2), "z": "x"}, "b": 1}
        assert a_canonico(a) == a_canonico(b)

    def test_decimal_a_escala_fija(self):
        # 0.78 y 0.7800 son el mismo valor → los mismos bytes.
        assert a_canonico(_claim(Decimal("0.78"))) == a_canonico(
            _claim(Decimal("0.7800"))
        )

    def test_A3_float_binario_prohibido(self):
        with pytest.raises(ValueError, match="ADR-0001"):
            a_canonico({"tiempo": 35.5})

    def test_nfc_unifica_representaciones_unicode(self):
        assert a_canonico("condición") == a_canonico("condición")

    def test_entry_id_y_enum_en_forma_textual(self):
        crudo = json.loads(a_canonico(_claim(Decimal("0.78"))))
        assert crudo["id"] == "T-000002/e1"
        assert crudo["autor"] == "diagnosticar"
        assert crudo["confianza"] == "0.7800"

    def test_ida_y_vuelta_estable(self):
        # json.loads(bytes) → re-canonicalizar → los mismos bytes (R3).
        bytes1 = a_canonico(_claim(Decimal("0.78")))
        assert a_canonico(json.loads(bytes1)) == bytes1

    def test_tipo_no_serializable_rechazado(self):
        with pytest.raises(ValueError, match="no serializable"):
            a_canonico({"raro": object()})
