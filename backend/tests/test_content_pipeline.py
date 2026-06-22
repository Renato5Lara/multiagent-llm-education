"""
Tests for the content generation pipeline neutrality fix.

Verifies that:
1. _generate_queries() produces no CS-domain hardcoded terms
2. Fallback templates produce neutral text for non-CS topics
3. _validate_generated_content() correctly flags CS contamination
"""

import pytest
from unittest.mock import MagicMock

from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy, RetrievalContext
from app.services.module_orchestration_service import ModuleOrchestrationService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_context(topic: str, bloom: int = 2, objectives: list[str] | None = None) -> RetrievalContext:
    return RetrievalContext(
        topic=topic,
        bloom_target=bloom,
        objectives=objectives or [],
        learning_style="",
        preferred_analogies=[],
    )


FORBIDDEN_IN_QUERIES = [
    "recorrido busqueda insercion",
    "recorrido",
    "busqueda insercion",
    "estructuras de datos",
    "busqueda binaria",
    "código de arreglos",
]

CS_CONTAMINATION_TOKENS = [
    "estructura de datos",
    "lista enlazada",
    "posición de memoria",
    "posicion de memoria",
    "arreglo",
    "búsqueda binaria",
    "busqueda binaria",
]

NON_CS_TOPICS = [
    "Estadística I",
    "Comunicación I",
    "Ciudadanía y Responsabilidad Social",
    "Base de Datos",
    "Sistemas Operativos",
]


# ── Fase 1: retrieval queries ─────────────────────────────────────────────────

