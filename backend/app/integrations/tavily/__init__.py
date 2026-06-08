"""Tavily-backed pedagogical retrieval tools."""

from app.integrations.tavily.cache import TavilyCache
from app.integrations.tavily.client import TavilyClient
from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import (
    AggregatedResearch,
    PedagogicalMetrics,
    QueryCategory,
    RetrievalContext,
    SearchDepth,
    TavilyQueryResult,
    TavilySearchResponse,
    TavilySource,
)

__all__ = [
    "AggregatedResearch",
    "PedagogicalMetrics",
    "PedagogicalRetrievalStrategy",
    "QueryCategory",
    "RetrievalContext",
    "SearchDepth",
    "TavilyCache",
    "TavilyClient",
    "TavilyQueryResult",
    "TavilySearchResponse",
    "TavilySource",
]
