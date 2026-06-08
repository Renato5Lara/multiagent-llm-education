"""Main session replay orchestrator — reconstructs full pedagogical evolution."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.memory.shared_memory import SharedMemoryStore, memory_store_from_session
from app.memory.pedagogical_memory import PedagogicalMemoryService
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.replay.adaptation_replay import adaptation_replay
from app.replay.reasoning_replay import reasoning_replay
from app.replay.memory_replay import memory_replay
from app.replay.timeline_builder import timeline_builder
from app.replay.replay_exporter import replay_exporter


class SessionReplay:
    """Reconstructs a complete student pedagogical journey week by week.

    Usage::

        sr = SessionReplay()
        replay = sr.replay(db, student_id="stu-1", course_id="c-1")
        md = replay_exporter.to_markdown(replay)
    """

    def replay(
        self,
        db: Session,
        student_id: str,
        course_id: str,
        memory_store: SharedMemoryStore | None = None,
    ) -> dict[str, Any]:
        store = memory_store or memory_store_from_session(db)
        ped = PedagogicalMemoryService(store)

        plans = (
            db.query(WeeklyPedagogicalPlan)
            .filter(
                WeeklyPedagogicalPlan.teacher_id == student_id,
                WeeklyPedagogicalPlan.course_id == course_id,
            )
            .order_by(WeeklyPedagogicalPlan.week_number.asc())
            .all()
        )

        steps: list[dict[str, Any]] = []
        prev_plan = None

        for plan in plans:
            week_num = plan.week_number
            module_id = f"{course_id}:week{week_num}"

            profile = ped.build_student_profile(student_id=student_id)
            metrics = ped.compute_metrics(student_id=student_id, weeks=week_num)
            mem_snapshot = memory_replay.snapshot(store, student_id, module_id, weeks=week_num)
            ad = adaptation_replay.replay_week(plan, prev_plan)
            reasoning = reasoning_replay.replay_week(
                student_id=student_id,
                week_number=week_num,
                profile=profile,
                plan=plan,
                previous_plan=prev_plan,
                metrics=metrics,
            )

            steps.append({
                "week_number": week_num,
                "profile": dict(profile),
                "metrics": dict(metrics),
                "adaptation": ad,
                "reasoning": reasoning,
                "memory": mem_snapshot,
            })
            prev_plan = plan

        timeline = timeline_builder.build(steps)
        longitudinal_metrics = timeline_builder.compute_metrics(timeline)

        result: dict[str, Any] = {
            "student_id": student_id,
            "course_id": course_id,
            "total_weeks": len(steps),
            "steps": steps,
            "timeline": timeline,
            "metrics": longitudinal_metrics,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        return result

    def replay_with_exports(
        self,
        db: Session,
        student_id: str,
        course_id: str,
    ) -> dict[str, Any]:
        replay = self.replay(db, student_id, course_id)
        replay["exports"] = replay_exporter.export_all(replay)
        return replay


session_replay = SessionReplay()
