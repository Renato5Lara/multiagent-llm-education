from __future__ import annotations

from typing import Any


class ReplayRecorder:
    """Thin recording adapter for event emitters that persist SSE events."""

    def __init__(self, emitter: Any):
        self.emitter = emitter

    async def record(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
        *,
        trace_id: str | None = None,
        correlation_id: str | None = None,
        agent_name: str | None = None,
        phase: str | None = None,
        confidence: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        enriched = dict(payload)
        if trace_id:
            enriched["trace_id"] = trace_id
        if correlation_id:
            enriched["correlation_id"] = correlation_id
        if agent_name:
            enriched["agent_name"] = agent_name
        if phase:
            enriched["phase"] = phase
        if confidence is not None:
            enriched["confidence"] = confidence
        if metadata:
            enriched["metadata"] = metadata
        return await self.emitter.emit(session_id, event_type, enriched)
