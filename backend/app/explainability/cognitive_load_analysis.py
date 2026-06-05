"""Analyse and explain cognitive load signals."""

from __future__ import annotations

from typing import Any

from app.explainability.models import Explanation, Reason


class CognitiveLoadAnalysis:
    """Analyses cognitive load signals and produces explanations.

    Examines historical load records, misconception density, source complexity,
    and pacing to determine whether overload exists and why.
    """

    SEVERITY_THRESHOLDS = {"low": 0.3, "moderate": 0.55, "high": 0.75}

    def analyse(self, profile: dict[str, Any], adaptive_plan: dict[str, Any]) -> Explanation:
        reasons: list[Reason] = []

        trend = profile.get("cognitive_load_trend", "stable")
        load_records = profile.get("cognitive_load_signals", [])
        avg_load = sum(load_records) / len(load_records) if load_records else 0.0

        severity = "low"
        for level, threshold in sorted(self.SEVERITY_THRESHOLDS.items(), key=lambda x: x[1]):
            if avg_load >= threshold:
                severity = level

        overload_detected = trend == "increasing" or avg_load > 0.55

        if avg_load > 0:
            reasons.append(Reason(
                factor="average_cognitive_load",
                value=round(avg_load, 2),
                contribution=0.4,
                evidence=(
                    f"Average cognitive load signal is {avg_load:.2f} "
                    f"(severity: {severity}). "
                    f"{'Student is showing signs of cognitive overload.' if avg_load > 0.55 else 'Load is within manageable range.'}"
                ),
            ))

        if load_records and len(load_records) >= 2:
            trend_direction = "increasing" if load_records[-1] > load_records[0] else "decreasing" if load_records[-1] < load_records[0] else "stable"
            reasons.append(Reason(
                factor="load_trajectory",
                value=trend_direction,
                contribution=0.25,
                evidence=(
                    f"Cognitive load has been {trend_direction} over the last {len(load_records)} observations "
                    f"(from {load_records[0]:.2f} to {load_records[-1]:.2f})."
                ),
            ))

        misconc = profile.get("common_misconceptions", [])
        if len(misconc) >= 2:
            reasons.append(Reason(
                factor="misconception_density",
                value=len(misconc),
                contribution=0.2,
                evidence=f"{len(misconc)} persistent misconceptions increase cognitive overhead during new learning.",
            ))

        pacing = profile.get("pacing", "moderate")
        if pacing == "fast" and overload_detected:
            reasons.append(Reason(
                factor="pacing_mismatch",
                value=pacing,
                contribution=0.15,
                evidence=f"Fast pacing combined with high cognitive load suggests the student needs slower content delivery.",
            ))

        conf = sum(r.contribution * 0.85 for r in reasons) if reasons else 0.0

        return Explanation(
            dimension="cognitive_load",
            previous_value=trend if overload_detected else "normal",
            new_value=f"overload_detected:{severity}" if overload_detected else "within_range",
            reasons=reasons,
            confidence=min(conf + (0.2 if overload_detected else 0.0), 1.0),
            trace_id=f"cognitive_load:{severity}:{trend}",
        )
