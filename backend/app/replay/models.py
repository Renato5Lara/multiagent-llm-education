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
