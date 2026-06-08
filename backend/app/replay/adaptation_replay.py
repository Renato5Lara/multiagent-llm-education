"""Replay adaptation decisions across weeks."""

from __future__ import annotations

from typing import Any


class AdaptationReplay:
    """Reconstructs what adaptation decisions were made each week and why.

    Reads from ``adaptive_plan``, ``prompt_plan``, and ``consensus_result``
    stored in each ``WeeklyPedagogicalPlan`` to produce a per-week summary
    of every adaptation decision.
    """

    def replay_week(
        self,
        plan: Any,
        previous_plan: Any | None = None,
    ) -> dict[str, Any]:
        prompt = getattr(plan, "prompt_plan", {}) or {}
        adaptive = getattr(plan, "adaptive_plan", {}) or {}
        consensus = getattr(plan, "consensus_result", {}) or {}

        prev_adaptive = getattr(previous_plan, "adaptive_plan", None) if previous_plan else None or {}
        prev_prompt = getattr(previous_plan, "prompt_plan", None) if previous_plan else None or {}

        bloom_prev = prev_adaptive.get("bloom_target", adaptive.get("original_bloom_target", adaptive.get("bloom_target", 3)))
        bloom_curr = adaptive.get("bloom_target", bloom_prev)
        bloom_changed = bloom_curr != bloom_prev

        prev_analogies = (prev_prompt.get("adaptation_info") or {}).get("analogy_domain")
        curr_analogies = (prompt.get("adaptation_info") or {}).get("analogy_domain")
        analogy_changed = curr_analogies != prev_analogies

        prev_modality = (prev_prompt.get("adaptation_info") or {}).get("learning_style")
        curr_modality = (prompt.get("adaptation_info") or {}).get("learning_style")

        scaffolding = adaptive.get("scaffolding", [])
        prev_scaffolding = prev_adaptive.get("scaffolding", [])
        scaffolding_changed = scaffolding != prev_scaffolding

        return {
            "bloom": {
                "previous": bloom_prev,
                "current": bloom_curr,
                "changed": bloom_changed,
                "direction": "up" if bloom_changed and bloom_curr > bloom_prev else "down" if bloom_changed and bloom_curr < bloom_prev else "stable",
                "adjusted_reason": adaptive.get("adaptation_rationale", {}).get("bloom_adjusted_reason", "normal"),
            },
            "analogy_domain": {
                "previous": prev_analogies,
                "current": curr_analogies,
                "changed": analogy_changed,
            },
            "learning_style": {
                "previous": prev_modality,
                "current": curr_modality,
            },
            "scaffolding": {
                "previous_count": len(prev_scaffolding),
                "current_count": len(scaffolding),
                "changed": scaffolding_changed,
                "steps": scaffolding,
            },
            "consensus": {
                "decision": consensus.get("decision", ""),
                "confidence": consensus.get("confidence", 0.0),
                "memory_influence": consensus.get("memory_influence", 0.0),
                "profile_influence": consensus.get("profile_influence", 0.0),
            },
            "differentiation": adaptive.get("differentiation", {}),
        }

    def replay_all(
        self,
        plans: list[Any],
    ) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        prev = None
        for plan in plans:
            steps.append(self.replay_week(plan, prev))
            prev = plan
        return steps


adaptation_replay = AdaptationReplay()
