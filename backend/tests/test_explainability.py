"""
Tests for explainable adaptive pedagogy.

Every test proves that the system can explain WHY it adapted content.
"""

from __future__ import annotations

import pytest
from app.explainability.adaptive_reasoning import AdaptiveReasoning
from app.explainability.bloom_explainer import BloomExplainer
from app.explainability.cognitive_load_analysis import CognitiveLoadAnalysis
from app.explainability.personalization_trace import PersonalizationTrace
from app.explainability.adaptation_decision_graph import AdaptationDecisionGraph


# =============================================================================
# BloomExplainer
# =============================================================================


class TestBloomExplainer:
    def test_explains_reduction_due_to_cognitive_overload(self):
        """Bloom 4→3 when cognitive_load_trend='increasing'."""
        explainer = BloomExplainer()
        profile = {
            "cognitive_load_trend": "increasing",
            "cognitive_load_signals": [0.5, 0.7, 0.82],
            "engagement_pattern": "consistent",
            "pacing": "moderate",
        }
        adaptive_plan = {
            "bloom_target": 3,
            "original_bloom_target": 4,
            "adaptation_rationale": {"learning_style": "visual"},
        }
        explanation = explainer.explain(profile, adaptive_plan)

        assert explanation.dimension == "bloom"
        assert explanation.previous_value == 4
        assert explanation.new_value == 3
        assert explanation.confidence > 0.4  # sum(contributions * 0.9) = 0.45

        factors = [r.factor for r in explanation.reasons]
        assert "cognitive_load_score" in factors
        assert explanation.reasons[0].evidence

    def test_explains_reduction_with_misconceptions_and_engagement(self):
        """Bloom 4→3 with additional contributing factors."""
        explainer = BloomExplainer()
        profile = {
            "cognitive_load_trend": "increasing",
            "cognitive_load_signals": [0.8],
            "common_misconceptions": [{"misconception": "a"}, {"misconception": "b"}, {"misconception": "c"}],
            "engagement_pattern": "dropping",
            "pacing": "slow",
        }
        adaptive_plan = {
            "bloom_target": 3,
            "original_bloom_target": 4,
            "adaptation_rationale": {},
        }
        explanation = explainer.explain(profile, adaptive_plan)

        factors = [r.factor for r in explanation.reasons]
        assert "misconception_persistence" in factors
        assert "engagement_decay" in factors
        assert "historical_pacing" in factors

    def test_explains_increase_due_to_bloom_attainment(self):
        """Bloom 3→4 when student reached level 4 previously."""
        explainer = BloomExplainer()
        profile = {
            "bloom_level_reached": 4,
            "engagement_pattern": "consistent",
        }
        adaptive_plan = {
            "bloom_target": 4,
            "original_bloom_target": 3,
            "adaptation_rationale": {},
        }
        explanation = explainer.explain(profile, adaptive_plan)

        assert explanation.previous_value == 3
        assert explanation.new_value == 4
        factors = [r.factor for r in explanation.reasons]
        assert "previous_bloom_attainment" in factors

    def test_explains_stable_no_adjustment(self):
        """Bloom stays the same when everything is normal."""
        explainer = BloomExplainer()
        profile = {
            "cognitive_load_trend": "stable",
            "engagement_pattern": "consistent",
            "pacing": "moderate",
        }
        adaptive_plan = {
            "bloom_target": 3,
            "original_bloom_target": 3,
            "adaptation_rationale": {},
        }
        explanation = explainer.explain(profile, adaptive_plan)

        assert explanation.previous_value == 3
        assert explanation.new_value == 3
        factors = [r.factor for r in explanation.reasons]
        assert "no_adjustment_needed" in factors


# =============================================================================
# CognitiveLoadAnalysis
# =============================================================================


