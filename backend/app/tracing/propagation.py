from __future__ import annotations

import logging
from typing import Any, Callable

from app.tracing.models import PropagationContext, Baggage

logger = logging.getLogger(__name__)

# ── Structured Logging Filter ────────────────────────────────────


class TraceLoggingFilter(logging.Filter):
    """Enriches log records with distributed tracing context.

    Adds trace_id, span_id, correlation_id, causation_id, and
    operation_name from the active PropagationContext to every
    log record. Safe to install on the root logger — fails
    gracefully (empty strings) when no context is active.

    Usage in main.py::

        root_logger = logging.getLogger()
        root_logger.addFilter(TraceLoggingFilter())
        logging.basicConfig(
            format="%(asctime)s | %(levelname)s | %(name)s "
                   "| [%(trace_id)s/%(span_id)s] %(message)s",
        )
    """

    def __init__(self, engine: Any | None = None) -> None:
        super().__init__()
        self._engine = engine

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            engine = self._engine
            if engine is None:
                from app.tracing import correlation_engine
                engine = correlation_engine
            ctx = engine.get_current()
            if ctx is not None:
                record.trace_id = ctx.span.trace_id
                record.span_id = ctx.span.span_id
                record.correlation_id = ctx.correlation.correlation_id
                record.causation_id = ctx.correlation.causation_id or ""
                record.operation_name = ctx.correlation.operation_name
            else:
                _set_empty_trace(record)
        except Exception:
            _set_empty_trace(record)
        return True


def _set_empty_trace(record: logging.LogRecord) -> None:
    record.trace_id = ""
    record.span_id = ""
    record.correlation_id = ""
    record.causation_id = ""
    record.operation_name = ""


def propagation_guard(
    max_span_depth: int = 64,
    max_baggage_bytes: int = 8192,
) -> Callable[[PropagationContext], PropagationContext | None]:
    def guard(ctx: PropagationContext) -> PropagationContext | None:
        depth = _compute_depth(ctx)
        if depth > max_span_depth:
            logger.warning(
                "span depth %d exceeds limit %d — dropping propagation",
                depth, max_span_depth,
            )
            return None

        baggage_size = _compute_baggage_bytes(ctx.baggage)
        if baggage_size > max_baggage_bytes:
            logger.warning(
                "baggage size %d bytes exceeds limit %d — truncating",
                baggage_size, max_baggage_bytes,
            )
            truncated = {}
            remaining = max_baggage_bytes
            for k, v in ctx.baggage.items.items():
                entry = f"{k}={v}".encode("utf-8")
                if len(entry) <= remaining:
                    truncated[k] = v
                    remaining -= len(entry)
            object.__setattr__(ctx, "baggage", Baggage(items=truncated))

        return ctx

    return guard


def _compute_depth(ctx: PropagationContext) -> int:
    depth = 0
    current = ctx.span.parent_span_id
    while current is not None:
        depth += 1
        if depth > 128:
            break
    return depth


def _compute_baggage_bytes(baggage: Baggage) -> int:
    return len(baggage.to_header().encode("utf-8"))


INBOUND_HEADERS = {
    "traceparent",
    "tracestate",
    "baggage",
    "x-trace-id",
    "x-correlation-id",
    "x-causation-id",
    "x-operation-name",
    "x-emitted-by",
}

OUTBOUND_HEADERS = {
    "traceparent",
    "tracestate",
    "baggage",
    "x-correlation-id",
    "x-causation-id",
    "x-operation-name",
    "x-emitted-by",
}


def sanitize_inbound_headers(headers: dict[str, str]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for k, v in headers.items():
        lk = k.lower()
        if lk in INBOUND_HEADERS:
            if lk == "traceparent":
                sanitized["traceparent"] = v
            elif lk == "tracestate":
                sanitized["tracestate"] = v
            elif lk == "baggage":
                sanitized["baggage"] = v
            elif lk == "x-trace-id":
                sanitized.setdefault("traceparent", v)
            elif lk == "x-correlation-id":
                sanitized["x-correlation-id"] = v
            elif lk == "x-causation-id":
                sanitized["x-causation-id"] = v
    return sanitized


def sanitize_outbound_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in OUTBOUND_HEADERS}
