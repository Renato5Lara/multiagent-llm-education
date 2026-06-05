"""
/api/replay endpoints — Longitudinal pedagogical session replay.

Provides REST + SSE access to full student evolution replay:
  - List / load replay sessions
  - Per-student replay (timeline, adaptation, reasoning, memory, export)
  - Real-time SSE stream of replay events for the interactive dashboard
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.memory.shared_memory import memory_store_from_session
from app.memory.pedagogical_memory import PedagogicalMemoryService
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.models.course import Course
from app.models.user import User
from app.replay.session_replay import session_replay
from app.replay.adaptation_replay import adaptation_replay
from app.replay.reasoning_replay import reasoning_replay
from app.replay.memory_replay import memory_replay
from app.replay.timeline_builder import timeline_builder
from app.replay.replay_exporter import replay_exporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/replay", tags=["Replay"])


# ── Helpers ──────────────────────────────────────────────────────────


def _serialize_plan(plan: WeeklyPedagogicalPlan) -> dict[str, Any]:
    return {
        "id": plan.id,
        "course_id": plan.course_id,
        "teacher_id": plan.teacher_id,
        "week_number": plan.week_number,
        "topic": plan.topic,
        "objectives": plan.objectives,
        "bloom_target": plan.bloom_target,
        "pedagogical_style": plan.pedagogical_style,
        "pedagogical_intention": plan.pedagogical_intention,
        "preferred_modality": plan.preferred_modality,
        "orchestration_status": plan.orchestration_status,
        "generated_at": plan.generated_at.isoformat() if plan.generated_at else None,
        "adaptive_plan": plan.adaptive_plan,
        "prompt_plan": plan.prompt_plan,
        "consensus_result": plan.consensus_result,
    }


async def _replay_event_stream(student_id: str, db: Session) -> AsyncIterator[str]:
    """SSE event generator for full student replay."""
    store = memory_store_from_session(db)
    ped = PedagogicalMemoryService(store)

    plans = (
        db.query(WeeklyPedagogicalPlan)
        .filter(WeeklyPedagogicalPlan.teacher_id == student_id)
        .order_by(WeeklyPedagogicalPlan.week_number.asc())
        .all()
    )

    yield f"event: replay:start\ndata: {json.dumps({'student_id': student_id, 'total_weeks': len(plans)})}\n\n"
    await asyncio.sleep(0.05)

    if not plans:
        yield f"event: replay:complete\ndata: {json.dumps({'student_id': student_id, 'weeks_replayed': 0})}\n\n"
        return

    steps: list[dict[str, Any]] = []
    prev_plan = None

    for plan in plans:
        week_num = plan.week_number
        module_id = f"{plan.course_id}:week{week_num}"

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

        step = {
            "week_number": week_num,
            "profile": dict(profile),
            "metrics": dict(metrics),
            "adaptation": ad,
            "reasoning": reasoning,
            "memory": mem_snapshot,
        }
        steps.append(step)

        yield f"event: replay:timeline\ndata: {json.dumps({'week_number': week_num, 'bloom': ad['bloom'], 'timeline': {'memory_records': mem_snapshot['total_records'], 'scaffolding_count': ad['scaffolding']['current_count']}})}\n\n"
        await asyncio.sleep(0.03)

        yield f"event: replay:adaptation\ndata: {json.dumps({'week_number': week_num, 'adaptation': ad})}\n\n"
        await asyncio.sleep(0.03)

        yield f"event: replay:memory\ndata: {json.dumps({'week_number': week_num, 'memory': mem_snapshot})}\n\n"
        await asyncio.sleep(0.03)

        yield f"event: replay:reasoning\ndata: {json.dumps({'week_number': week_num, 'explanations': reasoning['explanations']})}\n\n"
        await asyncio.sleep(0.03)

        bloom_exp = next((e for e in reasoning.get("explanations", []) if e.get("dimension") == "bloom"), None)
        if bloom_exp:
            yield f"event: replay:bloom\ndata: {json.dumps({'week_number': week_num, 'bloom': ad['bloom'], 'explanation': bloom_exp})}\n\n"
            await asyncio.sleep(0.02)

        misconception_count = len(profile.get("common_misconceptions") or [])
        yield f"event: replay:misconception\ndata: {json.dumps({'week_number': week_num, 'count': misconception_count, 'previous_count': 0 if prev_plan is None else len((ped.build_student_profile(student_id=student_id).get('common_misconceptions') or []))})}\n\n"
        await asyncio.sleep(0.02)

        yield f"event: replay:consensus\ndata: {json.dumps({'week_number': week_num, 'consensus': ad['consensus']})}\n\n"
        await asyncio.sleep(0.02)

        prev_plan = plan

    timeline = timeline_builder.build(steps)
    longitudinal_metrics = timeline_builder.compute_metrics(timeline)

    yield f"event: replay:complete\ndata: {json.dumps({'student_id': student_id, 'weeks_replayed': len(steps), 'timeline': timeline, 'metrics': longitudinal_metrics})}\n\n"


# ── REST endpoints ───────────────────────────────────────────────────


@router.get("/sessions")
def list_sessions(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """List all students with replayable sessions (weekly plans)."""
    rows = (
        db.query(
            WeeklyPedagogicalPlan.teacher_id,
            WeeklyPedagogicalPlan.course_id,
            User.first_name,
            User.last_name,
        )
        .join(User, User.id == WeeklyPedagogicalPlan.teacher_id)
        .distinct()
        .limit(limit)
        .all()
    )
    results = []
    for teacher_id, course_id, first_name, last_name in rows:
        plan_count = (
            db.query(WeeklyPedagogicalPlan)
            .filter(
                WeeklyPedagogicalPlan.teacher_id == teacher_id,
                WeeklyPedagogicalPlan.course_id == course_id,
            )
            .count()
        )
        course = db.query(Course).filter(Course.id == course_id).first()
        results.append({
            "student_id": teacher_id,
            "course_id": course_id,
            "course_name": course.name if course else "Unknown",
            "student_name": f"{first_name or ''} {last_name or ''}".strip(),
            "total_weeks": plan_count,
        })
    return {"sessions": results, "total": len(results)}


@router.get("/session/{session_id}")
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Get full replay session for a student_id (= teacher_id in plans)."""
    replay = session_replay.replay(db, student_id=session_id, course_id="")
    return replay


