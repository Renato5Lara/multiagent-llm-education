from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

TRACEPARENT_VERSION = "00"
MAX_BAGGAGE_ITEMS = 64
MAX_BAGGAGE_VALUE_BYTES = 1024
MAX_TAGS = 128
MAX_CAUSATION_DEPTH = 100


@dataclass(frozen=True)
class SpanContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    trace_flags: str = "01"

    def __post_init__(self) -> None:
        _validate_hex(self.trace_id, 32, "trace_id")
        _validate_hex(self.span_id, 16, "span_id")
        if self.parent_span_id is not None:
            _validate_hex(self.parent_span_id, 16, "parent_span_id")

    @classmethod
    def new(cls) -> SpanContext:
        return cls(
            trace_id=_new_hex(32),
            span_id=_new_hex(16),
        )

    def child(self) -> SpanContext:
        return SpanContext(
            trace_id=self.trace_id,
            span_id=_new_hex(16),
            parent_span_id=self.span_id,
            trace_flags=self.trace_flags,
        )

    def to_traceparent(self) -> str:
        return f"{TRACEPARENT_VERSION}-{self.trace_id}-{self.span_id}-{self.trace_flags}"

    @classmethod
    def from_traceparent(cls, value: str) -> SpanContext | None:
        try:
            parts = value.strip().split("-")
            if len(parts) != 4:
                return None
            ver, tid, sid, flags = parts
            if ver != TRACEPARENT_VERSION:
                return None
            _validate_hex(tid, 32, "trace_id")
            _validate_hex(sid, 16, "span_id")
            _validate_hex(flags, 2, "trace_flags")
            return cls(trace_id=tid, span_id=sid, trace_flags=flags)
        except (ValueError, AssertionError):
            return None


@dataclass(frozen=True)
class CorrelationContext:
    correlation_id: str
    causation_id: str | None = None
    operation_name: str = ""
    emitted_by: str = ""

    @classmethod
    def new(
        cls,
        operation_name: str = "",
        emitted_by: str = "",
        correlation_id: str | None = None,
    ) -> CorrelationContext:
        return cls(
            correlation_id=correlation_id or str(uuid.uuid4()),
            operation_name=operation_name,
            emitted_by=emitted_by,
        )

    def child(self, operation_name: str = "", causation_id: str | None = None) -> CorrelationContext:
        return CorrelationContext(
            correlation_id=self.correlation_id,
            causation_id=causation_id or self.causation_id,
            operation_name=operation_name or self.operation_name,
            emitted_by=self.emitted_by,
        )


@dataclass
class Baggage:
    items: dict[str, str] = field(default_factory=dict)

    def set(self, key: str, value: str) -> None:
        if len(self.items) >= MAX_BAGGAGE_ITEMS:
            raise ValueError(f"baggage item limit {MAX_BAGGAGE_ITEMS} exceeded")
        encoded = value.encode("utf-8")
        if len(encoded) > MAX_BAGGAGE_VALUE_BYTES:
            raise ValueError(f"baggage value for '{key}' exceeds {MAX_BAGGAGE_VALUE_BYTES} bytes")
        self.items[key] = value

    def get(self, key: str, default: str | None = None) -> str | None:
        return self.items.get(key, default)

    def merge(self, other: Baggage) -> None:
        for k, v in other.items.items():
            self.set(k, v)

    def to_header(self) -> str:
        return ",".join(f"{k}={v}" for k, v in self.items.items())

    @classmethod
    def from_header(cls, value: str) -> Baggage:
        items: dict[str, str] = {}
        for part in value.split(","):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                items[k.strip()] = v.strip()
        return cls(items=items)


@dataclass
class PropagationContext:
    span: SpanContext
    correlation: CorrelationContext
    baggage: Baggage = field(default_factory=Baggage)
    tags: dict[str, str] = field(default_factory=dict)
    tracestate: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def child_span(self, operation_name: str = "", causation_id: str | None = None) -> PropagationContext:
        return PropagationContext(
            span=self.span.child(),
            correlation=self.correlation.child(
                operation_name=operation_name,
                causation_id=causation_id or self.correlation.causation_id,
            ),
            baggage=Baggage(items=dict(self.baggage.items)),
            tags=dict(self.tags),
            tracestate=dict(self.tracestate),
        )

    def with_tag(self, key: str, value: str) -> PropagationContext:
        if len(self.tags) >= MAX_TAGS:
            raise ValueError(f"tag limit {MAX_TAGS} exceeded")
        tags = dict(self.tags)
        tags[key] = value
        return PropagationContext(
            span=self.span,
            correlation=self.correlation,
            baggage=self.baggage,
            tags=tags,
            tracestate=dict(self.tracestate),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.span.trace_id,
            "span_id": self.span.span_id,
            "parent_span_id": self.span.parent_span_id,
            "trace_flags": self.span.trace_flags,
            "correlation_id": self.correlation.correlation_id,
            "causation_id": self.correlation.causation_id,
            "operation_name": self.correlation.operation_name,
            "emitted_by": self.correlation.emitted_by,
            "baggage": dict(self.baggage.items),
            "tags": dict(self.tags),
            "tracestate": dict(self.tracestate),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PropagationContext:
        return cls(
            span=SpanContext(
                trace_id=data["trace_id"],
                span_id=data["span_id"],
                parent_span_id=data.get("parent_span_id"),
                trace_flags=data.get("trace_flags", "01"),
            ),
            correlation=CorrelationContext(
                correlation_id=data.get("correlation_id", data["trace_id"]),
                causation_id=data.get("causation_id"),
                operation_name=data.get("operation_name", ""),
                emitted_by=data.get("emitted_by", ""),
            ),
            baggage=Baggage(items=data.get("baggage", {})),
            tags=data.get("tags", {}),
            tracestate=data.get("tracestate", {}),
        )

    def to_legacy_trace_context(self) -> Any:
        from app.observability.tracing import TraceContext
        return TraceContext(
            trace_id=self.span.trace_id,
            span_id=self.span.span_id,
            parent_span_id=self.span.parent_span_id,
            correlation_id=self.correlation.correlation_id,
            causation_id=self.correlation.causation_id,
            emitted_by=self.correlation.emitted_by,
        )


def _new_hex(length: int) -> str:
    return uuid.uuid4().hex[:length]


def _validate_hex(value: str, length: int, name: str) -> None:
    assert len(value) == length, f"{name} must be {length} hex chars, got {len(value)}"
    int(value, 16)
