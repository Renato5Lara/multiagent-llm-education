from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ReplayPhase(str, Enum):
    RESEARCH = "research"
    PEDAGOGICAL = "pedagogical"
    ADAPTIVE = "adaptive"
    MULTIMODAL = "multimodal"
    PROMPT = "prompt"
    CONSISTENCY = "consistency"
    SANDBOX_VALIDATION = "sandbox_validation"
    CONSENSUS = "consensus"


class ReplayEventType(str, Enum):
    START = "replay:start"
    FRAME = "replay:frame"
    ADAPTATION = "replay:adaptation"
    CONSENSUS = "replay:consensus"
    MEMORY = "replay:memory"
    REASONING = "replay:reasoning"
    COMPLETE = "replay:complete"


@dataclass
class ReplayFrame:
    session_id: str
    step: int
    phase: ReplayPhase
    agent: str
    timestamp: float = field(default_factory=time.time)
    data: dict[str, Any] = field(default_factory=dict)
    delta: dict[str, Any] | None = None
    reasoning: str = ""
    signal: str = ""
    agent_decision: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        base = asdict(self)
        base["phase"] = self.phase.value
        return base


@dataclass
class ReplaySession:
    session_id: str
    topic: str
    started_at: float = field(default_factory=time.time)
    frames: list[ReplayFrame] = field(default_factory=list)
    completed_at: float | None = None

    @property
    def duration_ms(self) -> float:
        end = self.completed_at or time.time()
        return (end - self.started_at) * 1000

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": round(self.duration_ms, 2),
            "frame_count": self.frame_count,
            "frames": [f.to_dict() for f in self.frames],
        }


@dataclass
class CognitiveTrack:
    name: str
    label: str
    history: list[dict[str, Any]] = field(default_factory=list)

    def push(self, step: int, value: Any, delta: str | None = None):
        self.history.append({
            "step": step,
            "value": value,
            "delta": delta,
            "timestamp": time.time(),
        })

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "label": self.label, "history": self.history}


TRACK_DEFINITIONS: list[tuple[str, str]] = [
    ("weekly_evolution", "Evolución Semanal"),
    ("bloom_evolution", "Evolución Bloom"),
    ("misconceptions", "Misconceptions Históricas"),
    ("pacing_changes", "Cambios de Pacing"),
    ("multimodal_adaptation", "Adaptación Multimodal"),
    ("confidence_evolution", "Cambios de Confianza"),
    ("consensus_evolution", "Evolución de Consenso"),
    ("narrative_continuity", "Continuidad Narrativa"),
    ("prompt_evolution", "Evolución de Prompts"),
    ("cognitive_load", "Evolución de Carga Cognitiva"),
]


# ---------------------------------------------------------------------------
# Legacy schema (pre-5a1fb44 replay subsystem), still consumed by
# session_store, export, replayer, serializer, timeline and swarm_demo.
# The legacy ReplaySession is renamed LegacyReplaySession because the engine
# schema above owns the ReplaySession name; legacy consumers import it with
# `LegacyReplaySession as ReplaySession`.
# ---------------------------------------------------------------------------


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
class LegacyReplaySession:
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
