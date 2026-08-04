"""ADR-0014 — retrocompatibilidad de `margen` en la reconstrucción.

`_resultado_deliberacion` es función pura sobre un `dict` ya
canonicalizado (sin I/O, sin Postgres — mismo criterio que
`test_parteD_resolucion_margen.py` para la mecánica de consenso): cubre
directamente el contrato de deserialización, sin depender del
almacenamiento real, que ya validan las suites RFC-0007/RFC-0008.

Caso crítico: sesiones reales ya persistidas (ADR-0013, cadena H10)
tienen transiciones con `Resuelta`/`Aplazada` SIN la clave `margen` —
esta suite prueba que `_resultado_deliberacion` las reconstruye sin
error, con `margen=None`, en vez de fallar con `KeyError`.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.engine.checkpoint.reconstruccion import _resultado_deliberacion
from runtime.kernel.state.entries import Aplazada, Escalada, Resuelta


class TestRetrocompatibilidadMargen:
    def test_resuelta_historica_sin_clave_margen_reconstruye_a_none(self):
        """Forma canónica anterior a ADR-0014 — la clave ni existe."""
        datos = {
            "regla": "mayor-confianza-declarada",
            "aceptados": ["T-000001/e1"],
            "confianza": "0.8200",
        }
        resultado = _resultado_deliberacion(datos)
        assert isinstance(resultado, Resuelta)
        assert resultado.margen is None

    def test_aplazada_historica_sin_clave_margen_reconstruye_a_none(self):
        datos = {"evidencia_faltante": "más evidencia de validación"}
        resultado = _resultado_deliberacion(datos)
        assert isinstance(resultado, Aplazada)
        assert resultado.margen is None

    def test_resuelta_nueva_con_margen_reconstruye_el_decimal(self):
        """Forma canónica posterior a ADR-0014."""
        datos = {
            "regla": "mayor-confianza-declarada",
            "aceptados": ["T-000001/e1"],
            "confianza": "0.8200",
            "margen": "0.3000",
        }
        resultado = _resultado_deliberacion(datos)
        assert resultado.margen == Decimal("0.3000")

    def test_resuelta_nueva_con_margen_null_reconstruye_a_none(self):
        """`a_canonico` serializa `margen=None` como `null` explícito
        (dataclass siempre incluye sus campos) — distinto del caso
        histórico donde la clave falta del todo; ambos deben producir
        `None`."""
        datos = {
            "regla": "mayor-confianza-declarada",
            "aceptados": ["T-000001/e1"],
            "confianza": "0.8200",
            "margen": None,
        }
        resultado = _resultado_deliberacion(datos)
        assert resultado.margen is None

    def test_escalada_no_declara_margen(self):
        """Fuera de alcance de ADR-0014 §2 — Escalada no gana el campo."""
        datos = {"destinatario": "docente"}
        resultado = _resultado_deliberacion(datos)
        assert isinstance(resultado, Escalada)
        assert not hasattr(resultado, "margen")
