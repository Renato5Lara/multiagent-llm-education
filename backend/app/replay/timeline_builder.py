"""Build longitudinal timelines from replay steps."""

from __future__ import annotations

from typing import Any


class TimelineBuilder:
    """Aggregates per-week replay data into longitudinal timelines.

    Each timeline is a list of values indexed by week, making it easy
    to render evolution charts (Bloom over weeks, cognitive load trend, etc.).
    """

    def build(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        bloom_levels: list[int] = []
        bloom_changes: list[str] = []
        confidence_scores: list[float] = []
        scaffolding_counts: list[int] = []
        misconception_counts: list[int] = []
        cognitive_load_signals: list[float] = []
        memory_records: list[int] = []
        adaptation_strength: list[float] = []

        for step in steps:
            ad = step.get("adaptation", {})
            bloom = ad.get("bloom", {})
            bloom_levels.append(bloom.get("current", 3))
            bloom_changes.append(bloom.get("direction", "stable"))
            confidence_scores.append(ad.get("consensus", {}).get("confidence", 0.0))

            sc = ad.get("scaffolding", {})
            scaffolding_counts.append(sc.get("current_count", 0))

            reasoning = step.get("reasoning", {})
            explanations = reasoning.get("explanations", [])

            cog_exp = next((e for e in explanations if e.get("dimension") == "cognitive_load"), None)
            if cog_exp:
                load_reason = next((r for r in cog_exp.get("reasons", []) if r.get("factor") == "average_cognitive_load"), None)
                cognitive_load_signals.append(float(load_reason.get("value", 0.0)) if load_reason else 0.0)
            else:
                cognitive_load_signals.append(0.0)

            mem = step.get("memory", {})
            memory_records.append(mem.get("total_records", 0))

            profile = step.get("profile", {})
            misconc = profile.get("common_misconceptions", [])
            misconception_counts.append(len(misconc) if misconc else 0)

            metrics = step.get("metrics", {})
            adaptation_strength.append(float(metrics.get("personalization_strength", 0.0)))

        return {
            "bloom_levels": bloom_levels,
            "bloom_changes": bloom_changes,
            "confidence_scores": confidence_scores,
            "scaffolding_counts": scaffolding_counts,
            "misconception_counts": misconception_counts,
            "cognitive_load_signals": cognitive_load_signals,
            "memory_records": memory_records,
            "adaptation_strength": adaptation_strength,
        }

    def compute_metrics(self, timeline: dict[str, Any]) -> dict[str, Any]:
        bloom = timeline.get("bloom_levels", [])
        load = timeline.get("cognitive_load_signals", [])
        mis = timeline.get("misconception_counts", [])

        bloom_recovery = 0
        if len(bloom) >= 2:
            initial_bloom = bloom[0]
            for i in range(1, len(bloom)):
                if bloom[i] > initial_bloom:
                    bloom_recovery = bloom[i] - initial_bloom

        miscon_reduction = 0
        if len(mis) >= 2 and mis[0] > 0:
            miscon_reduction = mis[0] - mis[-1]

        load_trend = "stable"
        if len(load) >= 2:
            if load[-1] > load[0]:
                load_trend = "increasing"
            elif load[-1] < load[0]:
                load_trend = "decreasing"

        return {
            "bloom_recovery": bloom_recovery,
            "misconception_reduction": max(0, miscon_reduction),
            "cognitive_load_trend": load_trend,
            "total_weeks": len(bloom),
            "adaptation_stability": sum(1 for c in timeline.get("bloom_changes", []) if c == "stable") / max(len(bloom), 1),
            "confidence_trend": "up" if len(timeline.get("confidence_scores", [])) >= 2 and timeline["confidence_scores"][-1] > timeline["confidence_scores"][0] else "stable" if len(timeline.get("confidence_scores", [])) >= 2 else "unknown",
        }


timeline_builder = TimelineBuilder()
