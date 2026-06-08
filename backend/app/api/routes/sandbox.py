from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.sandbox import SandboxRequest, SandboxRunner


router = APIRouter(prefix="/api/sandbox", tags=["Python REPL Sandbox"])

runner = SandboxRunner()


@router.post("/execute")
async def execute_sandbox(request: SandboxRequest):
    """Execute educational Python code in the isolated Docker sandbox."""
    result = await runner.run(request)
    return result.model_dump(mode="json")


@router.post("/execute/stream")
async def stream_sandbox_execution(request: SandboxRequest):
    """SSE observable execution for live sandbox verification traces."""

    async def events():
        start_payload = {
            "phase": "code_verification",
            "status": "started",
            "limits": request.limits.model_dump(mode="json"),
            "metadata": request.metadata,
        }
        yield _sse("sandbox.start", start_payload)

        result = await runner.run(request)
        yield _sse(
            "sandbox.complete",
            {
                "phase": "code_verification",
                "status": result.status.value,
                "success": result.success,
                "result": result.to_replay_payload(),
            },
        )

    return StreamingResponse(events(), media_type="text/event-stream; charset=utf-8")


def _sse(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
