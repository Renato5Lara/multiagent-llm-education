"""
Tests for Sprint L1 + Sprint M1 — ConceptBlock generation.

Verifies:
1. _build_concept_blocks generates correct number of blocks (capped at MAX_CONCEPT_BLOCKS)
2. Each block has all Phase-1 required fields
3. Analogy domain matching (e.g., "Base de Datos" → biblioteca)
4. Curiosity domain matching with real data
5. Media prompt uses concept keywords
6. Graceful degradation when concepts are empty
7. _degraded_result includes concept_blocks: []
8. Schema validation via ConceptBlock Pydantic model
9. Integration: build_orchestration_result includes concept_blocks
10. Sprint M1: LLM enrichment path sets prediction_question / reflection_question
11. Sprint M1: Template fallback when LLM unavailable or fails
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.concept_block import ConceptBlock
from app.services.module_orchestration_service import (
    MAX_CONCEPT_BLOCKS,
    ModuleOrchestrationService,
    _build_context_snippets,
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
    m.id          = "module-test-001"
    m.title       = title
    m.bloom_level = bloom
    return m


def _make_course(name: str = "Ingeniería de Sistemas") -> MagicMock:
    c = MagicMock()
    c.id   = "course-001"
    c.name = name
    return c


def _run_blocks(svc: ModuleOrchestrationService, **kwargs) -> list:
    """Synchronous wrapper for the async _build_concept_blocks method."""
    return asyncio.run(svc._build_concept_blocks(**kwargs))


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
        svc    = _make_service()
        blocks = _run_blocks(
            svc,
            topic="Base de Datos",
            concepts=CONCEPTS_BD,
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=3,
            orch_id="test",
        )
        assert len(blocks) == len(CONCEPTS_BD)

    def test_caps_at_max_concept_blocks(self):
        svc           = _make_service()
        many_concepts = [f"Concepto {i} sobre el tema." for i in range(10)]
        blocks        = _run_blocks(
            svc,
            topic="Redes",
            concepts=many_concepts,
            examples_raw=[],
            misconceptions_raw=[],
            bloom_target=2,
            orch_id="test",
        )
        assert len(blocks) <= MAX_CONCEPT_BLOCKS

    def test_empty_concepts_returns_empty_list(self):
        svc    = _make_service()
        blocks = _run_blocks(
            svc,
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
        svc = _make_service()
        # Force template path — these tests verify template field shapes,
        # not LLM output.  Without the patch, a real OPENAI_API_KEY triggers
        # the LLM path and assertion values change unpredictably.
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            self.blocks = _run_blocks(
                svc,
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

    def test_template_path_has_no_prediction_question(self):
        # Template fallback (no LLM) → M1 fields are None
        for block in self.blocks:
            assert block.get("prediction_question") is None
            assert block.get("reflection_question") is None

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
        data = self._get_analogy("Estadistica y Probabilidad")
        assert data is not None

    def test_unknown_domain_returns_none(self):
        data = self._get_analogy("Filosofía Medieval")
        assert data is None

    def test_blocks_use_domain_analogy(self):
        # Template path must use _ANALOGY_DOMAINS table for "Base de Datos"
        svc = _make_service()
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            blocks = _run_blocks(
                svc,
                topic="Base de Datos",
                concepts=CONCEPTS_BD,
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test",
            )
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
        assert terms
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
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            blocks = _run_blocks(
                svc,
                topic="Base de Datos",
                concepts=["El modelo relacional organiza tablas con índices primarios para búsquedas eficientes."],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test",
            )
        prompt_text = blocks[0]["media_prompt"]["prompt"]
        assert any(kw in prompt_text for kw in ["modelo", "relacional", "tablas", "indices", "busquedas"])

    def test_media_prompt_type_rotates(self):
        svc = _make_service()
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            blocks = _run_blocks(
                svc,
                topic="Redes",
                concepts=[f"Concepto {i} sobre protocolos de red y enrutamiento de paquetes." for i in range(3)],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=2,
                orch_id="test",
            )
        types = {b["media_prompt"]["type"] for b in blocks}
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
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            blocks = _run_blocks(
                svc,
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
        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False
            blocks = _run_blocks(
                svc,
                topic="Estadística",
                concepts=CONCEPTS_BD[:2],
                examples_raw=[None, {}, 42],
                misconceptions_raw=[],
                bloom_target=2,
                orch_id="test",
            )
        assert len(blocks) == 2


# ── 7. _build_orchestration_result includes concept_blocks ───────────────────

class TestOrchestrationResultIntegration:

    def _build_result(self, topic: str, concepts: list[str]) -> dict:
        svc            = _make_service()
        research_state = {
            "research": {
                "concepts":          [{"concept": c} for c in concepts],
                "examples":          ["Ejemplo práctico."],
                "misconceptions":    [],
                "real_applications": [],
                "multimodal_prompts": [],
                "sources":           [],
                "degraded":          False,
                "confidence_score":  0.8,
            },
            "research_metrics":       {"pedagogical_confidence": 0.8},
            "consistency_validation": {"valid": True},
        }
        module = _make_module(topic)
        course = _make_course()
        return asyncio.run(
            svc._build_orchestration_result(
                research_state, MagicMock(), course, module, 3, "test-orch"
            )
        )

    def test_result_has_concept_blocks_field(self):
        result = self._build_result("Base de Datos", CONCEPTS_BD)
        assert "concept_blocks" in result

    def test_concept_blocks_is_list(self):
        result = self._build_result("Base de Datos", CONCEPTS_BD)
        assert isinstance(result["concept_blocks"], list)

    def test_concept_blocks_count_within_max(self):
        result = self._build_result("Redes", CONCEPTS_SO)
        # CONCEPTS_SO has 2 items < MAX_CONCEPT_BLOCKS, so all are included
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


# ── 8. Sprint M1: _build_context_snippets ─────────────────────────────────────

class TestBuildContextSnippets:

    def test_returns_string(self):
        snippets = _build_context_snippets(["Base de datos", "Índices"], [], [])
        assert isinstance(snippets, str)

    def test_includes_concept_strings(self):
        snippets = _build_context_snippets(["modelo relacional"], [], [])
        assert "modelo relacional" in snippets

    def test_includes_example_preview(self):
        snippets = _build_context_snippets(
            [],
            [{"example": "Tabla Clientes"}],
            [],
        )
        assert "Clientes" in snippets

    def test_includes_misconception(self):
        snippets = _build_context_snippets(
            [],
            [],
            [{"misconception": "SQL es lento"}],
        )
        assert "SQL es lento" in snippets

    def test_empty_inputs_returns_empty_string(self):
        snippets = _build_context_snippets([], [], [])
        assert snippets == ""


# ── 9. Sprint M1: LLM enrichment path ────────────────────────────────────────

class TestLLMEnrichmentPath:

    def _make_llm_response(self) -> object:
        from app.llm.service import LLMResponse
        payload = {
            "explanation":         "Imagina que los datos son libros en una biblioteca perfectamente organizada...",
            "analogy":             {"source": "biblioteca", "explanation": "Cada tabla es un estante temático."},
            "curiosity":           {"fact": "Netflix gestiona 125M usuarios con BD distribuidas.", "stat": "125M", "source": "Netflix Tech Blog, 2023"},
            "mini_activity":       {"instructions": "Identifica una tabla en tu vida diaria.", "steps": ["Piensa en un objeto cotidiano", "Describe sus atributos como columnas", "Imagina varios registros"]},
            "prediction_question": "¿Qué crees que es una tabla en una base de datos?",
            "reflection_question": "¿Cómo aplicarías el modelo relacional en un proyecto real?",
            "media_prompt":        {"type": "image", "title": "Visualiza una BD", "prompt": "Crea una infografía...", "learning_goal": "Reforzar la memoria visual."},
        }
        return LLMResponse(
            content=str(payload),
            parsed=payload,
            model="gpt-4o-mini",
            provider="openai",
            tokens_prompt=100,
            tokens_completion=300,
            tokens_total=400,
            confidence_raw=0.9,
            duration_ms=800.0,
            success=True,
        )

    def test_llm_path_sets_prediction_question(self):
        svc          = _make_service()
        mock_resp    = self._make_llm_response()

        with (
            patch("app.services.module_orchestration_service.settings") as mock_settings,
            patch("app.services.module_orchestration_service.LLMService") as MockLLMService,
        ):
            mock_settings.has_openai     = True
            mock_settings.OPENAI_API_KEY = "sk-test"
            MockLLMService.return_value.generate = AsyncMock(return_value=mock_resp)

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-llm",
            ))

        assert len(blocks) == 1
        assert blocks[0]["prediction_question"] == "¿Qué crees que es una tabla en una base de datos?"
        assert blocks[0]["reflection_question"] == "¿Cómo aplicarías el modelo relacional en un proyecto real?"

    def test_llm_path_uses_narrative_explanation(self):
        svc       = _make_service()
        mock_resp = self._make_llm_response()

        with (
            patch("app.services.module_orchestration_service.settings") as mock_settings,
            patch("app.services.module_orchestration_service.LLMService") as MockLLMService,
        ):
            mock_settings.has_openai     = True
            mock_settings.OPENAI_API_KEY = "sk-test"
            MockLLMService.return_value.generate = AsyncMock(return_value=mock_resp)

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-llm",
            ))

        assert "Imagina que" in blocks[0]["explanation"]

    def test_llm_path_passes_pydantic_validation(self):
        svc       = _make_service()
        mock_resp = self._make_llm_response()

        with (
            patch("app.services.module_orchestration_service.settings") as mock_settings,
            patch("app.services.module_orchestration_service.LLMService") as MockLLMService,
        ):
            mock_settings.has_openai     = True
            mock_settings.OPENAI_API_KEY = "sk-test"
            MockLLMService.return_value.generate = AsyncMock(return_value=mock_resp)

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-llm",
            ))

        validated = ConceptBlock.model_validate(blocks[0])
        assert validated.prediction_question is not None
        assert validated.reflection_question is not None


# ── 10. Sprint M1: Template fallback ─────────────────────────────────────────

class TestTemplateFallback:

    def test_llm_exception_falls_back_to_template(self):
        """RuntimeError during LLM call → template path, M1 fields are None."""
        svc = _make_service()

        with (
            patch("app.services.module_orchestration_service.settings") as mock_settings,
            patch("app.services.module_orchestration_service.LLMService") as MockLLMService,
        ):
            mock_settings.has_openai     = True
            mock_settings.OPENAI_API_KEY = "sk-test"
            MockLLMService.return_value.generate = AsyncMock(side_effect=RuntimeError("network error"))

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-fallback",
            ))

        assert len(blocks) == 1
        assert blocks[0]["prediction_question"] is None
        assert blocks[0]["reflection_question"] is None
        assert blocks[0]["analogy"] is not None

    def test_no_openai_key_uses_template(self):
        """settings.has_openai=False → no LLM call, template path."""
        svc = _make_service()

        with patch("app.services.module_orchestration_service.settings") as mock_settings:
            mock_settings.has_openai = False

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-no-key",
            ))

        assert blocks[0]["prediction_question"] is None
        assert blocks[0]["analogy"] is not None

    def test_llm_returns_no_parsed_falls_back(self):
        """LLM success=False or parsed=None → template path."""
        from app.llm.service import LLMResponse
        svc          = _make_service()
        bad_response = LLMResponse(
            content="",
            parsed=None,
            model="gpt-4o-mini",
            provider="openai",
            tokens_prompt=0,
            tokens_completion=0,
            tokens_total=0,
            confidence_raw=0.0,
            duration_ms=100.0,
            success=False,
            error="rate_limit",
        )

        with (
            patch("app.services.module_orchestration_service.settings") as mock_settings,
            patch("app.services.module_orchestration_service.LLMService") as MockLLMService,
        ):
            mock_settings.has_openai     = True
            mock_settings.OPENAI_API_KEY = "sk-test"
            MockLLMService.return_value.generate = AsyncMock(return_value=bad_response)

            blocks = asyncio.run(svc._build_concept_blocks(
                topic="Base de Datos",
                concepts=CONCEPTS_BD[:1],
                examples_raw=[],
                misconceptions_raw=[],
                bloom_target=3,
                orch_id="test-bad-resp",
            ))

        assert blocks[0]["prediction_question"] is None
        assert blocks[0]["analogy"] is not None
