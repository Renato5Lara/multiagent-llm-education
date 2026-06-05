"""Explain Bloom-level adaptation decisions."""

from __future__ import annotations

from typing import Any

from app.explainability.models import Explanation, Reason


class BloomExplainer:
    """Explains why Bloom target was kept, raised, or lowered."""

    def explain(
        self,
        profile: dict[str, Any],
        adaptive_plan: dict[str, Any],
        previous_adaptive_plan: dict[str, Any] | None = None,
    ) -> Explanation:
        reasons: list[Reason] = []
        original = adaptive_plan.get("original_bloom_target", adaptive_plan.get("bloom_target", 3))
        adjusted = adaptive_plan.get("bloom_target", original)
        rationale = adaptive_plan.get("adaptation_rationale", {})

        if adjusted < original:
            cog = profile.get("cognitive_load_trend", "stable")
            load_records = profile.get("cognitive_load_signals", [])
            avg_load = sum(load_records) / len(load_records) if load_records else 0.0

            reasons.append(Reason(
                factor="cognitive_load_score",
                value=round(avg_load, 2) if load_records else cog,
                contribution=0.5,
                evidence=(
                    f"Cognitive load trend '{cog}' with average signal {avg_load:.2f} "
                    f"indicates the student is overwhelmed at the current level."
                ),
            ))

            misconc = profile.get("common_misconceptions", [])
            if len(misconc) >= 2:
                reasons.append(Reason(
                    factor="misconception_persistence",
                    value=f"{len(misconc)} persistent misconceptions",
                    contribution=0.25,
                    evidence=f"{len(misconc)} recurring misconceptions suggest foundational gaps at Bloom {original}.",
                ))

            eng = profile.get("engagement_pattern", "consistent")
            if eng == "dropping":
                reasons.append(Reason(
                    factor="engagement_decay",
                    value=eng,
                    contribution=0.15,
                    evidence="Engagement pattern 'dropping' signals the student is losing motivation at the current difficulty.",
                ))

            pacing = profile.get("pacing", "moderate")
            if pacing == "slow":
                reasons.append(Reason(
                    factor="historical_pacing",
                    value=pacing,
                    contribution=0.1,
                    evidence=f"Historical pacing '{pacing}' indicates the student needs more time per concept.",
                ))

        elif adjusted > original:
            bp = profile.get("bloom_level_reached", 0) or 0
            reasons.append(Reason(
                factor="previous_bloom_attainment",
                value=bp,
                contribution=0.6,
                evidence=f"Student reached Bloom level {bp} in previous weeks, ready for advancement.",
            ))
            if profile.get("engagement_pattern") == "consistent":
                reasons.append(Reason(
                    factor="consistent_engagement",
                    value="consistent",
                    contribution=0.4,
                    evidence="Consistent engagement supports increasing difficulty.",
                ))

        else:
            reasons.append(Reason(
                factor="no_adjustment_needed",
                value="stable",
                contribution=1.0,
                evidence=(
                    f"Bloom target {original} is appropriate: "
                    f"cognitive load ({profile.get('cognitive_load_trend', 'stable')}), "
                    f"engagement ({profile.get('engagement_pattern', 'consistent')}), "
                    f"and pacing ({profile.get('pacing', 'moderate')}) are all within normal range."
                ),
            ))

        conf = sum(r.contribution * 0.9 for r in reasons) if reasons else 0.0

        return Explanation(
            dimension="bloom",
            previous_value=original,
            new_value=adjusted,
            reasons=reasons,
            confidence=min(conf, 1.0),
            trace_id=f"bloom:{rationale.get('learning_style', 'unknown')}:{original}->{adjusted}",
        )
