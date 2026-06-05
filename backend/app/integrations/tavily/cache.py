"""Small async TTL cache for Tavily responses."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TavilyCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl_seconds = ttl_seconds
        self._items: dict[str, _CacheEntry] = {}

    async def get(self, key: str) -> Any | None:
        entry = self._items.get(self._normalize(key))
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._items.pop(self._normalize(key), None)
            return None
        return entry.value

    async def set(self, key: str, value: Any) -> None:
        self._items[self._normalize(key)] = _CacheEntry(
            value=value,
            expires_at=time.monotonic() + self.ttl_seconds,
        )

    async def clear(self) -> None:
        self._items.clear()

    @staticmethod
    def _normalize(key: str) -> str:
        return " ".join(str(key).lower().split())
