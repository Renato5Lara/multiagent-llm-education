"""El helper compartido de las capacidades LLM (domain/shared/llm_roundtrip.py).

Extraído tras la cuarta capacidad (Diagnosticar/Remediar/Orientar/
Evaluar), por decisión del tesista: es infraestructura genuina —no
depende de Claim, Fact ni de ninguna capacidad— a diferencia de la firma,
el reducer y el provenance, que Evaluar demostró que SÍ varían por
capacidad (registrado en memoria del proyecto, no en un ADR: no
introduce concepto nuevo).
"""

import pytest

from runtime.domain.shared.llm_roundtrip import ejecutar_roundtrip


class _ProveedorFijo:
    modelo = "fijo-v1"
    version = "1"

    def __init__(self, texto: str):
        self._texto = texto

    def generar(self, prompt: str) -> str:
        return self._texto


class TestADR_0004_EjecutarRoundtrip:
    def test_json_valido_sin_campos_requeridos(self):
        datos = ejecutar_roundtrip(_ProveedorFijo('{"x": 1}'), "prompt")
        assert datos == {"x": 1}

    def test_campos_requeridos_presentes(self):
        datos = ejecutar_roundtrip(
            _ProveedorFijo('{"accion": "reforzar", "confianza": "0.8"}'),
            "prompt",
            campos_requeridos=("accion", "confianza"),
        )
        assert datos["accion"] == "reforzar"

    def test_E2_campo_faltante_se_propaga_ruidosamente(self):
        # ADR-0004: un round-trip incompleto es un bug de prompt/proveedor
        # (E-2) — se propaga, jamás se disfraza de rechazo de dominio.
        with pytest.raises(ValueError, match="ADR-0004 E-2"):
            ejecutar_roundtrip(
                _ProveedorFijo('{"accion": "reforzar"}'),
                "prompt",
                campos_requeridos=("accion", "confianza"),
            )

    def test_json_malformado_se_propaga_como_error_de_parseo(self):
        with pytest.raises(Exception):
            ejecutar_roundtrip(_ProveedorFijo("no es json"), "prompt")
