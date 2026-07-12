"""RFC-0006/1, Parte 0 — política versionada (kernel/deliberation/politica.py).

Sin Postgres, sin LangGraph: `Politica`/`POLITICAS`/`resolver_politica`
no dependen de nada persistido — son constantes de código.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from runtime.kernel.deliberation.politica import POLITICAS, Politica, resolver_politica


class TestParte0_PoliticaVersionada:
    def test_v1_esta_registrada_con_pesos_cero(self):
        v1 = POLITICAS["v1"]
        assert v1.peso_refuerzo == Decimal("0")
        assert v1.peso_refutacion == Decimal("0")
        assert v1.peso_decaimiento == Decimal("0")

    def test_resolver_politica_v1(self):
        assert resolver_politica("v1") is POLITICAS["v1"]

    def test_resolver_politica_version_inexistente_es_ValueError(self):
        with pytest.raises(ValueError, match="no está registrada"):
            resolver_politica("v99")

    def test_una_politica_nueva_no_toca_v1(self):
        """El mecanismo permite que una política nueva exista sin tocar
        una línea de v1 — construirla no muta POLITICAS ni v1 (frozen,
        diccionario aparte). No se registra aquí (eso es RFC-0006/3,
        Parte D) — solo se demuestra que el mecanismo lo soportaría."""
        v1_antes = POLITICAS["v1"]
        candidata = Politica(
            peso_refuerzo=Decimal("0.10"),
            peso_refutacion=Decimal("0.10"),
            peso_decaimiento=Decimal("0.02"),
        )
        assert candidata != v1_antes
        assert POLITICAS["v1"] is v1_antes
        assert POLITICAS["v1"].peso_refuerzo == Decimal("0")

    def test_permite_decaimiento_mayor_que_refuerzo(self):
        """No hay invariante `peso_refuerzo >= peso_decaimiento`: se
        consideró y se descartó durante la implementación de Parte A —
        `confianza.py` ancla la edad lógica a la última validación local
        (A4/A6, ver "Garantías" en el docstring de módulo de
        `confianza.py`), así que una validación recién aplicada siempre
        tiene edad lógica 0 en su propio tick, sin importar la magnitud
        de los pesos. Restringir esta combinación sería una invariante
        sin necesidad matemática real."""
        politica = Politica(
            peso_refuerzo=Decimal("0.01"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0.05"),
        )
        assert politica.peso_decaimiento > politica.peso_refuerzo

    def test_rechaza_pesos_negativos(self):
        with pytest.raises(ValueError, match="no puede ser negativo"):
            Politica(
                peso_refuerzo=Decimal("0"),
                peso_refutacion=Decimal("-0.01"),
                peso_decaimiento=Decimal("0"),
            )

    def test_no_importa_langgraph(self):
        """Toda la Parte A/0 se prueba sin ejecutar LangGraph — criterio
        de cierre de RFC-0006/1: verificación estructural de que ni
        siquiera el módulo de política lo importa."""
        import re
        from pathlib import Path

        fuente = Path(__file__).resolve().parents[3] / "runtime" / "kernel" / "deliberation" / "politica.py"
        texto = fuente.read_text(encoding="utf-8")
        assert not re.search(r"^\s*(import|from)\s+langgraph", texto, re.M)
