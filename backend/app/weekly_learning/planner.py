"""
WeeklyPlanner — generates a full weekly plan for a course.

Takes teacher input (thematic line, objectives, pedagogical intention)
and produces a complete WeeklyPlan with CourseWeek instances.

Flow:
  1. Select template based on total_weeks
  2. Fill thematic content for each week
  3. Generate week-specific objectives aligned to Bloom level
  4. Generate misconceptions, applications, modality, prompts
  5. Persist to DB
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.user import User
from app.weekly_learning.models import CourseWeek, WeeklyPlan
from app.weekly_learning.weekly_structure import weekly_structure_factory
from app.weekly_learning.progression import BloomProgression

logger = logging.getLogger(__name__)


class WeeklyPlanner:
    """
    Generates the weekly structure for a course.

    The teacher provides:
      - thematic_line: "Arreglos en programación"
      - objectives: ["Comprender la sintaxis", ...]
      - pedagogical_intention: descripción general
      - total_weeks: 5, 8, or 16

    The planner returns a WeeklyPlan with CourseWeek rows, each having:
      - theme, bloom_target, objectives, misconceptions, modality, etc.
    """

    def create_plan(
        self,
        db: Session,
        course: Course,
        teacher: User,
        thematic_line: str,
        objectives: list[str],
        pedagogical_intention: str,
        total_weeks: int = 5,
    ) -> WeeklyPlan:
        template = weekly_structure_factory.get_template(total_weeks)
        progression = [w.bloom_level for w in template.weeks]

        plan = WeeklyPlan(
            course_id=course.id,
            teacher_id=teacher.id,
            total_weeks=total_weeks,
            thematic_line=thematic_line,
            pedagogical_intention=pedagogical_intention,
            bloom_progression=progression,
            week_themes=[self._build_week_theme(template.weeks[i], thematic_line, i + 1) for i in range(total_weeks)],
            status="active",
        )
        db.add(plan)
        db.flush()

        for i, wt in enumerate(template.weeks):
            week_theme = plan.week_themes[i]
            week_obj = self._build_week(
                plan_id=plan.id,
                week_number=wt.week,
                theme=week_theme,
                bloom_target=wt.bloom_level,
                objectives=objectives,
                pedagogical_intention=pedagogical_intention,
            )
            db.add(week_obj)

        db.commit()
        db.refresh(plan)
        return plan

    def _build_week_theme(self, wt: Any, thematic_line: str, week_num: int) -> str:
        return f"{thematic_line} — {wt.theme_suffix} (Semana {week_num})"

    def _build_week(
        self,
        plan_id: str,
        week_number: int,
        theme: str,
        bloom_target: int,
        objectives: list[str],
        pedagogical_intention: str,
    ) -> CourseWeek:
        bloom_label = BloomProgression.get_label(bloom_target)
        verbs = BloomProgression.get_verbs(bloom_target)

        week_objectives = [
            f"{verb.capitalize()} {theme.lower().split(' — ')[0].lower()}: {obj}"
            for verb in verbs[:2]
            for obj in (objectives or ["conceptos fundamentales"])[:2]
        ][:4]

        return CourseWeek(
            plan_id=plan_id,
            week_number=week_number,
            theme=theme,
            bloom_target=bloom_target,
            objectives=week_objectives or [f"Comprender los fundamentos de {theme}"],
            misconceptions=self._generate_misconceptions(theme, bloom_target),
            real_applications=self._generate_applications(theme, week_number),
            recommended_modality=self._select_modality(week_number, bloom_target),
            multimodal_prompts=self._generate_prompts(theme, bloom_target, week_number),
            evaluation_criteria=self._generate_evaluation_criteria(bloom_target),
            orchestration_status="pending",
        )

    def _generate_misconceptions(self, theme: str, bloom_target: int) -> list[dict[str, str]]:
        return [
            {"misconception": f"Error común sobre {theme}", "correction": f"La forma correcta es...", "severity": "medium"},
            {"misconception": "Confundir conceptos fundamentales", "correction": "Es importante diferenciar...", "severity": "high"},
        ]

    def _generate_applications(self, theme: str, week_number: int) -> list[str]:
        return [
            f"Aplicación práctica de {theme} en el mundo real",
            f"Caso de estudio: cómo se usa {theme} en la industria",
        ]

    def _select_modality(self, week_number: int, bloom_target: int) -> str:
        if bloom_target <= 2:
            return "reading"
        elif bloom_target <= 4:
            return "visual"
        return "kinesthetic"

    def _generate_prompts(self, theme: str, bloom_target: int, week_number: int) -> list[dict[str, Any]]:
        return [
            {"modality": "image", "prompt": f"Diagrama conceptual de {theme}", "enabled": True},
            {"modality": "video", "prompt": f"Video explicativo de {theme}", "enabled": bloom_target >= 2},
            {"modality": "audio", "prompt": f"Podcast educativo sobre {theme}", "enabled": bloom_target >= 3},
        ]

    def _generate_evaluation_criteria(self, bloom_target: int) -> list[str]:
        verbs = BloomProgression.get_verbs(bloom_target)
        return [
            f"{verb.capitalize()} los conceptos clave del tema"
            for verb in verbs[:3]
        ]

    def get_plan(self, db: Session, course_id: str) -> WeeklyPlan | None:
        return (
            db.query(WeeklyPlan)
            .filter(WeeklyPlan.course_id == course_id)
            .order_by(WeeklyPlan.created_at.desc())
            .first()
        )

    def list_plans(self, db: Session, teacher_id: str) -> list[WeeklyPlan]:
        return (
            db.query(WeeklyPlan)
            .filter(WeeklyPlan.teacher_id == teacher_id)
            .order_by(WeeklyPlan.created_at.desc())
            .all()
        )


weekly_planner = WeeklyPlanner()
