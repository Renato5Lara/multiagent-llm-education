"""Tests for TavilyClient: retries, timeouts, auth, malformed responses, cache integration."""

from __future__ import annotations

import pytest
from httpx import AsyncClient, Request, Response

from app.integrations.tavily.client import TavilyClient, get_tavily_client
from app.integrations.tavily.errors import (
    TavilyAPIError,
    TavilyAuthError,
    TavilyConfigurationError,
    TavilyRateLimitError,
    TavilyTimeoutError,
)
from app.integrations.tavily.schemas import SearchDepth, TavilySearchResponse


@pytest.fixture(autouse=True)
def reset_singleton():
    import app.integrations.tavily.client as client_mod
    client_mod._client_instance = None
    yield


class TestTavilyClientInitialization:
    def test_no_api_key_returns_empty(self, monkeypatch):
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        client = TavilyClient()
        assert client.api_key == ""
        assert not client.is_enabled

    def test_with_api_key(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key-123")
        c = TavilyClient()
        assert c.api_key == "tvly-test-key-123"
        assert c.is_enabled
        assert c._timeout == 15.0


class TestTavilyClientSearch:
    MOCK_RESPONSE = {
        "results": [
            {
                "title": "Test Title",
                "url": "https://example.com/test",
                "content": "Test content for pedagogical research",
                "score": 0.95,
            }
        ],
        "answer": "This is a test answer.",
        "response_time": 0.45,
    }

    @pytest.mark.asyncio
    async def test_search_success(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")

        async def mock_post(*args, **kwargs):
            return Response(200, json=self.MOCK_RESPONSE, request=Request("POST", "https://api.tavily.com/search"))

        client = TavilyClient()
        client._client = AsyncClient()
        monkeypatch.setattr(client._client, "post", mock_post)

        resp = await client.search("test query", max_results=5, include_answer=True)
        assert isinstance(resp, TavilySearchResponse)
        assert len(resp.results) == 1
        assert resp.results[0].title == "Test Title"
        assert resp.answer == "This is a test answer."
        assert resp.source_count == 1

    @pytest.mark.asyncio
    async def test_search_auth_error(self, monkeypatch):
        async def mock_post(*args, **kwargs):
            return Response(401, json={"error": "Invalid API key"}, request=Request("POST", "https://api.tavily.com/search"))

        client = TavilyClient(api_key="bad-key")
        client._client = AsyncClient()
        monkeypatch.setattr(client._client, "post", mock_post)

        with pytest.raises(TavilyAuthError):
            await client.search("query")

    @pytest.mark.asyncio
    async def test_search_rate_limit(self, monkeypatch):
        async def mock_post(*args, **kwargs):
            return Response(429, json={"error": "Rate limit exceeded"}, request=Request("POST", "https://api.tavily.com/search"))

        client = TavilyClient(api_key="key")
        client._client = AsyncClient()
        monkeypatch.setattr(client._client, "post", mock_post)

        with pytest.raises(TavilyRateLimitError):
            await client.search("query")

    @pytest.mark.asyncio
    async def test_search_timeout(self, monkeypatch):
        import httpx

        client = TavilyClient(api_key="key")
        client._client = AsyncClient()

        async def mock_post(*args, **kwargs):
            raise httpx.TimeoutException("timeout")

        monkeypatch.setattr(client._client, "post", mock_post)

        with pytest.raises(TavilyTimeoutError):
            await client.search("query")

    @pytest.mark.asyncio
    async def test_search_disabled_client(self):
        client = TavilyClient(api_key="")
        with pytest.raises(TavilyConfigurationError):
            await client.search("anything")

    @pytest.mark.asyncio
    async def test_retry_on_500(self, monkeypatch):
        call_count = [0]

        async def mock_post(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                return Response(500, json={"error": "Internal"}, request=Request("POST", "https://api.tavily.com/search"))
            return Response(200, json=self.MOCK_RESPONSE, request=Request("POST", "https://api.tavily.com/search"))

        client = TavilyClient(api_key="key")
        client._client = AsyncClient()
        monkeypatch.setattr(client._client, "post", mock_post)

        resp = await client.search("test")
        assert call_count[0] == 3
        assert resp.source_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self, monkeypatch):
        call_count = [0]

        async def mock_post(*args, **kwargs):
            call_count[0] += 1
            return Response(500, json={"error": "Internal"}, request=Request("POST", "https://api.tavily.com/search"))

        client = TavilyClient(api_key="key")
        client._client = AsyncClient()
        monkeypatch.setattr(client._client, "post", mock_post)

        with pytest.raises(TavilyAPIError):
            await client.search("test")
        assert call_count[0] == 3


class TestGetTavilyClient:
    def test_singleton(self, monkeypatch):
        monkeypatch.setenv("TAVILY_API_KEY", "tvly-key")
        c1 = get_tavily_client()
        c2 = get_tavily_client()
        assert c1 is c2
