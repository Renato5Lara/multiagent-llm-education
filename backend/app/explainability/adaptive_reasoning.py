"""Central adaptive reasoning engine — orchestrates all sub-explainers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.explainability.models import AdaptationExplanation, Explanation
from app.explainability.bloom_explainer import BloomExplainer
from app.explainability.cognitive_load_analysis import CognitiveLoadAnalysis
from app.explainability.personalization_trace import PersonalizationTrace
from app.explainability.adaptation_decision_graph import AdaptationDecisionGraph


class AdaptiveReasoning:
    """Central explainability orchestrator.

    Takes student profile + current plan (+ optional previous plan) and
    produces a full ``AdaptationExplanation`` with per-dimension explanations,
    a decision graph, metrics, and SSE-traceable IDs.
    """

    def __init__(self) -> None:
        self.bloom = BloomExplainer()
        self.cognitive = CognitiveLoadAnalysis()
        self.trace = PersonalizationTrace()
        self.graph = AdaptationDecisionGraph()

    def explain(
        self,
        student_id: str,
        week_number: int,
        profile: dict[str, Any],
        prompt_plan: dict[str, Any],
        adaptive_plan: dict[str, Any],
        previous_adaptive_plan: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> AdaptationExplanation:
        explanations: list[Explanation] = [
            self.bloom.explain(profile, adaptive_plan, previous_adaptive_plan),
            self.cognitive.analyse(profile, adaptive_plan),
        ]
        explanations.extend(
            self.trace.trace_all(profile, prompt_plan, adaptive_plan)
        )

        decision_graph = self.graph.build(explanations)

        return AdaptationExplanation(
            student_id=student_id,
            week_number=week_number,
            explanations=explanations,
            decision_graph=decision_graph,
            metrics=metrics or {},
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def explain_from_plan(
        self,
        student_id: str,
        week_number: int,
        profile: dict[str, Any],
        plan: Any,
        previous_plan: Any | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> AdaptationExplanation:
        prompt_plan = getattr(plan, "prompt_plan", {}) or {}
        adaptive_plan = getattr(plan, "adaptive_plan", {}) or {}
        prev_adaptive = getattr(previous_plan, "adaptive_plan", None) if previous_plan else None
        return self.explain(
            student_id=student_id,
            week_number=week_number,
            profile=profile,
            prompt_plan=prompt_plan,
            adaptive_plan=adaptive_plan,
            previous_adaptive_plan=prev_adaptive,
            metrics=metrics,
        )


adaptive_reasoning = AdaptiveReasoning()
