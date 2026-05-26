from __future__ import annotations

import logging
import time
from typing import Any, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.tracing.engine import CorrelationEngine

logger = logging.getLogger(__name__)


def make_tracing_middleware(engine: CorrelationEngine) -> Callable:
    """Factory that returns an @app.middleware('http') compatible function."""
    async def tracing_middleware(request: Request, call_next: Callable) -> Response:
        ctx = engine.extract_from_headers(dict(request.headers))
        if ctx is None:
            ctx = engine.start(
                operation_name=f"{request.method} {request.url.path}",
                emitted_by="fastapi",
            )

        # Inject swarm-specific tracestate vendor entries
        if "swarm" not in ctx.tracestate:
            ctx.tracestate["swarm"] = "fastapi"
        if "swarm_trace_id" not in ctx.tracestate:
            ctx.tracestate["swarm_trace_id"] = ctx.span.trace_id[:16]

        ctx = ctx.with_tag("http.method", request.method)
        ctx = ctx.with_tag("http.path", str(request.url.path))
        if hasattr(request.state, "request_id"):
            ctx = ctx.with_tag("request_id", request.state.request_id)
        engine.set_current(ctx)

        start_ns = time.monotonic_ns()
        error: str | None = None
        response: Response | None = None

        try:
            response = await call_next(request)
            if response.status_code >= 400:
                error = f"HTTP {response.status_code}"
            return response
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = (time.monotonic_ns() - start_ns) / 1_000_000
            if ctx:
                tagged = ctx.with_tag("http.duration_ms", f"{duration_ms:.3f}")
                if error:
                    tagged = tagged.with_tag("http.error", error)
                if response is not None:
                    tagged = tagged.with_tag("http.status_code", str(response.status_code))
                engine.set_current(tagged)

            _emit_request_event(ctx, duration_ms, error, response)

            if ctx and response is not None:
                headers = engine.inject_into_headers(ctx)
                for k, v in headers.items():
                    response.headers[k] = v

            engine.end()

    return tracing_middleware


def _emit_request_event(
    ctx: Any,
    duration_ms: float,
    error: str | None,
    response: Response | None,
) -> None:
    try:
        from app.swarm_diagnostics import diagnostics_engine

        diagnostics_engine.make_event(
            event_type=f"http:{'error' if error else 'ok'}",
            correlation_id=ctx.correlation.correlation_id if ctx else None,
            causation_id=ctx.correlation.causation_id if ctx else None,
            trace_id=ctx.span.trace_id if ctx else None,
            scope="fastapi",
            source="fastapi",
            payload={
                "method": ctx.tags.get("http.method", "") if ctx else "",
                "path": ctx.tags.get("http.path", "") if ctx else "",
                "status_code": response.status_code if response else 0,
                "span_id": ctx.span.span_id if ctx else "",
            },
            duration_ms=duration_ms,
            error=error,
        )
    except Exception:
        logger.debug("diagnostics engine unavailable", exc_info=True)


def instrument_app(
    app: FastAPI,
    engine: CorrelationEngine | None = None,
    *,
    enable_middleware: bool = True,
) -> CorrelationEngine:
    if engine is None:
        from app.tracing import correlation_engine
        engine = correlation_engine

    if enable_middleware:
        app.middleware("http")(make_tracing_middleware(engine))

    @app.on_event("shutdown")
    async def emit_shutdown_event() -> None:
        try:
            from app.swarm_diagnostics import diagnostics_engine
            diagnostics_engine.make_event(
                event_type="app:shutdown",
                source="fastapi",
                trace_id=None,
            )
        except Exception:
            pass

    return engine
