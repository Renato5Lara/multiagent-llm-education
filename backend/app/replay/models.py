from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReplayMode(str, Enum):
    REALTIME = "realtime"
    ACCELERATED = "accelerated"
    STEP_BY_STEP = "step-by-step"
    COGNITIVE = "cognitive"


@dataclass(frozen=True)
class ReplayEvent:
    id: int
    session_id: str
    event_type: str
    timestamp: str
    payload: dict[str, Any]
    trace_id: str
    correlation_id: str
    agent_name: str
    phase: str
    latency_ms: float
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    cognitive_label: str = ""
    narrative_step: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "agent_name": self.agent_name,
            "phase": self.phase,
            "latency_ms": self.latency_ms,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "cognitive_label": self.cognitive_label,
            "narrative_step": self.narrative_step,
        }


@dataclass(frozen=True)
class ReplaySummary:
    session_id: str
    event_count: int
    duration_ms: float
    phases: list[str]
    agents: list[str]
    retrieval_sources: int
    consensus_votes: int
    memory_publications: int
    generated_prompts: int
    contradictions: int
    misconceptions: int
    final_decision: str | None
    final_confidence: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "event_count": self.event_count,
            "duration_ms": self.duration_ms,
            "phases": self.phases,
            "agents": self.agents,
            "retrieval_sources": self.retrieval_sources,
            "consensus_votes": self.consensus_votes,
            "memory_publications": self.memory_publications,
            "generated_prompts": self.generated_prompts,
            "contradictions": self.contradictions,
            "misconceptions": self.misconceptions,
            "final_decision": self.final_decision,
            "final_confidence": self.final_confidence,
        }


@dataclass(frozen=True)
class ReplaySession:
    session: dict[str, Any]
    events: list[ReplayEvent]
    summary: ReplaySummary
    modes: list[ReplayMode] = field(default_factory=lambda: list(ReplayMode))

    def to_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "events": [event.to_dict() for event in self.events],
            "summary": self.summary.to_dict(),
            "modes": [mode.value for mode in self.modes],
        }


def parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)
