"""Tests for observability: tracing."""

import time

from app.observability.tracing import (
    TraceContext,
    TracingSpan,
    get_current_trace,
    set_current_trace,
    trace_decay,
    new_trace_id,
    new_span_id,
)


# =============================================================================
# 1. TraceContext
# =============================================================================


class TestTraceContext:
    def test_new_creates_root_context(self):
        ctx = TraceContext.new()
        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert ctx.parent_span_id is None
        assert ctx.causation_id is None

    def test_new_with_correlation(self):
        ctx = TraceContext.new(correlation_id="my-corr", emitted_by="test")
        assert ctx.correlation_id == "my-corr"
        assert ctx.emitted_by == "test"

    def test_child_inherits_trace_and_correlation(self):
        parent = TraceContext.new(correlation_id="root-corr")
        child = parent.child("child-op")
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.correlation_id == parent.correlation_id
        assert child.span_id != parent.span_id
        assert child.emitted_by == "child-op"

    def test_to_dict_roundtrip(self):
        original = TraceContext.new(
            correlation_id="corr", causation_id="caus", emitted_by="svc",
        )
        data = original.to_dict()
        restored = TraceContext.from_dict(data)
        assert restored.trace_id == original.trace_id
        assert restored.span_id == original.span_id
        assert restored.parent_span_id == original.parent_span_id
        assert restored.correlation_id == original.correlation_id
        assert restored.causation_id == original.causation_id
        assert restored.emitted_by == original.emitted_by

    def test_unique_ids(self):
        ids = [new_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100

        spans = [new_span_id() for _ in range(100)]
        assert len(set(spans)) == 100


# =============================================================================
# 2. TracingSpan
# =============================================================================


class TestTracingSpan:
    def test_span_timing(self):
        ctx = TraceContext.new()
        span = TracingSpan(ctx, "test_op")
        span.start()
        time.sleep(0.01)
        span.finish()

        assert span.start_time is not None
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 8.0  # at least 8ms

    def test_span_context_manager(self):
        ctx = TraceContext.new()
        with TracingSpan(ctx, "cm_op") as span:
            span.set_tag("key", "value")

        assert span.duration_ms is not None
        assert span.tags["key"] == "value"

    def test_span_to_dict(self):
        ctx = TraceContext.new()
        with TracingSpan(ctx, "dict_op") as span:
            pass

        d = span.to_dict()
        assert d["operation"] == "dict_op"
        assert d["trace_id"] == ctx.trace_id
        assert d["span_id"] == ctx.span_id
        assert d["duration_ms"] is not None

    def test_context_var_propagation(self):
        trace_decay()
        assert get_current_trace() is None

        ctx = TraceContext.new()
        with TracingSpan(ctx, "prop_test") as span:
            current = get_current_trace()
            assert current is not None
            assert current["trace_id"] == ctx.trace_id
            assert current["span_id"] == ctx.span_id

        # After span exits, context var is still set (from last span)
        # That's fine — the span doesn't clean it up automatically

    def test_set_current_trace(self):
        ctx = TraceContext.new()
        set_current_trace(ctx.to_dict())
        assert get_current_trace()["trace_id"] == ctx.trace_id
        trace_decay()
        assert get_current_trace() is None

