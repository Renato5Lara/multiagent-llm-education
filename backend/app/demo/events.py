from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any, AsyncIterator

from app.demo.memory import SQLiteSharedMemoryStore


class DemoEventEmitter:
    """Persists demo events and fans them out to live SSE subscribers."""

    def __init__(self, store: SQLiteSharedMemoryStore):
        self._store = store
        self._queues: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def emit(self, session_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        event = await asyncio.to_thread(self._store.append_event, session_id, event_type, payload)
        async with self._lock:
            queues = list(self._queues.get(session_id, set()))
        for queue in queues:
            queue.put_nowait(event)
        return event

    async def subscribe(self, session_id: str, after_id: int = 0) -> AsyncIterator[str]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        async with self._lock:
            self._queues[session_id].add(queue)
        try:
            yield ": connected\n\n"
            for event in await asyncio.to_thread(self._store.events, session_id, after_id):
                yield self._format(event)
                if event["type"] == "session.completed":
                    return

            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                    yield self._format(event)
                    if event["type"] == "session.completed":
                        return
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            async with self._lock:
                self._queues[session_id].discard(queue)

    @staticmethod
    def _format(event: dict[str, Any]) -> str:
        return (
            f"id: {event['id']}\n"
            f"event: {event['type']}\n"
            f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        )
