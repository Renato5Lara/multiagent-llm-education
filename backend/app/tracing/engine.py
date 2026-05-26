from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from threading import Lock
from typing import Any

from app.tracing.models import (
    PropagationContext,
    SpanContext,
    CorrelationContext,
    Baggage,
    MAX_CAUSATION_DEPTH,
)

logger = logging.getLogger(__name__)

_current_ctx: ContextVar[dict | None] = ContextVar("_tracing_current_ctx", default=None)

CORRELATION_ID_HEADER = "X-Correlation-ID"
CAUSATION_ID_HEADER = "X-Causation-ID"
TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
BAGGAGE_HEADER = "baggage"
OPERATION_HEADER = "X-Operation-Name"
EMITTED_BY_HEADER = "X-Emitted-By"


class CorrelationEngine:
    def __init__(self) -> None:
        self._lock = Lock()
        self._span_count: int = 0
        self._max_spans: int = 10_000
        self._trace_start: dict[str, float] = {}

    # ── Context var access ──────────────────────────────────────

    def get_current(self) -> PropagationContext | None:
        raw = _current_ctx.get()
        if raw is None:
            return None
        return PropagationContext.from_dict(raw)

    def set_current(self, ctx: PropagationContext | None) -> None:
        _current_ctx.set(ctx.to_dict() if ctx else None)

    def decay(self) -> None:
        _current_ctx.set(None)

    # ── Span lifecycle ──────────────────────────────────────────

    def start(
        self,
        operation_name: str = "",
        emitted_by: str = "",
        correlation_id: str | None = None,
        causation_id: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> PropagationContext:
        span = SpanContext.new()
        correlation = CorrelationContext.new(
            operation_name=operation_name,
            emitted_by=emitted_by,
            correlation_id=correlation_id,
        )
        if causation_id:
            object.__setattr__(correlation, "causation_id", causation_id)

        ctx = PropagationContext(
            span=span,
            correlation=correlation,
            tags=tags or {},
        )
        self._trace_start[span.trace_id] = time.monotonic()
        self.set_current(ctx)
        with self._lock:
            self._span_count += 1
        return ctx

    def child(
        self,
        operation_name: str = "",
        causation_id: str | None = None,
        tags: dict[str, str] | None = None,
    ) -> PropagationContext:
        parent = self.get_current()
        if parent is None:
            return self.start(
                operation_name=operation_name,
                causation_id=causation_id,
                tags=tags,
            )

        if causation_id is None:
            causation_id = _next_causation_id(parent)

        ctx = parent.child_span(
            operation_name=operation_name or parent.correlation.operation_name,
            causation_id=causation_id,
        )
        if tags:
            for k, v in tags.items():
                ctx = ctx.with_tag(k, v)

        self.set_current(ctx)
        with self._lock:
            self._span_count += 1
        return ctx

    def end(self) -> PropagationContext | None:
        current = self.get_current()
        if current is None:
            return None

        causation_map: dict[str, str] = {}
        trace_id = current.span.trace_id
        duration = 0.0
        if trace_id in self._trace_start:
            duration = (time.monotonic() - self._trace_start.pop(trace_id)) * 1000

        if current.span.parent_span_id and trace_id in self._trace_start:
            pass

        self._emit_span_event(current, duration)

        if current.span.parent_span_id:
            parent_ctx = PropagationContext(
                span=SpanContext(
                    trace_id=current.span.trace_id,
                    span_id=current.span.parent_span_id,
                ),
                correlation=current.correlation,
                baggage=current.baggage,
            )
            self.set_current(parent_ctx)
            return parent_ctx

        self.decay()
        return None

    # ── Headers injection / extraction ──────────────────────────

    def extract_from_headers(self, headers: dict[str, str]) -> PropagationContext | None:
        traceparent = headers.get(TRACEPARENT_HEADER)
        span: SpanContext | None = None

        if traceparent:
            span = SpanContext.from_traceparent(traceparent)

        if span is None:
            raw_trace_id = headers.get("X-Trace-ID", str(uuid.uuid4()))
            cleaned = raw_trace_id.replace("-", "").lower()
            trace_id = cleaned[:32].ljust(32, "0")
            span = SpanContext(trace_id=trace_id, span_id=_new_span_id())

        correlation_id = headers.get(CORRELATION_ID_HEADER) or span.trace_id
        causation_id = headers.get(CAUSATION_ID_HEADER)
        operation_name = headers.get(OPERATION_HEADER, "")
        emitted_by = headers.get(EMITTED_BY_HEADER, "http:inbound")

        baggage_raw = headers.get(BAGGAGE_HEADER)
        baggage = Baggage.from_header(baggage_raw) if baggage_raw else Baggage()

        # Parse W3C tracestate: "vendor1=val1,vendor2=val2"
        tracestate_raw = headers.get(TRACESTATE_HEADER)
        tracestate: dict[str, str] = {}
        if tracestate_raw:
            for part in tracestate_raw.split(","):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    tracestate[k.strip()] = v.strip()

        ctx = PropagationContext(
            span=span,
            correlation=CorrelationContext(
                correlation_id=correlation_id,
                causation_id=causation_id,
                operation_name=operation_name,
                emitted_by=emitted_by,
            ),
            baggage=baggage,
            tracestate=tracestate,
        )
        self.set_current(ctx)
        return ctx

    def inject_into_headers(self, ctx: PropagationContext | None = None) -> dict[str, str]:
        if ctx is None:
            ctx = self.get_current()
        if ctx is None:
            return {}

        headers = {
            TRACEPARENT_HEADER: ctx.span.to_traceparent(),
            CORRELATION_ID_HEADER: ctx.correlation.correlation_id,
        }
        if ctx.correlation.causation_id:
            headers[CAUSATION_ID_HEADER] = ctx.correlation.causation_id
        if ctx.baggage.items:
            headers[BAGGAGE_HEADER] = ctx.baggage.to_header()
        if ctx.tracestate:
            headers[TRACESTATE_HEADER] = ",".join(
                f"{k}={v}" for k, v in ctx.tracestate.items()
            )
        return headers

    # ── Diagnostics bridge ──────────────────────────────────────

    def _emit_span_event(self, ctx: PropagationContext, duration_ms: float) -> None:
        try:
            from app.swarm_diagnostics import diagnostics_engine

            diagnostics_engine.make_event(
                event_type=f"tracing:span:{ctx.correlation.operation_name or 'op'}",
                correlation_id=ctx.correlation.correlation_id,
                causation_id=ctx.correlation.causation_id,
                trace_id=ctx.span.trace_id,
                scope=f"trace:{ctx.span.trace_id[:8]}",
                source=ctx.correlation.emitted_by or "correlation_engine",
                payload={
                    "span_id": ctx.span.span_id,
                    "parent_span_id": ctx.span.parent_span_id,
                    "operation_name": ctx.correlation.operation_name,
                    "duration_ms": round(duration_ms, 3),
                    "baggage": dict(ctx.baggage.items),
                    "tags": dict(ctx.tags),
                },
                duration_ms=duration_ms,
            )
        except Exception:
            logger.debug("diagnostics bridge unavailable", exc_info=True)

    def record_causation_chain(self, event_outbox_id: str, ctx: PropagationContext | None = None) -> None:
        if ctx is None:
            ctx = self.get_current()
        if ctx is None:
            return
        try:
            from app.swarm_diagnostics.pipeline.lineage import EventLineageTracker

            tracker = EventLineageTracker()
            depth = tracker.get_chain_depth(ctx.correlation.correlation_id)
            if depth > MAX_CAUSATION_DEPTH:
                logger.warning(
                    "causation chain depth %d exceeds limit %d for correlation=%s",
                    depth, MAX_CAUSATION_DEPTH, ctx.correlation.correlation_id,
                )
        except Exception:
            logger.debug("lineage tracker unavailable", exc_info=True)

    # ── Metrics ─────────────────────────────────────────────────

    @property
    def span_count(self) -> int:
        with self._lock:
            return self._span_count

    def reset_metrics(self) -> None:
        with self._lock:
            self._span_count = 0
            self._trace_start.clear()

    def __repr__(self) -> str:
        return f"<CorrelationEngine spans={self._span_count}>"


def _new_span_id() -> str:
    return uuid.uuid4().hex[:16]


def _next_causation_id(parent: PropagationContext) -> str:
    return str(uuid.uuid4())
