"""
Tests para el motor de explicaciones multimodales.
"""

import pytest


class TestExplanationBuilder:
    def test_build_empty(self):
        from app.services.explanation_service import ExplanationBuilder
        builder = ExplanationBuilder("Test")
        result = builder.build()
        assert result["title"] == "Test"
        assert result["chunks"] == []

    def test_add_intro(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_intro("Hola").build()
        assert result["chunks"][0]["type"] == "text"
        assert result["chunks"][0]["data"]["content"] == "Hola"

    def test_add_code(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_code("print('hi')", "python", caption="Ejemplo").build()
        types = [c["type"] for c in result["chunks"]]
        assert "text" in types
        assert "code" in types

    def test_add_step(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_step(1, "Primer paso", code="x = 1").build()
        chunks = result["chunks"]
        assert chunks[0]["type"] == "text"
        assert "Paso 1" in chunks[0]["data"]["content"]
        assert chunks[1]["type"] == "code"

    def test_add_comparison(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_comparison("C", "A", "1", "B", "2").build()
        chunk = result["chunks"][0]
        assert chunk["type"] == "comparison"
        assert chunk["data"]["left_label"] == "A"
        assert chunk["data"]["right_label"] == "B"

    def test_add_formula(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_formula("E=mc^2", description="Relatividad").build()
        assert result["chunks"][0]["type"] == "text"
        assert result["chunks"][1]["type"] == "formula"
        assert result["chunks"][1]["data"]["latex"] == "E=mc^2"

    def test_add_table(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_table(
            ["N", "Square"], [["1", "1"], ["2", "4"]], caption="Squares"
        ).build()
        assert result["chunks"][0]["type"] == "text"
        chunk = result["chunks"][1]
        assert chunk["type"] == "table"
        assert chunk["data"]["headers"] == ["N", "Square"]
        assert len(chunk["data"]["rows"]) == 2

    def test_add_bullet_list(self):
        from app.services.explanation_service import ExplanationBuilder
        result = ExplanationBuilder("T").add_bullet_list("Key points", ["a", "b"]).build()
        assert result["chunks"][0]["type"] == "text"
        assert "Key points" in result["chunks"][0]["data"]["content"]


class TestAlgorithmExplainer:
    def test_quicksort_explanation(self):
        from app.services.explanation_service import algorithm_explainer
        result = algorithm_explainer.explain_sorting("quicksort")
        assert result["title"] == "Algoritmo: Quicksort"
        assert any(c["type"] == "code" for c in result["chunks"])
        assert any(c["type"] == "comparison" for c in result["chunks"])
        assert any("O(n log n)" in str(c) for c in result["chunks"])

    def test_binary_search_explanation(self):
        from app.services.explanation_service import algorithm_explainer
        result = algorithm_explainer.explain_binary_search()
        assert result["title"] == "Búsqueda Binaria"
        assert any("O(log n)" in str(c) for c in result["chunks"])


class TestExplanationGenerator:
    def test_template_explanation(self):
        from app.services.explanation_service import ExplanationGenerator
        gen = ExplanationGenerator()
        result = gen._template_explanation("linked lists")
        assert result["title"] == "linked lists"
        assert "chunks" in result
        assert len(result["chunks"]) >= 3
        assert any(c["type"] == "code" for c in result["chunks"])

    def test_template_explanation_with_context(self):
        from app.services.explanation_service import ExplanationGenerator
        gen = ExplanationGenerator()
        result = gen._template_explanation("sorting", {"cycle": 2})
        assert "sorting" in result["title"]

    @pytest.mark.asyncio
    async def test_generate_explanation_fallback(self):
        from app.services.explanation_service import ExplanationGenerator
        gen = ExplanationGenerator()
        gen.use_openai = False
        result = await gen.generate_explanation("recursion")
        assert "chunks" in result
        assert result["title"] == "recursion"
