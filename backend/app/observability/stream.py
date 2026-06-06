"""
Real-time event bus backed by asyncio queues and Server-Sent Events.
Provides a single push / multi-subscriber fan-out.

Usage:
    stream = MetricsStream()
    # Producer side:
    stream.push({"type": "consensus", "data": {...}})

    # Consumer side (FastAPI SSE):
    @router.get("/stream")
    async def sse():
        async with stream.subscribe() as queue:
            async for event in stream.generate(queue):
                yield event
"""
from __future__ import annotations

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from app.observability.metrics_exporter import exporter


class MetricsStream:
    """Async fan-out event bus with bounded per-subscriber buffers."""

    def __init__(self, max_queue_size: int = 256, keepalive_interval: float = 15.0):
        self._subscribers: dict[int, asyncio.Queue] = {}
        self._counter = 0
        self._lock = asyncio.Lock()
        self._max_queue_size = max_queue_size
        self._keepalive_interval = keepalive_interval
        self._event_id = 0

    async def push(self, event_type: str, data: Any) -> None:
        """Push an event to all subscribers. Silently drops for slow consumers."""
        self._event_id += 1
        payload = {
            "id": self._event_id,
            "type": event_type,
            "data": data,
            "timestamp": time.time(),
        }
        async with self._lock:
            stale = []
            for sid, queue in self._subscribers.items():
                try:
                    queue.put_nowait(payload)
                except asyncio.QueueFull:
                    # Drop oldest to keep queue bounded
                    try:
                        queue.get_nowait()
                        queue.put_nowait(payload)
                    except asyncio.QueueEmpty:
                        pass
            # Prune stale subscribers that got garbage-collected
            # (will be pruned naturally via unsubscribe on exit)

    async def _subscribe(self) -> tuple[int, asyncio.Queue]:
        sid = self._counter
        self._counter += 1
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._max_queue_size)
        async with self._lock:
            self._subscribers[sid] = queue
        return sid, queue

    async def _unsubscribe(self, sid: int) -> None:
        async with self._lock:
            self._subscribers.pop(sid, None)

    @asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue, None]:
        sid, queue = await self._subscribe()
        try:
            yield queue
        finally:
            await self._unsubscribe(sid)

    async def generate(
        self, queue: asyncio.Queue,
    ) -> AsyncGenerator[str, None]:
        """Async generator that yields SSE-formatted strings.

        Sends periodic keepalive comments and a snapshot of current
        metrics every 5 seconds.  A single `flush: metrics` sentinel
        triggers one snapshot push.
        """
        last_snapshot = 0.0
        while True:
            now = time.time()
            try:
                # Wait for an event or timeout (for keepalive/snapshot)
                payload = await asyncio.wait_for(
                    queue.get(), timeout=min(self._keepalive_interval, 5.0)
                )
                yield f"id: {payload['id']}\nevent: {payload['type']}\ndata: {json.dumps(payload['data'])}\n\n"
            except asyncio.TimeoutError:
                # Periodic full-metrics snapshot
                if now - last_snapshot >= 5.0:
                    last_snapshot = now
                    snapshot = exporter.json_snapshot()
                    yield f"event: snapshot\ndata: {json.dumps(snapshot)}\n\n"
                else:
                    # Keepalive comment (ignored by EventSource)
                    yield ": keepalive\n\n"


    # ── Sync-safe push (for engine callbacks) ───────────────────────

    def push_sync(self, event_type: str, data: Any) -> None:
        """Synchronous push for use from non-async contexts (engine hooks).

        Safely schedules the async push on the running event loop.
        If no loop is running, the event is silently dropped.
        """
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.push(event_type, data), loop
                )
        except RuntimeError:
            pass  # no running loop


# Module-level singleton
stream: MetricsStream = MetricsStream()
