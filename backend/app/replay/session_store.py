from __future__ import annotations

from typing import Any

from app.replay.models import LegacyReplaySession as ReplaySession
from app.replay.timeline import ReplayTimelineBuilder


class ReplaySessionStore:
    """Builds cognitive replay sessions from an existing event-log store."""

    def __init__(self, event_store: Any, timeline_builder: ReplayTimelineBuilder | None = None):
        self.event_store = event_store
        self.timeline_builder = timeline_builder or ReplayTimelineBuilder()

    def load(self, session_id: str) -> ReplaySession | None:
        raw = self.event_store.replay(session_id)
        if raw is None:
            return None
        events, summary = self.timeline_builder.build(raw)
        return ReplaySession(session=raw["session"], events=events, summary=summary)

    def latest(self) -> ReplaySession | None:
        session_id = self.event_store.latest_session_id()
        return self.load(session_id) if session_id else None
