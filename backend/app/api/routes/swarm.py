"""/api/swarm endpoints — diagnostics health, tracing spans, memory dashboard."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.db.session import SessionLocal
from app.memory.shared_memory import SharedMemoryStore, memory_store_from_session
from app.memory.pedagogical_memory import PedagogicalMemoryService
from app.explainability.adaptive_reasoning import adaptive_reasoning
from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
from app.swarm_diagnostics import diagnostics_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/swarm", tags=["Swarm"])


@router.get("/memory")
def query_memory(
    student_id: Optional[str] = Query(None),
    module_id: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    key: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Query shared memory records by scope and type."""
    store = memory_store_from_session(db)
    records = store.query(
        student_id=student_id,
        module_id=module_id,
        memory_type=memory_type,
        key=key,
        limit=limit,
        include_stale=False,
    )
    return {
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "voter_name": r.voter_name,
                "memory_type": r.memory_type,
                "key": r.key,
                "confidence": r.confidence,
                "student_id": r.student_id,
                "module_id": r.module_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "value": r.value,
            }
            for r in records
        ],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/memory/stream")
async def stream_memory(
    student_id: Optional[str] = Query(None),
    module_id: Optional[str] = Query(None),
    memory_type: Optional[str] = Query(None),
    poll_interval: float = Query(2.0, ge=0.5, le=30.0),
):
    """SSE stream that polls shared memory for new records at a fixed interval.

    Provides a real-time dashboard view of memory being published by the
    pedagogical swarm agents during orchestration.
    """
    last_count = 0

    async def event_stream():
        nonlocal last_count
        yield ": memory stream connected\n\n"
        while True:
            try:
                session = SessionLocal()
                try:
                    store = memory_store_from_session(session)
                    records = store.query(
                        student_id=student_id,
                        module_id=module_id,
                        memory_type=memory_type,
                        limit=100,
                        include_stale=False,
                    )
                    count = len(records)
                    if count > last_count:
                        new_records = records[: count - last_count] if last_count > 0 else records
                        for r in new_records:
                            payload = {
                                "id": r.id,
                                "voter_name": r.voter_name,
                                "memory_type": r.memory_type,
                                "key": r.key,
                                "confidence": r.confidence,
                                "student_id": r.student_id,
                                "module_id": r.module_id,
                                "created_at": r.created_at.isoformat() if r.created_at else None,
                                "value_preview": str(r.value)[:200] if r.value else "",
                            }
                            yield f"event: memory.published\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                        last_count = count
                    yield f"event: heartbeat\ndata: {json.dumps({'count': count, 'ts': datetime.now(timezone.utc).isoformat()})}\n\n"
                finally:
                    session.close()
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'error': str(exc)[:200]})}\n\n"
            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/memory/influence")
async def stream_memory_influence(
    student_id: str = Query(..., description="Student to track"),
    poll_interval: float = Query(3.0, ge=1.0, le=30.0),
):
    """SSE stream of pedagogical adaptation metrics for a given student.

    Emits ``adaptation.metrics`` events containing real-time
    ``AdaptationMetrics`` dicts computed from shared memory.
    """
    last_metrics: dict[str, Any] = {}

    async def event_stream():
        nonlocal last_metrics
        yield ": influence stream connected\n\n"
        while True:
            try:
                session = SessionLocal()
                try:
                    store = memory_store_from_session(session)
                    svc = PedagogicalMemoryService(store)
                    metrics = svc.compute_metrics(student_id=student_id)
                    if metrics != last_metrics:
                        last_metrics = metrics
                        payload = {
                            "student_id": student_id,
                            "metrics": metrics,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                        yield f"event: adaptation.metrics\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

                    profile = svc.build_student_profile(student_id)
                    if profile:
                        profile_payload = {
                            "student_id": student_id,
                            "profile": profile,
                            "ts": datetime.now(timezone.utc).isoformat(),
                        }
                        yield f"event: student.profile\ndata: {json.dumps(profile_payload, ensure_ascii=False)}\n\n"
                finally:
                    session.close()
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'error': str(exc)[:200]})}\n\n"
            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/memory/profile/{student_id}")
