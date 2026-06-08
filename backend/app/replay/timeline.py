from __future__ import annotations

import uuid
from typing import Any

from app.replay.models import ReplayEvent, ReplaySummary, parse_timestamp


PHASE_BY_TYPE = {
    "session.started": "objective",
    "swarm.activated": "orchestration",
    "retrieval:start": "retrieval",
    "retrieval:source": "retrieval",
    "retrieval:complete": "retrieval",
    "contradiction:detected": "validation",
    "misconception:detected": "pedagogy",
    "prompt:generated": "prompting",
    "sandbox:start": "code_verification",
    "sandbox:complete": "code_verification",
    "sandbox:violation": "code_verification",
    "consistency:validated": "continuity",
    "agent.thinking": "deliberation",
    "vote.cast": "consensus",
    "consensus.updated": "consensus",
    "trust.updated": "observability",
    "memory.published": "memory",
    "anomaly.detected": "observability",
    "session.completed": "completion",
}

AGENT_BY_TYPE = {
    "retrieval:start": "research",
    "retrieval:source": "research",
    "retrieval:complete": "research",
    "contradiction:detected": "consistency",
    "misconception:detected": "pedagogical",
    "prompt:generated": "prompt_generator",
    "sandbox:start": "reviewer",
    "sandbox:complete": "reviewer",
    "sandbox:violation": "reviewer",
    "consistency:validated": "consistency",
}

COGNITIVE_LABELS = {
    "session.started": "Teacher objective captured",
    "retrieval:start": "Research plan formed",
    "retrieval:source": "External knowledge grounded",
    "contradiction:detected": "Source conflict resolved",
    "misconception:detected": "Learner risk surfaced",
    "prompt:generated": "Multimodal prompt grounded",
    "sandbox:start": "Code verification sandbox started",
    "sandbox:complete": "Educational code validated in sandbox",
    "sandbox:violation": "Unsafe code blocked by sandbox",
    "retrieval:complete": "Research synthesis completed",
    "memory.published": "Shared memory updated",
    "agent.thinking": "Agent begins deliberation",
    "vote.cast": "Consensus evidence contributed",
    "consensus.updated": "Collective decision shifts",
    "consistency:validated": "Narrative continuity validated",
    "session.completed": "Replayable cognition finalized",
}

NARRATIVE_STEPS = {
    "session.started": "docente define objetivo",
    "retrieval:start": "retrieval comienza",
    "retrieval:source": "fuentes aparecen",
    "contradiction:detected": "contradiction detected",
    "misconception:detected": "misconception identified",
    "agent.thinking": "agents deliberate",
    "vote.cast": "agents deliberate",
    "consensus.updated": "consensus emerges",
    "prompt:generated": "prompts generated",
    "sandbox:start": "ReviewerAgent executes sandbox",
    "sandbox:complete": "code verification completed",
    "sandbox:violation": "unsafe code blocked",
    "memory.published": "memory updated",
    "consistency:validated": "continuity validated",
}


class ReplayTimelineBuilder:
    def build(self, raw_replay: dict[str, Any]) -> tuple[list[ReplayEvent], ReplaySummary]:
        raw_events = list(raw_replay.get("events") or [])
        session = raw_replay.get("session") or {}
        correlation_id = f"replay-{session.get('session_id', 'unknown')}"
        timeline: list[ReplayEvent] = []
        previous_ts = None

        for index, raw in enumerate(raw_events):
            timestamp = str(raw.get("created_at") or raw.get("timestamp") or "")
            current_ts = parse_timestamp(timestamp)
            if previous_ts is None:
                latency_ms = 0.0
            else:
                latency_ms = max(0.0, (current_ts - previous_ts).total_seconds() * 1000)
            previous_ts = current_ts

            event_type = str(raw.get("type") or raw.get("event_type") or "")
            payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
            replay_event = ReplayEvent(
                id=int(raw.get("id") or index + 1),
                session_id=str(raw.get("session_id") or session.get("session_id") or ""),
                event_type=event_type,
                timestamp=timestamp,
                payload=payload,
                trace_id=str(payload.get("trace_id") or self._trace_id(raw, event_type)),
                correlation_id=str(payload.get("correlation_id") or correlation_id),
                agent_name=self._agent_name(event_type, payload),
                phase=str(payload.get("phase") or PHASE_BY_TYPE.get(event_type, "unknown")),
                latency_ms=round(latency_ms, 2),
                confidence=self._confidence(event_type, payload),
                metadata=self._metadata(event_type, payload),
                cognitive_label=COGNITIVE_LABELS.get(event_type, event_type),
                narrative_step=NARRATIVE_STEPS.get(event_type, ""),
            )
            timeline.append(replay_event)

        return timeline, self._summary(session, timeline)

    def _summary(self, session: dict[str, Any], events: list[ReplayEvent]) -> ReplaySummary:
        final = next((event for event in reversed(events) if event.event_type == "session.completed"), None)
        final_payload = final.payload if final else {}
        duration_ms = 0.0
        if len(events) >= 2:
            duration_ms = max(
                0.0,
                (parse_timestamp(events[-1].timestamp) - parse_timestamp(events[0].timestamp)).total_seconds() * 1000,
            )
        return ReplaySummary(
            session_id=str(session.get("session_id") or (events[0].session_id if events else "")),
            event_count=len(events),
            duration_ms=round(duration_ms, 2),
            phases=sorted({event.phase for event in events if event.phase}),
            agents=sorted({event.agent_name for event in events if event.agent_name}),
            retrieval_sources=sum(1 for event in events if event.event_type == "retrieval:source"),
            consensus_votes=sum(1 for event in events if event.event_type == "vote.cast"),
            memory_publications=sum(1 for event in events if event.event_type == "memory.published"),
            generated_prompts=sum(1 for event in events if event.event_type == "prompt:generated"),
            contradictions=sum(1 for event in events if event.event_type == "contradiction:detected"),
            misconceptions=sum(1 for event in events if event.event_type == "misconception:detected"),
            final_decision=final_payload.get("decision"),
            final_confidence=final_payload.get("confidence"),
        )

    def _agent_name(self, event_type: str, payload: dict[str, Any]) -> str:
        return str(
            payload.get("agent")
            or payload.get("agent_name")
            or payload.get("voter_name")
            or AGENT_BY_TYPE.get(event_type)
            or "system"
        )

    def _confidence(self, event_type: str, payload: dict[str, Any]) -> float | None:
        for key in ("confidence", "retrieval_confidence", "pedagogical_confidence", "grounding_score", "continuity_score"):
            value = payload.get(key)
            if isinstance(value, int | float):
                return round(float(value), 4)
        if event_type == "retrieval:source" and isinstance(payload.get("score"), int | float):
            return round(float(payload["score"]), 4)
        return None

    def _metadata(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        keys = [
            "category",
            "domain",
            "query_id",
            "rank",
            "decision",
            "severity",
            "memory_id",
            "key",
            "modality",
            "bloom_level",
            "status",
            "approved",
            "success",
        ]
        metadata = {key: payload[key] for key in keys if key in payload}
        metadata["event_family"] = event_type.split(":", 1)[0].split(".", 1)[0]
        return metadata

    def _trace_id(self, raw: dict[str, Any], event_type: str) -> str:
        seed = f"{raw.get('session_id')}:{raw.get('id')}:{event_type}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
