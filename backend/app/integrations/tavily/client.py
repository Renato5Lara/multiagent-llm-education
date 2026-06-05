"""Async Tavily API client with degraded-mode support."""

from __future__ import annotations

import time
import logging

import httpx

from app.core.config import settings
from app.integrations.tavily.schemas import SearchDepth, TavilySearchResponse

logger = logging.getLogger(__name__)


class TavilyClient:
    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 12.0,
    ):
        self.api_key = api_key if api_key is not None else settings.TAVILY_API_KEY
        self.timeout_seconds = timeout_seconds

    @property
    def degraded(self) -> bool:
        """True when no API key is available — all searches will be empty."""
        return not bool(self.api_key and self.api_key.strip())

    async def search(
        self,
        query: str,
        *,
        max_results: int = 3,
        search_depth: SearchDepth = SearchDepth.BASIC,
        include_answer: bool = True,
    ) -> TavilySearchResponse:
        if self.degraded:
            logger.debug("TavilyClient degraded — returning empty result for query=%r", query[:80])
            return TavilySearchResponse(
                query=query,
                results=[],
                answer="",
                response_time_ms=0.0,
            )

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth.value if isinstance(search_depth, SearchDepth) else str(search_depth),
            "include_answer": include_answer,
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()
        elapsed_ms = (time.perf_counter() - started) * 1000
        if not isinstance(data, dict):
            data = {}
        return TavilySearchResponse.from_mapping(data, query=query, response_time_ms=elapsed_ms)
