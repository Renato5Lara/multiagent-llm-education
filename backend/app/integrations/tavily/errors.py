"""Tavily integration errors — structured, typed, and chainable."""

from __future__ import annotations


class TavilyError(Exception):
    """Base error for all Tavily integration failures."""

    def __init__(self, message: str, original: Exception | None = None):
        self.original = original
        super().__init__(message)


class TavilyRateLimitError(TavilyError):
    """Rate limit exceeded (HTTP 429)."""

    def __init__(self, retry_after: int = 60, message: str | None = None):
        self.retry_after = retry_after
        super().__init__(message or f"Tavily rate limit exceeded. Retry after {retry_after}s.")


class TavilyTimeoutError(TavilyError):
    """Request timed out."""

    def __init__(self, timeout_seconds: float, message: str | None = None):
        self.timeout_seconds = timeout_seconds
        super().__init__(message or f"Tavily request timed out after {timeout_seconds}s.")


class TavilyAuthError(TavilyError):
    """Authentication failure (HTTP 401/403)."""

    def __init__(self, message: str | None = None):
        super().__init__(message or "Tavily authentication failed. Check API key.")


class TavilyAPIError(TavilyError):
    """Generic API error (HTTP 4xx/5xx)."""

    def __init__(self, status_code: int, body: str | None = None):
        self.status_code = status_code
        self.body = body
        super().__init__(f"Tavily API error: HTTP {status_code}. Body: {body[:200] if body else 'N/A'}")


class TavilyCacheError(TavilyError):
    """Cache layer failure (non-fatal, degrades gracefully)."""


class TavilyConfigurationError(TavilyError):
    """Configuration error (missing API key, invalid params)."""