class TestCognitiveLoadAnalysis:
    def test_detects_overload_with_high_signals(self):
        """High average load → overload detected."""
        analyser = CognitiveLoadAnalysis()
        profile = {
            "cognitive_load_trend": "increasing",
            "cognitive_load_signals": [0.6, 0.75, 0.88],
            "common_misconceptions": [{"m": 1}, {"m": 2}],
            "pacing": "moderate",
        }
        explanation = analyser.analyse(profile, {})

        assert explanation.dimension == "cognitive_load"
        assert "overload" in str(explanation.new_value).lower()
        assert explanation.confidence > 0.6

        factors = [r.factor for r in explanation.reasons]
        assert "average_cognitive_load" in factors
        assert "load_trajectory" in factors

    def test_normal_load_no_overload(self):
        """Low signals → within_range."""
        analyser = CognitiveLoadAnalysis()
        profile = {
            "cognitive_load_trend": "stable",
            "cognitive_load_signals": [0.2, 0.25, 0.3],
            "pacing": "moderate",
        }
        explanation = analyser.analyse(profile, {})

        assert "within_range" in str(explanation.new_value).lower()

    def test_overload_with_pacing_mismatch(self):
        """Fast pacing + overload → pacing_mismatch factor."""
        analyser = CognitiveLoadAnalysis()
        profile = {
            "cognitive_load_trend": "increasing",
            "cognitive_load_signals": [0.8],
            "pacing": "fast",
        }
        explanation = analyser.analyse(profile, {})

        factors = [r.factor for r in explanation.reasons]
        assert "pacing_mismatch" in factors


# =============================================================================
# PersonalizationTrace
# =============================================================================


class TestPersonalizationTrace:
    def test_explains_prompt_for_visual_gaming(self):
        """Visual + gaming → prompt explanation includes both factors."""
        tracer = PersonalizationTrace()
        profile = {
            "learning_style": "visual",
            "preferred_analogies": ["gaming"],
            "successful_example_types": ["diagram", "infographic"],
        }
        prompt_plan = {
            "adaptation_info": {
                "learning_style": "visual",
                "analogy_domain": "gaming",
                "phase_labels": ["Tutorial", "Nivel 1", "Nivel 2"],
            }
        }
        explanation = tracer.explain_prompt_adaptation(profile, prompt_plan)

        assert explanation.dimension == "prompt"
        factors = [r.factor for r in explanation.reasons]
        assert "learning_style_preference" in factors
        assert "analogy_domain_preference" in factors
        assert "prior_successful_examples" in factors
        assert explanation.confidence > 0.5

    def test_explains_modality_from_history(self):
        """Known modality preference → modality explanation."""
        tracer = PersonalizationTrace()
        profile = {"preferred_modality": "image"}
        explanation = tracer.explain_modality_adaptation(profile)

        assert explanation.dimension == "modality"
        assert explanation.new_value == "image"
        factors = [r.factor for r in explanation.reasons]
        assert "historical_modality_success" in factors

    def test_explains_pacing_with_cognitive_load(self):
        """Increasing load → pacing explanation suggests slower pace."""
        tracer = PersonalizationTrace()
        profile = {
            "pacing": "moderate",
            "cognitive_load_trend": "increasing",
        }
        adaptive_plan = {"adaptation_rationale": {}}
        explanation = tracer.explain_pacing_adaptation(profile, adaptive_plan)

        assert explanation.dimension == "pacing"
        factors = [r.factor for r in explanation.reasons]
        assert "cognitive_load_mitigation" in factors

    def test_explains_scaffolding_with_extra_break(self):
        """Cognitive load break → scaffolding explanation."""
        tracer = PersonalizationTrace()
        profile = {"cognitive_load_trend": "increasing"}
        adaptive_plan = {
            "scaffolding": [
                "tutorial interactivo",
                "pausa de reflexion y consolidacion",
                "reto principal",
            ]
        }
        explanation = tracer.explain_scaffolding_adaptation(profile, adaptive_plan)

        assert explanation.dimension == "scaffolding"
        factors = [r.factor for r in explanation.reasons]
        assert "cognitive_load_break" in factors

    def test_explains_scaffolding_with_gaming_terms(self):
        """Gaming analogies → scaffolding aligned."""
        tracer = PersonalizationTrace()
        profile = {
            "preferred_analogies": ["gaming"],
            "cognitive_load_trend": "stable",
            "pacing": "moderate",
        }
        adaptive_plan = {
            "scaffolding": ["tutorial interactivo guiado paso a paso", "mision secundaria"]
        }
        explanation = tracer.explain_scaffolding_adaptation(profile, adaptive_plan)

        factors = [r.factor for r in explanation.reasons]
        assert "analogy_aligned_scaffolding" in factors

    def test_trace_all_returns_four_explanations(self):
        """trace_all returns prompt + modality + pacing + scaffolding."""
        tracer = PersonalizationTrace()
        profile = {"learning_style": "visual", "preferred_analogies": ["gaming"]}
        prompt_plan = {"adaptation_info": {}}
        adaptive_plan = {"adaptation_rationale": {}, "scaffolding": []}
        explanations = tracer.trace_all(profile, prompt_plan, adaptive_plan)

        assert len(explanations) == 4
        dims = [e.dimension for e in explanations]
        assert "prompt" in dims
        assert "modality" in dims
        assert "pacing" in dims
        assert "scaffolding" in dims


