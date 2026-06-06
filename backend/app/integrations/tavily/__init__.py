"""Tavily Search API integration for pedagogical retrieval."""

from app.integrations.tavily.client import TavilyClient
from app.integrations.tavily.cache import TavilyCache
from app.integrations.tavily.rate_limit import TavilyRateLimiter, TavilyCircuitBreaker
from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import (
    TavilyQueryResult,
    TavilySearchResponse,
    TavilySource,
    RetrievalContext,
    AggregatedResearch,
)
from app.integrations.tavily.errors import (
    TavilyError,
    TavilyRateLimitError,
    TavilyTimeoutError,
    TavilyAuthError,
    TavilyAPIError,
)

__all__ = [
    "TavilyClient",
    "TavilyCache",
    "TavilyRateLimiter",
    "TavilyCircuitBreaker",
    "PedagogicalRetrievalStrategy",
    "TavilyQueryResult",
    "TavilySearchResponse",
    "TavilySource",
    "RetrievalContext",
    "AggregatedResearch",
    "TavilyError",
    "TavilyRateLimitError",
    "TavilyTimeoutError",
    "TavilyAuthError",
    "TavilyAPIError",
]
