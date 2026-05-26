"""
FastAPI middleware for automatic swarm diagnostics instrumentation.

Injects diagnostic events for every request, traces correlation IDs,
and records execution timing. Integrates with the existing tracing
infrastructure via TraceContext.
"""

from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.swarm_diagnostics import diagnostics_engine
from app.observability.tracing import get_current_trace, set_current_trace, TraceContext


class SwarmDiagnosticsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that auto-instruments every HTTP request.

    Usage in app/main.py:
        from app.swarm_diagnostics.middleware.fastapi import SwarmDiagnosticsMiddleware
        app.add_middleware(SwarmDiagnosticsMiddleware)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or trace_id

        trace_ctx = TraceContext(
            trace_id=trace_id,
            span_id=str(uuid.uuid4()),
            correlation_id=correlation_id,
            emitted_by=f"http:{request.method}:{request.url.path}",
        )
        set_current_trace(trace_ctx)

        start = time.monotonic()
        error: str | None = None

        try:
            response = await call_next(request)
            if response.status_code >= 400:
                error = f"HTTP {response.status_code}"
            return response
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            diagnostics_engine.make_event(
                event_type=f"http:{request.method}:{request.url.path}",
                correlation_id=correlation_id,
                trace_id=trace_id,
                scope=f"endpoint:{request.url.path}",
                source="fastapi",
                payload={
                    "method": request.method,
                    "path": str(request.url.path),
                    "status_code": getattr(response, "status_code", 0) if "response" in dir() else 0,
                },
                duration_ms=duration_ms,
                error=error,
            )


def instrument_app(app: FastAPI) -> None:
    """Add swarm diagnostics middleware and lifespan hooks to a FastAPI app."""
    app.add_middleware(SwarmDiagnosticsMiddleware)

    @app.on_event("shutdown")
    async def emit_shutdown_diagnostic():
        diagnostics_engine.make_event(
            event_type="app:shutdown",
            source="fastapi",
        )
