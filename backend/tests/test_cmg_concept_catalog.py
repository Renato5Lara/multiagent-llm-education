"""Tests de cobertura de los 32 conceptos del currículo IS301 —
corrige el hallazgo real del primer E2E (fallback genérico de
`ProgrammerAgent` para conceptos fuera de "arreglos"). Verifica que
CADA concepto tenga plantilla específica, que D1/D3 pasen con
contenido real, y que ningún concepto reciba la plantilla de otro."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.concept import Concept
from app.models.learning_objective import LearningObjective
from app.services.cmg_concept_catalog import MODULOS_CUBIERTOS, _CATALOGO, conceptos_cubiertos
from app.services.cmg_evaluation_service import evaluar_d1, evaluar_d3
from app.services.cmg_generation_service import CONTROL_CONFIG, generar_cmg


@pytest.fixture(autouse=True)
def _sin_llm(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")


def _concept(titulo: str, i: int) -> Concept:
    return Concept(id=f"c-{i}", title=titulo, learning_objective_id="lo-1", order=i)


def _objetivo(bloom_level: int = 4) -> LearningObjective:
    return LearningObjective(id="lo-1", course_id="course-1", title="Objetivo de prueba", bloom_level=bloom_level, order=1)


class TestCoberturaCompleta:
    def test_los_32_conceptos_reales_tienen_plantilla(self):
        """Cruza el catálogo contra el currículo REAL sembrado por
        `d6e7f8a9b0c1_migrate_is301_to_8_modules.py` (parseado por AST,
        sin ejecutar la migración) — 32/32, ni uno de más ni de menos."""
        import ast

        with open("alembic/versions/d6e7f8a9b0c1_migrate_is301_to_8_modules.py") as f:
            arbol = ast.parse(f.read())
        conceptos_por_modulo = None
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Assign) and any(
                getattr(t, "id", None) == "CONCEPTS_BY_MODULE" for t in nodo.targets
            ):
                conceptos_por_modulo = ast.literal_eval(nodo.value)
                break
        assert conceptos_por_modulo is not None

        conceptos_reales = {c for lista in conceptos_por_modulo.values() for c in lista}
        assert len(conceptos_reales) == 32
        assert set(conceptos_cubiertos()) == conceptos_reales

        for modulo, lista in conceptos_por_modulo.items():
            for titulo in lista:
                assert _CATALOGO[titulo].modulo == modulo

    @pytest.mark.parametrize("modulo", MODULOS_CUBIERTOS)
    async def test_cada_modulo_genera_contenido_especifico(self, modulo):
        """Por módulo: cada uno de sus conceptos produce un CMG cuyo
        código y ejercicio provienen del catálogo (§FASE 8, item 1)."""
        conceptos_del_modulo = [t for t, p in _CATALOGO.items() if p.modulo == modulo]
        assert conceptos_del_modulo
        for i, titulo in enumerate(conceptos_del_modulo):
            cmg = await generar_cmg(_concept(titulo, i), _objetivo(), CONTROL_CONFIG)
            assert cmg.code_source == "catalog-v1"
            assert cmg.code
            assert cmg.exercise.prompt


_CONCEPTOS_REPRESENTATIVOS = (
    "Algoritmo",
    "Variables",
    "Operadores aritméticos básicos",
    "Condicionales básicos",
    "Bucle while",
    "Bucle for",
    "Definición e invocación de funciones",
    "Creación y estructura de arreglos (listas)",
    "Recursividad",
)


class TestConceptosRepresentativos:
    @pytest.mark.parametrize("titulo", _CONCEPTOS_REPRESENTATIVOS)
    async def test_d1_pasa_con_contenido_real(self, titulo):
        concept = _concept(titulo, 0)
        objetivo = _objetivo()
        cmg = await generar_cmg(concept, objetivo, CONTROL_CONFIG)
        resultado = evaluar_d1(concept, objetivo, cmg)
        assert resultado.passed, resultado.issues

    @pytest.mark.parametrize("titulo", _CONCEPTOS_REPRESENTATIVOS)
    async def test_d3_pasa_con_contenido_real(self, titulo):
        concept = _concept(titulo, 0)
        cmg = await generar_cmg(concept, _objetivo(), CONTROL_CONFIG)
        resultado = evaluar_d3(concept, cmg)
        assert resultado.passed, resultado.issues

    async def test_while_usa_la_palabra_clave_while_en_el_codigo(self):
        cmg = await generar_cmg(_concept("Bucle while", 0), _objetivo(), CONTROL_CONFIG)
        assert "while" in cmg.code

    async def test_recursividad_usa_una_llamada_recursiva_real(self):
        cmg = await generar_cmg(_concept("Recursividad", 0), _objetivo(), CONTROL_CONFIG)
        # La función se llama a sí misma — evidencia de recursividad real,
        # no solo texto que menciona la palabra.
        assert cmg.code.count("factorial(") >= 2


class TestSinFugaDePlantillaGenerica:
    async def test_dos_conceptos_distintos_no_comparten_codigo(self):
        """§FASE 8, item 3: ningún concepto recibe la plantilla de otro
        (ni la genérica de ProgrammerAgent para conceptos del catálogo
        cerrado)."""
        cmg_while = await generar_cmg(_concept("Bucle while", 0), _objetivo(), CONTROL_CONFIG)
        cmg_recursion = await generar_cmg(_concept("Recursividad", 1), _objetivo(), CONTROL_CONFIG)
        cmg_funciones = await generar_cmg(
            _concept("Definición e invocación de funciones", 2), _objetivo(), CONTROL_CONFIG
        )
        codigos = {cmg_while.code, cmg_recursion.code, cmg_funciones.code}
        assert len(codigos) == 3  # los tres son distintos entre sí

    async def test_concepto_del_catalogo_nunca_produce_el_fallback_generico(self):
        cmg = await generar_cmg(_concept("Bucle while", 0), _objetivo(), CONTROL_CONFIG)
        assert "resolver()" not in cmg.code  # firma del fallback genérico de ProgrammerAgent
        assert cmg.code_source == "catalog-v1"

    async def test_concepto_fuera_del_catalogo_cae_al_fallback_marcado_explicitamente(self):
        """Un `Concept` que no pertenece al catálogo cerrado (currículo
        futuro, o error de datos) debe seguir generando ALGO — vía
        `ProgrammerAgent` — pero la trazabilidad debe dejarlo explícito,
        nunca disfrazado de cobertura real."""
        concept = _concept("Concepto inexistente fuera del catálogo IS301", 99)
        cmg = await generar_cmg(concept, _objetivo(), CONTROL_CONFIG)
        assert cmg.code_source == "programmer_agent_fallback"
