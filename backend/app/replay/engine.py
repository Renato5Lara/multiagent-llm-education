from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from app.observability.stream import stream
from app.replay.models import (
    CognitiveTrack,
    ReplayEventType,
    ReplayFrame,
    ReplayPhase,
    ReplaySession,
    TRACK_DEFINITIONS,
)
from app.replay.tracks import CognitiveTracker

logger = logging.getLogger(__name__)


class ReplayEngine:
    def __init__(self):
        self._sessions: dict[str, ReplaySession] = {}
        self._active_session: ReplaySession | None = None
        self._step_counter: int = 0
        self.cognitive: CognitiveTracker = CognitiveTracker()

    @property
    def active_session(self) -> ReplaySession | None:
        return self._active_session

    def start_session(self, topic: str, session_id: str | None = None) -> str:
        sid = session_id or str(uuid.uuid4())[:12]
        self._step_counter = 0
        session = ReplaySession(session_id=sid, topic=topic)
        self._sessions[sid] = session
        self._active_session = session
        self._emit(ReplayEventType.START, {
            "session_id": sid,
            "topic": topic,
            "started_at": session.started_at,
        })
        logger.info("Replay[%s]: session started for topic='%s'", sid, topic[:40])
        return sid

    def record_frame(
        self,
        phase: ReplayPhase,
        agent: str,
        data: dict[str, Any],
        *,
        reasoning: str = "",
        signal: str = "",
        agent_decision: str = "",
        evidence: dict | None = None,
        delta: dict | None = None,
    ) -> ReplayFrame | None:
        if not self._active_session:
            return None
        self._step_counter += 1
        frame = ReplayFrame(
            session_id=self._active_session.session_id,
            step=self._step_counter,
            phase=phase,
            agent=agent,
            data=data,
            reasoning=reasoning,
            signal=signal,
            agent_decision=agent_decision,
            evidence=evidence or {},
            delta=delta,
        )
        self._active_session.frames.append(frame)
        self._emit(ReplayEventType.FRAME, frame.to_dict())
        return frame

    def record_adaptation(self, delta: str, signal: str, source_agent: str, data: dict):
        payload = {
            "delta": delta,
            "signal": signal,
            "agent": source_agent,
            "data": data,
            "step": self._step_counter,
            "session_id": self._active_session.session_id if self._active_session else None,
        }
        self._emit(ReplayEventType.ADAPTATION, payload)

    def record_consensus(
        self,
        decision: str,
        confidence: float,
        voter_breakdown: dict,
        unanimous: bool = False,
    ):
        payload = {
            "decision": decision,
            "confidence": round(confidence, 3),
            "voter_breakdown": voter_breakdown,
            "unanimous": unanimous,
            "step": self._step_counter,
        }
        self._emit(ReplayEventType.CONSENSUS, payload)

    def record_reasoning(self, agent: str, reasoning: str, evidence: dict):
        payload = {
            "agent": agent,
            "reasoning": reasoning,
            "evidence": evidence,
            "step": self._step_counter,
        }
        self._emit(ReplayEventType.REASONING, payload)

    def record_memory(self, operation: str, key: str, value: Any):
        payload = {
            "operation": operation,
            "key": key,
            "value": value,
            "step": self._step_counter,
        }
        self._emit(ReplayEventType.MEMORY, payload)

    def complete_session(self) -> dict[str, Any] | None:
        if not self._active_session:
            return None
        self._active_session.completed_at = time.time()
        summary = self._build_summary()
        self._emit(ReplayEventType.COMPLETE, summary)
        session = self._active_session
        self._active_session = None
        logger.info(
            "Replay[%s]: session completed — %d frames in %.0fms",
            session.session_id, session.frame_count, session.duration_ms,
        )
        return summary

    def get_session(self, session_id: str) -> ReplaySession | None:
        return self._sessions.get(session_id)

    def list_sessions(self, limit: int = 20) -> list[dict]:
        sessions = sorted(
            self._sessions.values(),
            key=lambda s: s.started_at,
            reverse=True,
        )[:limit]
        return [s.to_dict() for s in sessions]

    def _build_summary(self) -> dict[str, Any]:
        if not self._active_session:
            return {}
        s = self._active_session
        return {
            "session_id": s.session_id,
            "topic": s.topic,
            "duration_ms": round(s.duration_ms, 2),
            "frame_count": s.frame_count,
            "cognitive_tracks": self.cognitive.snapshot(),
        }

    def _emit(self, event_type: ReplayEventType, data: dict):
        stream.push_sync(event_type.value, data)

    def reset(self):
        self.__init__()


engine: ReplayEngine = ReplayEngine()
