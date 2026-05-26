"""
Tracing Context — lightweight distributed trace propagation.

Provides:
    - TraceContext: immutable context with trace_id, span_id, parent_span_id
    - TracingSpan: measures operation duration with structured metadata
    - Context var propagation for async safety
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_current_trace: ContextVar[dict | None] = ContextVar("_current_trace", default=None)


def new_trace_id() -> str:
    return str(uuid.uuid4())


def new_span_id() -> str:
    return str(uuid.uuid4())[:8]


@dataclass
class TraceContext:
    """Immutable context for distributed tracing.

    Carries the minimal set of identifiers needed to reconstruct
    the full causality chain of an operation.
    """

    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    emitted_by: str | None = None

    @classmethod
    def new(
        cls,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        emitted_by: str | None = None,
    ) -> TraceContext:
        """Create a new root trace context."""
        tid = new_trace_id()
        return cls(
            trace_id=tid,
            span_id=new_span_id(),
            correlation_id=correlation_id or tid,
            causation_id=causation_id,
            emitted_by=emitted_by,
        )

    def child(self, operation: str) -> TraceContext:
        """Create a child span context."""
        return TraceContext(
            trace_id=self.trace_id,
            span_id=new_span_id(),
            parent_span_id=self.span_id,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
            emitted_by=operation,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "emitted_by": self.emitted_by,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TraceContext:
        return cls(
            trace_id=data["trace_id"],
            span_id=data["span_id"],
            parent_span_id=data.get("parent_span_id"),
            correlation_id=data.get("correlation_id"),
            causation_id=data.get("causation_id"),
            emitted_by=data.get("emitted_by"),
        )


class TracingSpan:
    """Measures duration and carries metadata for a traced operation.

    Usage:
        trace_ctx = TraceContext.new(emitted_by="my_service")
        with TracingSpan(trace_ctx, "my_operation") as span:
            do_work()
        print(span.duration_ms)
    """

    def __init__(self, trace_ctx: TraceContext, operation: str):
        self.trace_ctx = trace_ctx
        self.operation = operation
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        self.start_ns: int | None = None
        self.duration_ms: float | None = None
        self.tags: dict[str, Any] = {}

    def start(self) -> None:
        self.start_time = datetime.now(timezone.utc)
        self.start_ns = time.monotonic_ns()
        _current_trace.set(self.trace_ctx.to_dict())

    def finish(self) -> None:
        self.end_time = datetime.now(timezone.utc)
        if self.start_ns is not None:
            self.duration_ms = (time.monotonic_ns() - self.start_ns) / 1_000_000

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "span_id": self.trace_ctx.span_id,
            "parent_span_id": self.trace_ctx.parent_span_id,
            "trace_id": self.trace_ctx.trace_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": round(self.duration_ms, 3) if self.duration_ms is not None else None,
            "tags": self.tags,
        }

    def set_tag(self, key: str, value: Any) -> None:
        self.tags[key] = value

    def log_structured(self) -> None:
        logger.info(
            "Span[%s:%s] op=%s parent=%s duration=%.2fms tags=%s",
            self.trace_ctx.trace_id[:8],
            self.trace_ctx.span_id,
            self.operation,
            self.trace_ctx.parent_span_id or "root",
            self.duration_ms or 0.0,
            self.tags,
        )

    def __enter__(self) -> TracingSpan:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.finish()
        self.log_structured()


def get_current_trace() -> dict | None:
    return _current_trace.get()


def set_current_trace(trace: dict | None) -> None:
    _current_trace.set(trace)


def trace_decay() -> None:
    """Clear the current trace from context."""
    _current_trace.set(None)
