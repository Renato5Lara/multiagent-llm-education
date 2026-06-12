from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.replay.models import ReplayEvent, ReplayMode, LegacyReplaySession as ReplaySession


class CognitiveReplayer:
    def __init__(self, replay: ReplaySession):
        self.replay = replay

    async def stream(
        self,
        *,
        mode: ReplayMode = ReplayMode.ACCELERATED,
        speed: float = 4.0,
    ) -> AsyncIterator[ReplayEvent]:
        previous: ReplayEvent | None = None
        for event in self.replay.events:
            if previous is not None and mode in {ReplayMode.REALTIME, ReplayMode.ACCELERATED, ReplayMode.COGNITIVE}:
                delay_ms = event.latency_ms
                if mode in {ReplayMode.ACCELERATED, ReplayMode.COGNITIVE}:
                    delay_ms = delay_ms / max(1.0, speed)
                await asyncio.sleep(min(delay_ms / 1000, 3.0))
            yield event
            previous = event

    def step(self, index: int) -> ReplayEvent | None:
        if index < 0 or index >= len(self.replay.events):
            return None
        return self.replay.events[index]