class TestRetrievalQueries:
    def setup_method(self):
        self.strategy = PedagogicalRetrievalStrategy.__new__(PedagogicalRetrievalStrategy)

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_queries_contain_no_hardcoded_cs_terms(self, topic):
        ctx = _make_context(topic)
        queries = self.strategy._generate_queries(ctx)
        all_text = " ".join(q for q, _ in queries).lower()
        for forbidden in FORBIDDEN_IN_QUERIES:
            assert forbidden not in all_text, (
                f"Query for topic={topic!r} contains forbidden term {forbidden!r}. "
                f"Full queries: {[q for q, _ in queries]}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_queries_contain_topic(self, topic):
        ctx = _make_context(topic)
        queries = self.strategy._generate_queries(ctx)
        for q_text, _ in queries:
            assert topic.lower() in q_text.lower(), (
                f"Query {q_text!r} does not contain topic {topic!r}"
            )

    def test_objectives_used_when_provided(self):
        ctx = _make_context("Cálculo I", objectives=["derivadas", "integrales"])
        queries = self.strategy._generate_queries(ctx)
        all_text = " ".join(q for q, _ in queries).lower()
        assert "derivadas" in all_text or "integrales" in all_text

    def test_objectives_fallback_uses_topic_not_cs(self):
        ctx = _make_context("Estadística I", objectives=[])
        queries = self.strategy._generate_queries(ctx)
        all_text = " ".join(q for q, _ in queries).lower()
        # old fallback was "recorrido, busqueda e insercion" — must not appear
        assert "recorrido" not in all_text
        assert "insercion" not in all_text


# ── Fase 2: fallback templates ────────────────────────────────────────────────

class TestFallbackTemplates:
    def setup_method(self):
        self.svc = ModuleOrchestrationService()

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_introduction_contains_topic(self, topic):
        text = self.svc._generate_introduction(topic, [])
        assert topic.lower() in text.lower(), f"Introduction missing topic {topic!r}: {text[:200]}"

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_introduction_has_no_cs_contamination(self, topic):
        text = self.svc._generate_introduction(topic, []).lower()
        for token in CS_CONTAMINATION_TOKENS:
            assert token not in text, (
                f"Introduction for {topic!r} contains CS token {token!r}. Text: {text[:300]}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_explanation_fallback_has_no_cs_contamination(self, topic):
        text = self.svc._generate_explanation(topic, [], bloom_target=2).lower()
        for token in CS_CONTAMINATION_TOKENS:
            assert token not in text, (
                f"Explanation for {topic!r} contains CS token {token!r}. Text: {text[:300]}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_misconceptions_fallback_has_no_cs_contamination(self, topic):
        items = self.svc._build_misconceptions([], topic)
        all_text = " ".join(
            f"{i['misconception']} {i['correction']}" for i in items
        ).lower()
        for token in CS_CONTAMINATION_TOKENS:
            assert token not in all_text, (
                f"Misconceptions for {topic!r} contain CS token {token!r}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_examples_fallback_has_no_cs_contamination(self, topic):
        items = self.svc._build_examples([], topic, bloom_target=2)
        all_text = " ".join(items).lower()
        for token in CS_CONTAMINATION_TOKENS:
            assert token not in all_text, (
                f"Examples for {topic!r} contain CS token {token!r}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_applications_fallback_has_no_cs_contamination(self, topic):
        items = self.svc._build_real_applications([], topic)
        all_text = " ".join(items).lower()
        for token in CS_CONTAMINATION_TOKENS:
            assert token not in all_text, (
                f"Applications for {topic!r} contain CS token {token!r}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_guided_practice_has_no_cs_contamination(self, topic):
        text = self.svc._generate_guided_practice(topic, bloom_target=3).lower()
        cs_specific = ["búsqueda binaria", "busqueda binaria", "10 elementos", "lista enlazada", "arreglo"]
        for token in cs_specific:
            assert token not in text, (
                f"Guided practice for {topic!r} contains CS token {token!r}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_continuity_notes_has_no_cs_contamination(self, topic):
        module_mock = MagicMock()
        module_mock.title = topic
        course_mock = MagicMock()
        course_mock.name = "Curso de prueba"
        text = self.svc._generate_continuity_notes(topic, module_mock, course_mock).lower()
        cs_specific = ["lista enlazada", "pilas, colas", "tads", "gestión de memoria", "gestion de memoria"]
        for token in cs_specific:
            assert token not in text, (
                f"Continuity notes for {topic!r} contain CS token {token!r}"
            )

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_pedagogical_stages_has_no_cs_contamination(self, topic):
        stages = self.svc._build_pedagogical_stages(topic, bloom_target=3, concepts=[])
        all_text = " ".join(
            f"{s['content']} {' '.join(s['examples'])}" for s in stages
        ).lower()
        cs_specific = ["recorrido, búsqueda y modificación", "estructuras de datos y patrones", "esta estructura"]
        for token in cs_specific:
            assert token not in all_text, (
                f"Pedagogical stages for {topic!r} contain CS token {token!r}"
            )


# ── Fase 3: semantic validation ───────────────────────────────────────────────

class TestSemanticValidation:
    def setup_method(self):
        self.svc = ModuleOrchestrationService()

    # ── Keyword extraction ────────────────────────────────────────────────────

    def test_keyword_extraction_strips_noise_words(self):
        kws = ModuleOrchestrationService._topic_keywords("Semana 1: Estadística I")
        # "semana", "estadística" — "semana" is a stopword, "i" too short; only "estadística" survives
        assert "estadística" in kws
        assert "semana" not in kws

    def test_keyword_extraction_communicacion(self):
        kws = ModuleOrchestrationService._topic_keywords("Comunicación I")
        assert "comunicación" in kws

    # ── Topic presence checks ─────────────────────────────────────────────────

    def test_valid_content_passes(self):
        intro = "Este módulo introduce Estadística I y sus conceptos fundamentales."
        expl  = "Estadística I abarca principios de probabilidad y análisis de datos."
        assert self.svc._validate_generated_content("Estadística I", intro, expl, "test-id") is True

    def test_semana_prefix_topic_passes_when_keyword_present(self):
        """'Semana 1: Estadística I' — content references 'estadística', not 'semana 1:'."""
        intro = "En este módulo aprenderás Estadística I desde sus fundamentos."
        expl  = "El estudio de Estadística I permite analizar datos con rigor."
        assert self.svc._validate_generated_content("Semana 1: Estadística I", intro, expl, "test-id") is True

    def test_topic_absent_from_intro_fails(self):
        intro = "Bienvenido al módulo. Este tema es muy importante en el curso."
        expl  = "Estadística I abarca principios de análisis de datos."
        assert self.svc._validate_generated_content("Estadística I", intro, expl, "test-id") is False

    def test_topic_absent_from_explanation_fails(self):
        intro = "Estadística I es un tema fundamental del curso."
        expl  = "Los arreglos son estructuras de datos que almacenan elementos."
        assert self.svc._validate_generated_content("Estadística I", intro, expl, "test-id") is False

    # ── CS contamination ──────────────────────────────────────────────────────

    def test_cs_contamination_in_comunicacion_fails(self):
        """'Comunicación I' is not a CS course — 'estructura de datos' must be rejected."""
        intro = "Comunicación I es un tema importante del curso."
        expl  = "Comunicación I es una estructura de datos fundamental."
        assert self.svc._validate_generated_content("Comunicación I", intro, expl, "test-id") is False

    def test_cs_contamination_in_estadistica_fails(self):
        intro = "Estadística I es un tema importante del curso."
        expl  = "Estadística I es una estructura de datos fundamental."
        assert self.svc._validate_generated_content("Estadística I", intro, expl, "test-id") is False

    def test_cs_contamination_allowed_for_arreglos(self):
        intro = "Arreglos son estructuras de datos del curso."
        expl  = "Los arreglos permiten almacenar múltiples elementos."
        assert self.svc._validate_generated_content("Arreglos", intro, expl, "test-id") is True

    def test_base_de_datos_allows_estructura_de_datos(self):
        """'Base de Datos' is a CS course — 'estructura de datos' is valid there."""
        intro = "Base de Datos cubre el diseño de estructuras de datos relacionales."
        expl  = "En Base de Datos aprenderás sobre tablas, índices y relaciones."
        assert self.svc._validate_generated_content("Base de Datos", intro, expl, "test-id") is True

    def test_sistemas_operativos_allows_cs_terms(self):
        intro = "Sistemas Operativos estudia la gestión de procesos y memoria."
        expl  = "En Sistemas Operativos se abordan algoritmos de planificación y estructuras del kernel."
        assert self.svc._validate_generated_content("Sistemas Operativos", intro, expl, "test-id") is True

    # ── End-to-end: fallbacks must pass for every non-CS topic ────────────────

    @pytest.mark.parametrize("topic", NON_CS_TOPICS)
    def test_clean_fallbacks_pass_validation(self, topic):
        """Corrected fallback templates must pass semantic validation."""
        intro = self.svc._generate_introduction(topic, [])
        expl  = self.svc._generate_explanation(topic, [], bloom_target=2)
        result = self.svc._validate_generated_content(topic, intro, expl, "test-id")
        assert result is True, (
            f"Fallback content for {topic!r} failed semantic validation.\n"
            f"intro: {intro[:200]}\nexpl:  {expl[:200]}"
        )
