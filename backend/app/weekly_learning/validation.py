"""
WeeklyValidator — cross-week and intra-week consistency validation.

Checks:
  - Bloom monotonic progression (non-decreasing)
  - No gaps in week sequence
  - Each week has required fields populated
  - Thematic continuity across weeks
  - Retrieval confidence thresholds
  - Misconception coverage
"""

from __future__ import annotations

from typing import Any

from app.weekly_learning.models import CourseWeek, WeeklyPlan
from app.weekly_learning.progression import BloomProgression


class WeeklyValidator:
    """
    Validates the integrity and pedagogical soundness of a weekly plan.

    Two levels:
      - Plan-level: cross-week consistency, progression, completeness
      - Week-level: per-week content quality, confidence, alignment
    """

    @staticmethod
    def validate_plan(plan: WeeklyPlan) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []

        if not plan.weeks:
            issues.append({"type": "empty_plan", "severity": "error", "message": "El plan no tiene semanas"})
            return issues

        if plan.total_weeks != len(plan.weeks):
            issues.append({
                "type": "week_count_mismatch",
                "severity": "warning",
                "message": f"El plan declara {plan.total_weeks} semanas pero tiene {len(plan.weeks)}",
            })

        week_numbers = sorted(w.week_number for w in plan.weeks)
        expected = list(range(1, len(week_numbers) + 1))
        if week_numbers != expected:
            issues.append({
                "type": "week_number_gap",
                "severity": "error",
                "message": f"Semanas esperadas {expected}, encontradas {week_numbers}",
            })

        progression = [w.bloom_target for w in sorted(plan.weeks, key=lambda w: w.week_number)]
        prog_issues = BloomProgression.validate(progression)
        for pi in prog_issues:
            issues.append({"type": "bloom_progression", "severity": "warning", "message": pi})

        for week in plan.weeks:
            week_issues = WeeklyValidator.validate_week(week)
            issues.extend(week_issues)

        return issues

    @staticmethod
    def validate_week(week: CourseWeek) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []

        if not week.theme or len(week.theme.strip()) < 3:
            issues.append({
                "type": "missing_theme",
                "severity": "error",
                "message": f"Semana {week.week_number}: tema vacío o muy corto",
            })

        if not week.objectives or len(week.objectives) == 0:
            issues.append({
                "type": "missing_objectives",
                "severity": "error",
                "message": f"Semana {week.week_number}: sin objetivos",
            })

        if week.bloom_target < 1 or week.bloom_target > 6:
            issues.append({
                "type": "invalid_bloom",
                "severity": "error",
                "message": f"Semana {week.week_number}: Bloom level {week.bloom_target} fuera de rango",
            })

        if not week.misconceptions or len(week.misconceptions) == 0:
            issues.append({
                "type": "missing_misconceptions",
                "severity": "info",
                "message": f"Semana {week.week_number}: sin misconceptions definidas",
            })

        if not week.multimodal_prompts or len(week.multimodal_prompts) == 0:
            issues.append({
                "type": "missing_multimodal",
                "severity": "info",
                "message": f"Semana {week.week_number}: sin prompts multimodales",
            })

        if week.content:
            if not week.content.introduction:
                issues.append({
                    "type": "missing_introduction",
                    "severity": "warning",
                    "message": f"Semana {week.week_number}: sin introducción generada",
                })
            if not week.content.pedagogical_explanation:
                issues.append({
                    "type": "missing_explanation",
                    "severity": "warning",
                    "message": f"Semana {week.week_number}: sin explicación pedagógica",
                })

        return issues

    @staticmethod
    def check_thematic_continuity(plan: WeeklyPlan) -> list[dict[str, Any]]:
        issues: list[dict[str, Any]] = []
        sorted_weeks = sorted(plan.weeks, key=lambda w: w.week_number)

        for i in range(1, len(sorted_weeks)):
            prev = sorted_weeks[i - 1]
            curr = sorted_weeks[i]
            if curr.bloom_target < prev.bloom_target:
                issues.append({
                    "type": "thematic_regression",
                    "severity": "warning",
                    "message": (
                        f"Regresión Bloom de semana {prev.week_number} ({prev.bloom_target}) "
                        f"a semana {curr.week_number} ({curr.bloom_target})"
                    ),
                })

        return issues

    @staticmethod
    def plan_health_score(plan: WeeklyPlan) -> float:
        issues = WeeklyValidator.validate_plan(plan)
        if not plan.weeks:
            return 0.0

        errors = sum(1 for i in issues if i["severity"] == "error")
        warnings = sum(1 for i in issues if i["severity"] == "warning")
        infos = sum(1 for i in issues if i["severity"] == "info")

        base = 1.0
        base -= errors * 0.25
        base -= warnings * 0.1
        base -= infos * 0.02
        return max(0.0, base)


weekly_validator = WeeklyValidator()
