"""Trace and explain personalization decisions across all dimensions."""

from __future__ import annotations

from typing import Any

from app.explainability.models import Explanation, Reason


DIMENSION_EXTRACTORS: dict[str, tuple[str, str]] = {
    "prompt": ("learning_style", "preferred_analogies"),
    "modality": ("preferred_modality",),
    "pacing": ("pacing",),
    "scaffolding": ("cognitive_load_trend", "pacing", "preferred_analogies"),
}


class PersonalizationTrace:
    """Explains why the system personalized prompts, modality, pacing, etc."""

    def explain_prompt_adaptation(self, profile: dict[str, Any], prompt_plan: dict[str, Any]) -> Explanation:
        reasons: list[Reason] = []
        ls = profile.get("learning_style", "")
        analogies = profile.get("preferred_analogies", []) or []
        adaptation_info = prompt_plan.get("adaptation_info", {})

        if ls:
            reasons.append(Reason(
                factor="learning_style_preference",
                value=ls,
                contribution=0.4,
                evidence=(
                    f"Student prefers {ls} learning. "
                    f"{'Prompt enriched with visual context (diagrams, infographics).' if ls == 'visual' else ''}"
                    f"{'Prompt adapted for auditory delivery.' if ls == 'auditory' else ''}"
                    f"{'Prompt uses detailed textual references.' if ls == 'reading' else ''}"
                    f"{'Prompt emphasizes hands-on activities.' if ls == 'kinesthetic' else ''}"
                ),
            ))

        if analogies:
            domain = analogies[0]
            reasons.append(Reason(
                factor="analogy_domain_preference",
                value=domain,
                contribution=0.3,
                evidence=(
                    f"Student responds well to {domain} analogies. "
                    f"Prompt structure uses '{domain}' metaphors and phase labels "
                    f"({', '.join(adaptation_info.get('phase_labels', []))})."
                ),
            ))

        if profile.get("successful_example_types"):
            ex_types = profile["successful_example_types"]
            reasons.append(Reason(
                factor="prior_successful_examples",
                value=ex_types,
                contribution=0.2,
                evidence=f"Previous successful example types ({', '.join(ex_types)}) informed prompt design.",
            ))

        if profile.get("narrative_persona"):
            reasons.append(Reason(
                factor="narrative_continuity",
                value=profile["narrative_persona"][:60],
                contribution=0.1,
                evidence="Narrative persona from previous weeks was continued for consistency.",
            ))

        conf = min(sum(r.contribution for r in reasons), 1.0)
        return Explanation(
            dimension="prompt",
            new_value=f"adapted_for_{ls or 'default'}_{analogies[0] if analogies else 'none'}",
            reasons=reasons,
            confidence=conf,
            trace_id=f"prompt:{ls}:{analogies[0] if analogies else 'none'}",
        )

    def explain_modality_adaptation(self, profile: dict[str, Any]) -> Explanation:
        reasons: list[Reason] = []
        mod = profile.get("preferred_modality", "")

        if mod:
            reasons.append(Reason(
                factor="historical_modality_success",
                value=mod,
                contribution=0.6,
                evidence=f"Student has historically engaged best with '{mod}' modality.",
            ))

        ls = profile.get("learning_style", "")
        modality_map = {"visual": "image", "auditory": "audio", "reading": "text", "kinesthetic": "interactive"}
        if ls and ls in modality_map and not mod:
            mod = modality_map[ls]
            reasons.append(Reason(
                factor="learning_style_alignment",
                value=ls,
                contribution=0.4,
                evidence=f"Modality '{mod}' selected based on {ls} learning style alignment.",
            ))

        if not reasons:
            reasons.append(Reason(
                factor="default_modality",
                value="visual",
                contribution=1.0,
                evidence="No historical preference found; using default visual modality.",
            ))

        conf = min(sum(r.contribution for r in reasons), 1.0)
        return Explanation(
            dimension="modality",
            new_value=mod or "visual",
            reasons=reasons,
            confidence=conf,
            trace_id=f"modality:{mod or 'visual'}",
        )

    def explain_pacing_adaptation(self, profile: dict[str, Any], adaptive_plan: dict[str, Any]) -> Explanation:
        reasons: list[Reason] = []
        pacing = profile.get("pacing", "moderate")
        rationale = adaptive_plan.get("adaptation_rationale", {})
        cog = profile.get("cognitive_load_trend", "stable")

        if cog == "increasing" and pacing != "slow":
            reasons.append(Reason(
                factor="cognitive_load_mitigation",
                value=cog,
                contribution=0.5,
                evidence="Increasing cognitive load suggests a slower pace is needed for comprehension.",
            ))

        if profile.get("engagement_pattern") == "dropping":
            reasons.append(Reason(
                factor="engagement_recovery",
                value="dropping",
                contribution=0.3,
                evidence="Dropping engagement may be addressed by adjusting content delivery pace.",
            ))

        if not reasons:
            reasons.append(Reason(
                factor="pace_maintained",
                value=pacing,
                contribution=1.0,
                evidence=f"Current pace '{pacing}' is appropriate based on cognitive load and engagement signals.",
            ))

        conf = min(sum(r.contribution for r in reasons), 1.0)
        return Explanation(
            dimension="pacing",
            previous_value=pacing,
            new_value=pacing,
            reasons=reasons,
            confidence=conf,
            trace_id=f"pacing:{pacing}:{cog}",
        )

    def explain_scaffolding_adaptation(self, profile: dict[str, Any], adaptive_plan: dict[str, Any]) -> Explanation:
        reasons: list[Reason] = []
        scaffolding = adaptive_plan.get("scaffolding", [])
        cog = profile.get("cognitive_load_trend", "stable")
        analogies = profile.get("preferred_analogies", []) or []
        pacing = profile.get("pacing", "moderate")

        has_extra_break = any("pausa" in s for s in scaffolding)
        if has_extra_break:
            reasons.append(Reason(
                factor="cognitive_load_break",
                value=cog,
                contribution=0.4,
                evidence="Extra consolidation break added to manage cognitive load.",
            ))

        if analogies:
            domain = analogies[0]
            has_domain_label = any(
                domain_term in s for s in scaffolding
                for domain_term in ["tutorial", "mision", "calentamiento", "entrenamiento", "compas", "melodia"]
            )
            if has_domain_label:
                reasons.append(Reason(
                    factor="analogy_aligned_scaffolding",
                    value=domain,
                    contribution=0.3,
                    evidence=f"Scaffolding terms aligned with preferred {domain} analogy domain.",
                ))

        if pacing == "fast":
            has_diagnostic = any("diagnostico" in s or "calentamiento" in s for s in scaffolding)
            if not has_diagnostic:
                reasons.append(Reason(
                    factor="pace_optimization",
                    value="fast",
                    contribution=0.2,
                    evidence="Diagnostic/warm-up steps removed for fast-paced learners.",
                ))

        if not reasons:
            reasons.append(Reason(
                factor="default_scaffolding",
                value="standard",
                contribution=1.0,
                evidence="Standard scaffolding structure used — no adaptation signals detected.",
            ))

        conf = min(sum(r.contribution for r in reasons), 1.0)
        return Explanation(
            dimension="scaffolding",
            new_value=scaffolding,
            reasons=reasons,
            confidence=conf,
            trace_id=f"scaffolding:{len(scaffolding)}_steps",
        )

    def trace_all(self, profile: dict[str, Any], prompt_plan: dict[str, Any], adaptive_plan: dict[str, Any]) -> list[Explanation]:
        return [
            self.explain_prompt_adaptation(profile, prompt_plan),
            self.explain_modality_adaptation(profile),
            self.explain_pacing_adaptation(profile, adaptive_plan),
            self.explain_scaffolding_adaptation(profile, adaptive_plan),
        ]
