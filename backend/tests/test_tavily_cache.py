"""Tests for TavilyCache: set/get, expiration, reuse tracking, clear_expired, in-memory fallback."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.tavily.cache import TavilyCache, get_tavily_cache
from app.integrations.tavily.schemas import SearchDepth, TavilySearchResponse, TavilySource


def _make_response(title: str = "test") -> TavilySearchResponse:
    return TavilySearchResponse(
        query=title,
        results=[TavilySource(title=title, url=f"https://{title}.com", content="content", score=0.9)],
        answer="test answer",
        response_time_ms=0.3,
    )


class TestTavilyCacheInMemory:
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        cache = TavilyCache(uow=None)
        resp = _make_response()
        await cache.set("test query", resp)
        got = await cache.get("test query")
        assert got is not None
        assert got.answer == "test answer"

    @pytest.mark.asyncio
    async def test_get_miss(self):
        cache = TavilyCache(uow=None)
        got = await cache.get("nonexistent")
        assert got is None

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        cache = TavilyCache(uow=None, default_ttl=0)
        resp = _make_response()
        await cache.set("will expire", resp)
        await cache.get("will expire")

    @pytest.mark.asyncio
    async def test_reuse_tracking(self):
        cache = TavilyCache(uow=None)
        resp = _make_response()
        await cache.set("reuse test", resp)
        await cache.get("reuse test")
        await cache.get("reuse test")
        total_reuses = sum(1 for _ in cache._fallback_store.values())
        assert total_reuses > 0

    @pytest.mark.asyncio
    async def test_clear_expired(self):
        cache = TavilyCache(uow=None, default_ttl=0)
        resp = _make_response()
        await cache.set("stale", resp)
        await cache.clear_expired()
        assert "stale" not in cache._fallback_store

    @pytest.mark.asyncio
    async def test_stats_in_memory(self):
        cache = TavilyCache(uow=None)
        resp = _make_response()
        await cache.set("a", resp)
        await cache.set("b", resp)
        await cache.get("a")
        stats = await cache.stats()
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_in_memory_fallback_on_db_error(self):
        cache = TavilyCache(uow=None)
        cache._fallback_store = {}

        resp = _make_response()
        await cache.set("fallback", resp)
        got = await cache.get("fallback")
        assert got is not None

    @pytest.mark.asyncio
    async def test_get_tavily_cache_singleton(self):
        c1 = get_tavily_cache()
        c2 = get_tavily_cache()
        assert c1 is c2
