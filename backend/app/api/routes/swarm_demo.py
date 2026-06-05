from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field

from app.demo.events import DemoEventEmitter
from app.demo.memory import SQLiteSharedMemoryStore
from app.demo.orchestrator import SwarmDemoOrchestrator
from app.replay.export import ReplayExporter
from app.replay.models import ReplayMode
from app.replay.replayer import CognitiveReplayer
from app.replay.session_store import ReplaySessionStore


router = APIRouter(prefix="/api/swarm/demo", tags=["Swarm Demo"])

store = SQLiteSharedMemoryStore()
emitter = DemoEventEmitter(store)
orchestrator = SwarmDemoOrchestrator(store, emitter)
replay_store = ReplaySessionStore(store)
replay_exporter = ReplayExporter()


class StartDemoRequest(BaseModel):
    seed: int = Field(default=42, ge=1, le=999999)


@router.post("/run")
async def run_demo(payload: StartDemoRequest):
    return await orchestrator.start(seed=payload.seed)


@router.get("/latest")
def latest_demo():
    session_id = store.latest_session_id()
    return {"session_id": session_id}


@router.get("/replay/{session_id}")
def replay_demo(session_id: str):
    replay = store.replay(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return replay


@router.get("/replay/{session_id}/cognitive")
def cognitive_replay(session_id: str):
    replay = replay_store.load(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return replay.to_dict()


@router.get("/replay/{session_id}/step/{index}")
def replay_step(session_id: str, index: int):
    replay = replay_store.load(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Demo session not found")
    event = CognitiveReplayer(replay).step(index)
    if event is None:
        raise HTTPException(status_code=404, detail="Replay step not found")
    return event.to_dict()


@router.get("/replay/{session_id}/export")
def export_replay(session_id: str, fmt: str = Query("json", pattern="^(json|markdown|md|html|summary)$")):
    replay = replay_store.load(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Demo session not found")
    body, media_type = replay_exporter.export(replay, fmt)
    if isinstance(body, dict):
        return JSONResponse(body)
    return Response(content=body, media_type=media_type)


@router.get("/replay/{session_id}/stream")
async def replay_stream(
    session_id: str,
    mode: ReplayMode = Query(ReplayMode.ACCELERATED),
    speed: float = Query(4.0, ge=1.0, le=20.0),
):
    replay = replay_store.load(session_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Demo session not found")

    async def event_stream():
        yield ": replay connected\n\n"
        async for event in CognitiveReplayer(replay).stream(mode=mode, speed=speed):
            yield (
                f"id: {event.id}\n"
                f"event: replay.frame\n"
                f"data: {json.dumps(event.to_dict(), ensure_ascii=False)}\n\n"
            )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/events/{session_id}")
async def demo_events(session_id: str, after_id: int = Query(0, ge=0)):
    return StreamingResponse(
        emitter.subscribe(session_id, after_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
