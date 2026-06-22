"""
Tests for Sprint L1 — ConceptBlock generation.

Verifies:
1. _build_concept_blocks generates correct number of blocks
2. Each block has all Phase-1 required fields
3. Analogy domain matching (e.g., "Base de Datos" → biblioteca)
4. Curiosity domain matching with real data
5. Media prompt uses concept keywords
6. Graceful degradation when concepts are empty
7. _degraded_result includes concept_blocks: []
8. Schema validation via ConceptBlock Pydantic model
9. Integration: build_orchestration_result includes concept_blocks
"""

import pytest
from unittest.mock import MagicMock

from app.schemas.concept_block import ConceptBlock
from app.services.module_orchestration_service import (
    ModuleOrchestrationService,
    _match_domain,
    _extract_concept_terms,
    _ANALOGY_DOMAINS,
    _CURIOSITY_DOMAINS,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_service() -> ModuleOrchestrationService:
    return ModuleOrchestrationService()


def _make_module(title: str = "Base de Datos", bloom: int = 3) -> MagicMock:
    m = MagicMock()
    m.id    = "module-test-001"
    m.title = title
    m.bloom_level = bloom
    return m


def _make_course(name: str = "Ingeniería de Sistemas") -> MagicMock:
    c = MagicMock()
    c.id   = "course-001"
    c.name = name
    return c


CONCEPTS_BD = [
    "El modelo relacional organiza datos en tablas con filas y columnas, facilitando consultas estructuradas.",
    "Las claves primarias garantizan unicidad de cada registro dentro de una tabla.",
    "Los índices permiten búsquedas eficientes sin recorrer toda la tabla.",
]

CONCEPTS_SO = [
    "El kernel es el núcleo del sistema operativo que gestiona recursos de hardware.",
    "La planificación de procesos determina qué proceso usa la CPU en cada instante.",
]


# ── 1. Número de bloques ──────────────────────────────────────────────────────

class TestConceptBlockCount:

    def test_returns_one_block_per_concept(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Base de Datos",
            concepts=CONCEPTS_BD,
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )
        assert len(blocks) == 3

    def test_caps_at_six_blocks(self):
        svc = _make_service()
        many_concepts = [f"Concepto {i} sobre el tema." for i in range(10)]
        blocks = svc._build_concept_blocks(
            topic="Redes",
            concepts=many_concepts,
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=2,
            orch_id="test",
        )
        assert len(blocks) <= 6

    def test_empty_concepts_returns_empty_list(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Estadística",
            concepts=[],
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=2,
            orch_id="test",
        )
        assert blocks == []


# ── 2. Campos requeridos por bloque ──────────────────────────────────────────

class TestConceptBlockFields:

    def setup_method(self):
        self.svc    = _make_service()
        self.blocks = self.svc._build_concept_blocks(
            topic="Base de Datos",
            concepts=CONCEPTS_BD,
            examples_raw=["Ejemplo de tabla Clientes con id, nombre, email."],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )

    def test_all_blocks_have_id(self):
        for block in self.blocks:
            assert "id" in block and block["id"]

    def test_all_blocks_have_title(self):
        for block in self.blocks:
            assert "title" in block and block["title"]

    def test_all_blocks_have_explanation(self):
        for block in self.blocks:
            assert "explanation" in block and block["explanation"]

    def test_all_blocks_have_analogy(self):
        for block in self.blocks:
            assert block.get("analogy") is not None

    def test_all_blocks_have_curiosity(self):
        for block in self.blocks:
            assert block.get("curiosity") is not None

    def test_all_blocks_have_media_prompt(self):
        for block in self.blocks:
            assert block.get("media_prompt") is not None

    def test_all_blocks_have_mini_activity(self):
        for block in self.blocks:
            assert block.get("mini_activity") is not None
            assert len(block["mini_activity"]["steps"]) >= 2

    def test_first_block_example_from_research(self):
        # Block 0 should receive the first research example
        assert self.blocks[0]["example"] is not None
        assert "Clientes" in self.blocks[0]["example"]

    def test_second_block_no_example(self):
        # Only 1 example provided, block 1+ have no example
        assert self.blocks[1]["example"] is None

    def test_reflection_is_none_in_phase1(self):
        for block in self.blocks:
            assert block.get("reflection") is None

    def test_knowledge_check_is_none_in_phase1(self):
        for block in self.blocks:
            assert block.get("knowledge_check") is None

    def test_blocks_pass_pydantic_validation(self):
        for block in self.blocks:
            validated = ConceptBlock.model_validate(block)
            assert validated.id
            assert validated.explanation


# ── 3. Analogías contextuales ─────────────────────────────────────────────────

class TestAnalogyDomainMatching:

    def _get_analogy(self, topic: str) -> dict | None:
        return _match_domain(topic, _ANALOGY_DOMAINS)

    def test_base_de_datos_matches_biblioteca(self):
        data = self._get_analogy("Base de Datos")
        assert data is not None
        assert "biblioteca" in data["source"]

    def test_sistema_operativo_matches_orquesta(self):
        data = self._get_analogy("Sistemas Operativos")
        assert data is not None
        assert "orquesta" in data["source"]

    def test_redes_matches_carreteras(self):
        data = self._get_analogy("Redes de Computadoras")
        assert data is not None
        assert "carretera" in data["source"]

    def test_programacion_matches_receta(self):
        data = self._get_analogy("Fundamentos de Programación")
        assert data is not None
        assert "receta" in data["source"]

    def test_estadistica_matches_lupa(self):
        data = self._get_analogy("Estadística Descriptiva")
        assert data is not None
        assert "lupa" in data["source"]

    def test_ia_matches_nino(self):
        data = self._get_analogy("Inteligencia Artificial")
        assert data is not None
        assert "niño" in data["source"]

    def test_accent_insensitive_matching(self):
        # "Estadística" vs "estadistica" in domain keywords
        data = self._get_analogy("Estadistica y Probabilidad")
        assert data is not None

    def test_unknown_domain_returns_none(self):
        data = self._get_analogy("Filosofía Medieval")
        assert data is None

    def test_blocks_use_domain_analogy(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Base de Datos",
            concepts=CONCEPTS_BD,
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )
        # All blocks in same module share the domain analogy
        for block in blocks:
            assert "biblioteca" in block["analogy"]["source"]


# ── 4. Curiosidades contextuales ─────────────────────────────────────────────

class TestCuriosityDomainMatching:

    def _get_curiosity(self, topic: str) -> dict | None:
        return _match_domain(topic, _CURIOSITY_DOMAINS)

    def test_base_de_datos_mentions_netflix(self):
        data = self._get_curiosity("Base de Datos")
        assert data is not None
        assert "Netflix" in data["fact"]

    def test_sistema_operativo_mentions_linux(self):
        data = self._get_curiosity("Sistemas Operativos")
        assert data is not None
        assert "Linux" in data["fact"]

    def test_redes_mentions_google(self):
        data = self._get_curiosity("Redes")
        assert data is not None
        assert "Google" in data["fact"]

    def test_ia_mentions_gpt(self):
        data = self._get_curiosity("Inteligencia Artificial")
        assert data is not None
        assert "GPT" in data["fact"]

    def test_curiosity_has_stat(self):
        data = self._get_curiosity("Base de Datos")
        assert data is not None
        assert data.get("stat")

    def test_curiosity_has_source(self):
        data = self._get_curiosity("Redes")
        assert data is not None
        assert data.get("source")

    def test_unknown_domain_returns_none(self):
        data = self._get_curiosity("Latín Clásico")
        assert data is None


# ── 5. Media prompts con keywords del concepto ───────────────────────────────

class TestMediaPromptKeywords:

    def test_extract_concept_terms_returns_words(self):
        text  = "El modelo relacional organiza datos en tablas con filas y columnas."
        terms = _extract_concept_terms(text, 5)
        assert terms  # not empty
        assert "modelo" in terms or "relacional" in terms or "tablas" in terms

    def test_extract_concept_terms_deduplicates(self):
        text  = "tabla tabla tabla índice índice"
        terms = _extract_concept_terms(text, 5)
        assert terms.count("tabla") <= 1

    def test_extract_concept_terms_skips_short_words(self):
        terms = _extract_concept_terms("es la de por", 5)
        assert terms == ""

    def test_media_prompt_contains_concept_keywords(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Base de Datos",
            concepts=["El modelo relacional organiza tablas con índices primarios para búsquedas eficientes."],
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )
        prompt_text = blocks[0]["media_prompt"]["prompt"]
        # At least one concept keyword should appear in the prompt
        assert any(kw in prompt_text for kw in ["modelo", "relacional", "tablas", "indices", "busquedas"])

    def test_media_prompt_type_rotates(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Redes",
            concepts=[f"Concepto {i} sobre protocolos de red y enrutamiento de paquetes." for i in range(3)],
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=2,
            orch_id="test",
        )
        types = {b["media_prompt"]["type"] for b in blocks}
        # Should have at least image; may have video too if 3 blocks
        assert "image" in types


# ── 6. Degradación elegante ───────────────────────────────────────────────────

class TestGracefulDegradation:

    def test_degraded_result_has_empty_concept_blocks(self):
        svc    = _make_service()
        module = _make_module()
        course = _make_course()
        result = svc._degraded_result(module, course, "test-orch")
        assert result["concept_blocks"] == []

    def test_single_concept_generates_one_block(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Cálculo",
            concepts=["La derivada mide la tasa de cambio instantáneo de una función."],
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )
        assert len(blocks) == 1
        assert blocks[0]["analogy"] is not None

    def test_no_crash_with_malformed_examples(self):
        svc = _make_service()
        blocks = svc._build_concept_blocks(
            topic="Estadística",
            concepts=CONCEPTS_BD[:2],
            examples_raw=[None, {}, 42],   # malformed
            misconceptions_raw=[],
            bloom_target=2,
            orch_id="test",
        )
        # Should not raise; may or may not attach example
        assert len(blocks) == 2


# ── 7. _build_orchestration_result includes concept_blocks ───────────────────

class TestOrchestrationResultIntegration:

    def _build_result(self, topic: str, concepts: list[str]) -> dict:
        svc = _make_service()
        research_state = {
            "research": {
                "concepts": [{"concept": c} for c in concepts],
                "examples": ["Ejemplo práctico."],
                "misconceptions": [],
                "real_applications": [],
                "multimodal_prompts": [],
                "sources": [],
                "degraded": False,
                "confidence_score": 0.8,
            },
            "research_metrics": {"pedagogical_confidence": 0.8},
            "consistency_validation": {"valid": True},
        }
        module = _make_module(topic)
        course = _make_course()
        return svc._build_orchestration_result(
            research_state, MagicMock(), course, module, 3, "test-orch"
        )

    def test_result_has_concept_blocks_field(self):
        result = self._build_result("Base de Datos", CONCEPTS_BD)
        assert "concept_blocks" in result

    def test_concept_blocks_is_list(self):
        result = self._build_result("Base de Datos", CONCEPTS_BD)
        assert isinstance(result["concept_blocks"], list)

    def test_concept_blocks_count_matches_concepts(self):
        result = self._build_result("Redes", CONCEPTS_SO)
        assert len(result["concept_blocks"]) == len(CONCEPTS_SO)

    def test_result_with_no_concepts_has_empty_blocks(self):
        result = self._build_result("Filosofía Medieval", [])
        assert result["concept_blocks"] == []

    def test_result_validates_as_pydantic_schema(self):
        from app.schemas.progress import ModuleOrchestrationResponse
        result = self._build_result("Base de Datos", CONCEPTS_BD)
        schema = ModuleOrchestrationResponse.model_validate(result)
        assert len(schema.concept_blocks) == len(CONCEPTS_BD)
        assert schema.concept_blocks[0].analogy is not None