# =============================================================================
# AdaptationDecisionGraph
# =============================================================================


class TestAdaptationDecisionGraph:
    def test_builds_graph_with_nodes_and_edges(self):
        """Decision graph contains nodes + edges from explanations."""
        from app.explainability.models import Explanation, Reason

        explanations = [
            Explanation(
                dimension="bloom",
                previous_value=4,
                new_value=3,
                reasons=[
                    Reason(factor="cognitive_load_score", value=0.82, contribution=0.5, evidence="High load"),
                    Reason(factor="misconception_persistence", value=3, contribution=0.3, evidence="Many misconceptions"),
                ],
            )
        ]
        builder = AdaptationDecisionGraph()
        graph = builder.build(explanations)

        assert "nodes" in graph
        assert "edges" in graph
        assert len(graph["nodes"]) >= 2  # at least 1 signal + 1 decision
        assert len(graph["edges"]) >= 1
        assert graph["nodes"][0]["type"] == "decision"
        assert graph["nodes"][1]["type"] == "signal"


# =============================================================================
# AdaptiveReasoning (central orchestrator)
# =============================================================================


class TestAdaptiveReasoning:
    def test_orchestrates_all_explainers(self):
        """AdaptiveReasoning.explain returns all 6 dimensions."""
        engine = AdaptiveReasoning()
        profile = {
            "learning_style": "visual",
            "preferred_analogies": ["gaming"],
            "cognitive_load_trend": "increasing",
            "cognitive_load_signals": [0.8],
            "engagement_pattern": "consistent",
            "pacing": "moderate",
        }
        prompt_plan = {"adaptation_info": {"analogy_domain": "gaming", "phase_labels": []}}
        adaptive_plan = {
            "bloom_target": 3,
            "original_bloom_target": 4,
            "adaptation_rationale": {},
            "scaffolding": ["pausa de reflexion"],
        }

        result = engine.explain(
            student_id="stu-1",
            week_number=2,
            profile=profile,
            prompt_plan=prompt_plan,
            adaptive_plan=adaptive_plan,
        )

        assert result.student_id == "stu-1"
        assert result.week_number == 2
        assert len(result.explanations) >= 5

        dims = [e.dimension for e in result.explanations]
        assert "bloom" in dims
        assert "cognitive_load" in dims
        assert "prompt" in dims
        assert "modality" in dims
        assert "pacing" in dims
        assert "scaffolding" in dims

        # Decision graph should have content
        assert "nodes" in result.decision_graph
        assert "edges" in result.decision_graph
        assert len(result.decision_graph["nodes"]) > 0

    def test_explain_from_plan_works_with_orm_like_object(self):
        """explain_from_plan extracts prompt_plan/adaptive_plan from ORM-like object."""
        engine = AdaptiveReasoning()
        plan = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {"analogy_domain": "music", "phase_labels": ["Compas 1"]}},
            "adaptive_plan": {"bloom_target": 3, "original_bloom_target": 4, "scaffolding": []},
        })()

        result = engine.explain_from_plan(
            student_id="stu-1",
            week_number=1,
            profile={"learning_style": "auditory", "cognitive_load_trend": "stable"},
            plan=plan,
        )

        assert len(result.explanations) >= 5
        assert result.student_id == "stu-1"

    def test_metrics_passed_through(self):
        """Metrics dict is included in result."""
        engine = AdaptiveReasoning()
        profile = {"cognitive_load_trend": "stable"}
        prompt_plan = {"adaptation_info": {}}
        adaptive_plan = {"bloom_target": 3, "original_bloom_target": 3, "scaffolding": []}

        result = engine.explain(
            student_id="stu-1",
            week_number=1,
            profile=profile,
            prompt_plan=prompt_plan,
            adaptive_plan=adaptive_plan,
            metrics={"adaptation_consistency": 0.85},
        )

        assert result.metrics.get("adaptation_consistency") == 0.85


# =============================================================================
# REST explain endpoint
# =============================================================================


def test_explain_endpoint_no_plan_returns_gracefully(client, docente_token, db):
    """GET /api/swarm/explain/{student_id} with no weekly plans → still returns explanation."""
    resp = client.get(
        "/api/swarm/explain/stu-no-plans?week_number=1",
        headers={"Authorization": f"Bearer {docente_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["student_id"] == "stu-no-plans"
    assert "explanations" in data
    assert "decision_graph" in data
