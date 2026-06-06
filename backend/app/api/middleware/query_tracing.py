"""
Per-request query tracing middleware.

Attaches to the global QueryCounter and captures query count + N+1
warnings for every request. Emits structured logs and attaches
X-Query-Count and X-N1-Warnings headers to responses.
"""

import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.query_counter import get_global_counter, get_n1_warnings

logger = logging.getLogger("query_tracing")


class QueryTracingMiddleware(BaseHTTPMiddleware):
    """Middleware that measures SQL query count per request.

    Must be installed AFTER the DB session middleware in the middleware stack.
    """

    async def dispatch(self, request: Request, call_next):
        counter = get_global_counter()
        if counter:
            counter.start()

        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)

        if counter:
            counter.stop()
            query_count = counter.count
            n1_warnings = get_n1_warnings()

            response.headers["X-Query-Count"] = str(query_count)
            if n1_warnings:
                response.headers["X-N1-Warnings"] = "; ".join(n1_warnings[:3])
                for warn in n1_warnings:
                    logger.warning(
                        "[QUERY TRACING] %s | path=%s duration=%sms queries=%d",
                        warn,
                        request.url.path,
                        duration,
                        query_count,
                    )

            if query_count > 20:
                logger.info(
                    "High query count: %d | path=%s duration=%sms",
                    query_count,
                    request.url.path,
                    duration,
                )

            logger.info(
                "Query metrics | path=%s method=%s status=%d queries=%d duration=%sms",
                request.url.path,
                request.method,
                response.status_code,
                query_count,
                duration,
            )
        return response