def get_student_profile(student_id: str, db: Session = Depends(get_db)):
    """Get the aggregated pedagogical student profile from shared memory."""
    store = memory_store_from_session(db)
    svc = PedagogicalMemoryService(store)
    profile = svc.build_student_profile(student_id=student_id)
    metrics = svc.compute_metrics(student_id=student_id)
    return {
        "student_id": student_id,
        "profile": profile,
        "metrics": metrics,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/memory/profile/{student_id}/history")
def get_student_profile_history(student_id: str, db: Session = Depends(get_db)):
    """Get the raw pedagogical memory records for a student."""
    store = memory_store_from_session(db)
    records = store.query(student_id=student_id, memory_type="pedagogical_profile", limit=50, include_stale=False)
    return {
        "student_id": student_id,
        "count": len(records),
        "records": [
            {
                "id": r.id,
                "key": r.key,
                "confidence": r.confidence,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "value": r.value,
            }
            for r in records
        ],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/explain/{student_id}")
def get_adaptation_explanation(
    student_id: str,
    week_number: int = Query(..., ge=1),
    db: Session = Depends(get_db),
):
    """Generate an explainability report for a student's week plan.

    Returns per-dimension explanations (bloom, cognitive_load, prompt,
    modality, pacing, scaffolding), a decision graph, and reasoning metrics.
    """
    store = memory_store_from_session(db)
    ped = PedagogicalMemoryService(store)
    profile = ped.build_student_profile(student_id=student_id)
    metrics = ped.compute_metrics(student_id=student_id)

    plan = (
        db.query(WeeklyPedagogicalPlan)
        .filter(
            WeeklyPedagogicalPlan.teacher_id == student_id,
            WeeklyPedagogicalPlan.week_number == week_number,
        )
        .order_by(WeeklyPedagogicalPlan.generated_at.desc())
        .first()
    )
    previous_plan = (
        db.query(WeeklyPedagogicalPlan)
        .filter(
            WeeklyPedagogicalPlan.teacher_id == student_id,
            WeeklyPedagogicalPlan.week_number == week_number - 1,
        )
        .order_by(WeeklyPedagogicalPlan.generated_at.desc())
        .first()
    ) if week_number > 1 else None

    explanation = adaptive_reasoning.explain_from_plan(
        student_id=student_id,
        week_number=week_number,
        profile=profile,
        plan=plan,
        previous_plan=previous_plan,
        metrics=metrics,
    )
    return explanation.to_dict()


@router.get("/explain/stream")
async def stream_explain(
    student_id: str = Query(..., description="Student to explain"),
    poll_interval: float = Query(3.0, ge=1.0, le=30.0),
):
    """SSE stream of adaptation explanations for a student.

    Emits ``adaptation:decision``, ``bloom:adjusted``, ``pacing:changed``,
    ``modality:adapted``, ``overload:detected``, and ``misconception:persistent``
    events as profile signals change.
    """
    last_explanations: dict[str, Any] = {}

    async def event_stream():
        nonlocal last_explanations
        yield ": explain stream connected\n\n"
        while True:
            try:
                session = SessionLocal()
                try:
                    store = memory_store_from_session(session)
                    ped = PedagogicalMemoryService(store)
                    profile = ped.build_student_profile(student_id=student_id)
                    metrics = ped.compute_metrics(student_id=student_id)

                    plan = (
                        session.query(WeeklyPedagogicalPlan)
                        .filter(WeeklyPedagogicalPlan.teacher_id == student_id)
                        .order_by(WeeklyPedagogicalPlan.generated_at.desc())
                        .first()
                    )

                    if plan and profile:
                        prompt_plan = plan.prompt_plan or {}
                        adaptive_plan = plan.adaptive_plan or {}
                        explanation = adaptive_reasoning.explain(
                            student_id=student_id,
                            week_number=plan.week_number,
                            profile=profile,
                            prompt_plan=prompt_plan,
                            adaptive_plan=adaptive_plan,
                            metrics=metrics,
                        )
                        current = explanation.to_dict()
                        if current != last_explanations:
                            last_explanations = current

                            for exp in current.get("explanations", []):
                                dim = exp["dimension"]
                                event_map = {
                                    "bloom": "bloom:adjusted",
                                    "cognitive_load": "overload:detected",
                                    "prompt": "adaptation:decision",
                                    "modality": "modality:adapted",
                                    "pacing": "pacing:changed",
                                    "scaffolding": "adaptation:decision",
                                }
                                event_type = event_map.get(dim, "adaptation:decision")
                                yield f"event: {event_type}\ndata: {json.dumps(exp, ensure_ascii=False)}\n\n"

                            yield f"event: decision.graph\ndata: {json.dumps(current.get('decision_graph', {}), ensure_ascii=False)}\n\n"

                    yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.now(timezone.utc).isoformat()})}\n\n"
                finally:
                    session.close()
            except Exception as exc:
                yield f"event: error\ndata: {json.dumps({'error': str(exc)[:200]})}\n\n"
            await asyncio.sleep(poll_interval)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/health")
def swarm_health():
    scope = "global"
    snapshot = diagnostics_engine.health_report(scope=scope)
    data = snapshot.to_dict()
    data["requested_at"] = datetime.now(timezone.utc).isoformat()
    return data


@router.get("/spans")
def list_tracing_spans(
    limit: Optional[int] = Query(50, ge=1, le=500),
    event_type: Optional[str] = Query(None, description="Filter by event type prefix"),
):
    prefix = event_type or "tracing:span"
    events = diagnostics_engine.get_recent_events(
        event_type_prefix=prefix,
        limit=limit,
    )
    return {
        "count": len(events),
        "events": [e.to_dict() for e in events],
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
