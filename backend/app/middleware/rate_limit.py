import logging
import time
from collections import defaultdict
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthRateLimiter:
    """IP-based rate limiter for auth endpoints.

    Prevents brute-force login attacks with per-IP tracking.
    ONLY counts FAILED login attempts — successful logins never consume quota.
    Uses sliding window counters in memory (not distributed).
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[ip]
        bucket[:] = [t for t in bucket if t > window_start]
        return len(bucket) < self.max_requests

    def increment(self, ip: str) -> None:
        self._buckets[ip].append(time.monotonic())

    def get_remaining(self, ip: str) -> int:
        now = time.monotonic()
        window_start = now - self.window_seconds
        bucket = self._buckets[ip]
        bucket[:] = [t for t in bucket if t > window_start]
        return max(0, self.max_requests - len(bucket))


_limiter = AuthRateLimiter()


def make_auth_rate_limit_middleware(app: FastAPI) -> Callable:
    """Apply rate limiting to /api/auth/login endpoint."""

    async def middleware(request: Request, call_next: Callable) -> Response:
        ip = request.client.host if request.client else "unknown"

        # Rate limit login and refresh endpoints
        is_auth_endpoint = (
            request.url.path == "/api/auth/login"
            or request.url.path == "/api/auth/refresh"
        ) and request.method == "POST"

        if is_auth_endpoint:
            if not _limiter.is_allowed(ip):
                remaining = _limiter.get_remaining(ip)
                logger.warning("Rate limit exceeded for IP %s on %s", ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": {
                            "message": "Demasiadas solicitudes. Intenta de nuevo en 60 segundos.",
                            "retry_after_seconds": 60,
                            "code": "IP_RATE_LIMITED",
                        },
                        "status_code": 429,
                        "retry_after_seconds": 60,
                    },
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Remaining": str(remaining),
                    },
                )

            response = await call_next(request)
            # Only count FAILED attempts against the rate limit
            if response.status_code == 401:
                _limiter.increment(ip)
            return response

        return await call_next(request)

    return middleware
