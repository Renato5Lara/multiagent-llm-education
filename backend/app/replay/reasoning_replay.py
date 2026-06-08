"""Replay reasoning explanations across weeks."""

from __future__ import annotations

from typing import Any

from app.explainability.adaptive_reasoning import AdaptiveReasoning


class ReasoningReplay:
    """Generates per-week adaptation explanations, replaying the reasoning
    that was (or would have been) produced at each week boundary."""

    def __init__(self) -> None:
        self._reasoning = AdaptiveReasoning()

    def replay_week(
        self,
        student_id: str,
        week_number: int,
        profile: dict[str, Any],
        plan: Any,
        previous_plan: Any | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        explanation = self._reasoning.explain_from_plan(
            student_id=student_id,
            week_number=week_number,
            profile=profile,
            plan=plan,
            previous_plan=previous_plan,
            metrics=metrics,
        )
        result = explanation.to_dict()

        dims = {e["dimension"] for e in result.get("explanations", [])}
        return {
            "week_number": week_number,
            "explanations": result["explanations"],
            "decision_graph": result["decision_graph"],
            "dimensions": sorted(dims),
            "generated_at": result["generated_at"],
        }

    def replay_all(
        self,
        student_id: str,
        profiles: list[dict[str, Any]],
        plans: list[Any],
        all_metrics: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        prev_plan = None
        for i, plan in enumerate(plans):
            profile = profiles[i] if i < len(profiles) else {}
            metrics = all_metrics[i] if all_metrics and i < len(all_metrics) else {}
            week_num = getattr(plan, "week_number", i + 1)
            steps.append(self.replay_week(
                student_id=student_id,
                week_number=week_num,
                profile=profile,
                plan=plan,
                previous_plan=prev_plan,
                metrics=metrics,
            ))
            prev_plan = plan
        return steps


reasoning_replay = ReasoningReplay()