@router.get("/student/{student_id}")
def get_student_replay(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Full student replay with all steps."""
    store = memory_store_from_session(db)
    replay = session_replay.replay(db, student_id=student_id, course_id="", memory_store=store)
    return replay


@router.get("/student/{student_id}/timeline")
def get_student_timeline(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Longitudinal timeline only (bloom, confidence, memory growth)."""
    store = memory_store_from_session(db)
    replay = session_replay.replay(db, student_id=student_id, course_id="", memory_store=store)
    return {
        "student_id": student_id,
        "timeline": replay["timeline"],
        "metrics": replay["metrics"],
    }


@router.get("/student/{student_id}/adaptation")
def get_student_adaptation(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Adaptation decisions per week."""
    plans = (
        db.query(WeeklyPedagogicalPlan)
        .filter(WeeklyPedagogicalPlan.teacher_id == student_id)
        .order_by(WeeklyPedagogicalPlan.week_number.asc())
        .all()
    )
    return {
        "student_id": student_id,
        "adaptations": adaptation_replay.replay_all(list(plans)),
    }


@router.get("/student/{student_id}/reasoning")
def get_student_reasoning(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Reasoning explanations per week."""
    store = memory_store_from_session(db)
    ped = PedagogicalMemoryService(store)
    plans = (
        db.query(WeeklyPedagogicalPlan)
        .filter(WeeklyPedagogicalPlan.teacher_id == student_id)
        .order_by(WeeklyPedagogicalPlan.week_number.asc())
        .all()
    )
    profiles = [ped.build_student_profile(student_id=student_id) for _ in plans]
    return {
        "student_id": student_id,
        "reasoning": reasoning_replay.replay_all(student_id, profiles, list(plans)),
    }


@router.get("/student/{student_id}/memory")
def get_student_memory(
    student_id: str,
    db: Session = Depends(get_db),
):
    """Memory snapshots per week."""
    store = memory_store_from_session(db)
    plans = (
        db.query(WeeklyPedagogicalPlan)
        .filter(WeeklyPedagogicalPlan.teacher_id == student_id)
        .order_by(WeeklyPedagogicalPlan.week_number.asc())
        .all()
    )
    snapshots = []
    for plan in plans:
        module_id = f"{plan.course_id}:week{plan.week_number}"
        snap = memory_replay.snapshot(store, student_id, module_id, weeks=plan.week_number)
        snapshots.append({"week_number": plan.week_number, **snap})

    deltas = []
    for i in range(1, len(snapshots)):
        deltas.append({
            "from_week": snapshots[i - 1]["week_number"],
            "to_week": snapshots[i]["week_number"],
            **memory_replay.deltas(snapshots[i - 1], snapshots[i]),
        })

    return {
        "student_id": student_id,
        "snapshots": snapshots,
        "deltas": deltas,
    }


@router.get("/student/{student_id}/export")
def get_student_export(
    student_id: str,
    db: Session = Depends(get_db),
    fmt: str = Query("json", description="Export format: json, csv, markdown, latex"),
):
    """Export full replay in academic format."""
    store = memory_store_from_session(db)
    replay = session_replay.replay(db, student_id=student_id, course_id="", memory_store=store)

    content_type_map = {
        "json": "application/json",
        "csv": "text/csv",
        "markdown": "text/markdown",
        "latex": "application/x-latex",
    }
    content_type = content_type_map.get(fmt, "application/json")

    if fmt == "json":
        return replay
    elif fmt == "csv":
        csv_content = replay_exporter.to_csv(replay)
        return StreamingResponse(
            iter([csv_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename=replay_{student_id}.csv"},
        )
    elif fmt == "markdown":
        md_content = replay_exporter.to_markdown(replay)
        return StreamingResponse(
            iter([md_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename=replay_{student_id}.md"},
        )
    elif fmt == "latex":
        latex_content = replay_exporter.to_latex(replay)
        return StreamingResponse(
            iter([latex_content]),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename=replay_{student_id}.tex"},
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {fmt}")


# ── SSE streaming ────────────────────────────────────────────────────


@router.get("/stream/{student_id}")
async def stream_replay(
    student_id: str,
    db: Session = Depends(get_db),
):
    """SSE stream that emits full replay events for the interactive dashboard.

    Events: replay:start, replay:timeline, replay:adaptation, replay:memory,
            replay:reasoning, replay:bloom, replay:misconception,
            replay:consensus, replay:complete
    """
    return StreamingResponse(
        _replay_event_stream(student_id, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
