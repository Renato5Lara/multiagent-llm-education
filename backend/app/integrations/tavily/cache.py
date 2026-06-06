"""TavilyCache — SQLAlchemy-based cache with TTL, SHA256 hashing, and reuse tracking."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import AsyncUnitOfWork, UnitOfWork
from app.integrations.tavily.errors import TavilyCacheError
from app.integrations.tavily.schemas import CacheEntry, SearchDepth, TavilySearchResponse, TavilySource
from app.models.retrieval import RetrievalCache
from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)

DEFAULT_TTL_SECONDS = 3600  # 1 hour
MAX_TTL_SECONDS = 86400 * 7  # 7 days


def _hash_query(query: str, depth: SearchDepth = SearchDepth.BASIC) -> str:
    raw = f"{query}|{depth.value}|v1"
    return hashlib.sha256(raw.encode()).hexdigest()


class TavilyCache:
    """Production cache for Tavily search results.

    Backed by the retrieval_cache SQLAlchemy table (PostgreSQL).
    Falls back to in-process dict if DB is unavailable.

    Features:
    - SHA256 query hashing for deterministic keys
    - TTL-based expiration with configurable duration
    - Reuse counting for cache efficiency metrics
    - Staleness cleanup
    - Graceful degradation (in-memory fallback)
    """

    def __init__(
        self,
        uow: AsyncUnitOfWork | UnitOfWork | None = None,
        default_ttl: int = DEFAULT_TTL_SECONDS,
        max_ttl: int = MAX_TTL_SECONDS,
    ):
        self._uow = uow
        self._default_ttl = default_ttl
        self._max_ttl = max_ttl
        self._fallback_store: dict[str, CacheEntry] = {}
        self._db_available = uow is not None

    @property
    def _db(self) -> AsyncSession | None:
        if self._uow is None:
            return None
        try:
            return self._uow.db
        except Exception:
            return None

    # ── Public API ────────────────────────────────────────────────

    async def get(
        self,
        query: str,
        depth: SearchDepth = SearchDepth.BASIC,
    ) -> TavilySearchResponse | None:
        """Retrieve cached result if available and not expired."""
        qhash = _hash_query(query, depth)

        # Try DB first
        if self._db_available:
            try:
                record = await self._query_db(qhash)
                if record is not None:
                    if _is_expired(record):
                        logger.debug("Cache expired for hash=%s", qhash[:12])
                        exporter.inc_counter("tavily_cache_expired")
                        return None

                    self._increment_reuse(record)
                    exporter.inc_counter("tavily_cache_hits")
                    logger.debug("Cache HIT for hash=%s (reuse=%d)", qhash[:12], record.reuse_count)

                    return _record_to_response(record)
            except Exception as e:
                logger.warning("Cache DB query failed, falling back: %s", e)
                exporter.inc_counter("tavily_cache_db_errors")

        # Fallback to in-memory store
        entry = self._fallback_store.get(qhash)
        if entry is not None:
            if entry.is_expired:
                del self._fallback_store[qhash]
                exporter.inc_counter("tavily_cache_expired")
                return None
            entry.reuse_count += 1
            exporter.inc_counter("tavily_cache_hits")
            logger.debug("Cache HIT (memory) for hash=%s", qhash[:12])
            return _entry_to_response(entry)

        exporter.inc_counter("tavily_cache_misses")
        return None

    async def set(
        self,
        query: str,
        response: TavilySearchResponse,
        depth: SearchDepth = SearchDepth.BASIC,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a search result in cache."""
        qhash = _hash_query(query, depth)
        actual_ttl = min(ttl_seconds or self._default_ttl, self._max_ttl)

        # DB store
        if self._db_available:
            try:
                await self._upsert_db(qhash, query, response, actual_ttl)
                logger.debug("Cache STORE for hash=%s ttl=%ds", qhash[:12], actual_ttl)
                return
            except Exception as e:
                logger.warning("Cache DB store failed, using memory fallback: %s", e)
                exporter.inc_counter("tavily_cache_store_errors")

        # Memory fallback
        entry = CacheEntry(
            query_hash=qhash,
            query=query,
            response_json=response.to_dict(),
            created_at=datetime.now(timezone.utc),
            ttl_seconds=actual_ttl,
            latency_ms=response.response_time_ms,
            source_count=response.source_count,
        )
        self._fallback_store[qhash] = entry
        if len(self._fallback_store) > 1000:
            self._evict_oldest()

    async def invalidate(self, query: str, depth: SearchDepth = SearchDepth.BASIC) -> None:
        """Remove a cached entry."""
        qhash = _hash_query(query, depth)
        if self._db_available:
            try:
                db = self._db
                if db is not None:
                    stmt = select(RetrievalCache).where(RetrievalCache.query_hash == qhash)
                    result = await db.execute(stmt)
                    record = result.scalar_one_or_none()
                    if record:
                        await db.delete(record)
                        if isinstance(self._uow, AsyncUnitOfWork):
                            await self._uow.flush()
            except Exception:
                pass
        self._fallback_store.pop(qhash, None)

    async def clear_expired(self, batch_size: int = 100) -> int:
        """Remove all expired entries. Returns count of removed records."""
        if not self._db_available:
            old_count = len(self._fallback_store)
            now = datetime.now(timezone.utc)
            self._fallback_store = {
                k: v for k, v in self._fallback_store.items() if not v.is_expired
            }
            return old_count - len(self._fallback_store)

        try:
            db = self._db
            if db is None:
                return 0

            stmt = (
                select(RetrievalCache)
                .where(RetrievalCache.expires_at <= datetime.now(timezone.utc))
                .limit(batch_size)
            )
            result = await db.execute(stmt)
            records = list(result.scalars().all())

            for r in records:
                await db.delete(r)

            if isinstance(self._uow, AsyncUnitOfWork):
                await self._uow.flush()

            count = len(records)
            if count > 0:
                logger.info("Cache cleanup: removed %d expired entries", count)
            return count
        except Exception as e:
            logger.warning("Cache cleanup failed: %s", e)
            return 0

    async def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        stats: dict[str, Any] = {
            "memory_entries": len(self._fallback_store),
            "default_ttl_seconds": self._default_ttl,
            "db_available": self._db_available,
        }

        if self._db_available:
            try:
                db = self._db
                if db is not None:
                    from sqlalchemy import func

                    stmt = select(
                        func.count(RetrievalCache.id),
                        func.coalesce(func.sum(RetrievalCache.reuse_count), 0),
                    )
                    result = await db.execute(stmt)
                    row = result.one()
                    stats["db_entries"] = row[0]
                    stats["total_reuses"] = row[1]
            except Exception:
                stats["db_entries"] = "error"

        return stats

    # ── Private DB helpers ─────────────────────────────────────────

    async def _query_db(self, qhash: str) -> RetrievalCache | None:
        db = self._db
        if db is None:
            return None
        stmt = select(RetrievalCache).where(RetrievalCache.query_hash == qhash)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def _upsert_db(
        self,
        qhash: str,
        query: str,
        response: TavilySearchResponse,
        ttl: int,
    ) -> None:
        db = self._db
        if db is None:
            return

        stmt = select(RetrievalCache).where(RetrievalCache.query_hash == qhash)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        expires_at = datetime.now(timezone.utc).replace(microsecond=0)
        from datetime import timedelta

        expires_at += timedelta(seconds=ttl)

        if existing:
            existing.response_json = response.to_dict()
            existing.expires_at = expires_at
            existing.ttl_seconds = ttl
            existing.latency_ms = response.response_time_ms
            existing.source_count = response.source_count
        else:
            record = RetrievalCache(
                query_hash=qhash,
                query=query,
                response_json=response.to_dict(),
                ttl_seconds=ttl,
                expires_at=expires_at,
                latency_ms=response.response_time_ms,
                source_count=response.source_count,
            )
            db.add(record)

        if isinstance(self._uow, AsyncUnitOfWork):
            await self._uow.flush()

    def _increment_reuse(self, record: RetrievalCache) -> None:
        import sqlalchemy as sa

        record.reuse_count = (record.reuse_count or 0) + 1

    def _evict_oldest(self) -> None:
        oldest_key = min(
            self._fallback_store,
            key=lambda k: self._fallback_store[k].created_at,
        )
        del self._fallback_store[oldest_key]


# ── Singleton ──────────────────────────────────────────────────────

_cache_instance: TavilyCache | None = None


def get_tavily_cache(
    uow: AsyncUnitOfWork | UnitOfWork | None = None,
) -> TavilyCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = TavilyCache(uow=uow)
    return _cache_instance


def _is_expired(record: RetrievalCache) -> bool:
    if record.expires_at is None:
        return False
    now = datetime.now(timezone.utc)
    expires = record.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return now > expires


def _record_to_response(record: RetrievalCache) -> TavilySearchResponse:
    data = record.response_json or {}
    results = []
    for item in data.get("top_sources", []):
        results.append(
            TavilySource(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
        )
    return TavilySearchResponse(
        query=data.get("query", record.query),
        results=results,
        answer=data.get("answer"),
        response_time_ms=float(record.latency_ms or 0),
    )


def _entry_to_response(entry: CacheEntry) -> TavilySearchResponse:
    data = entry.response_json
    results = []
    for item in data.get("top_sources", []):
        results.append(
            TavilySource(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                score=float(item.get("score", 0.0)),
            )
        )
    return TavilySearchResponse(
        query=entry.query,
        results=results,
        answer=data.get("answer"),
        response_time_ms=entry.latency_ms,
    )
