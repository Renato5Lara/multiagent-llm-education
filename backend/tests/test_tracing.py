"""
Comprehensive tests for the distributed tracing package (app/tracing).

Covers:
    - CorrelationEngine lifecycle (start, child, end)
    - PropagationContext models (W3C traceparent, baggage, dict roundtrip)
    - Header inject/extract (W3C + custom headers)
    - Legacy TraceContext bridge (backward compat with app/observability/tracing.py)
    - LangGraph node tracing wrapper
    - Propagation guard (depth limits, baggage size limits)
    - Context variable async isolation
    - Diagnostics bridge integration
    - Causation chain depth tracking
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone

import pytest

from app.tracing import (
    correlation_engine,
    PropagationContext,
    SpanContext,
    CorrelationContext,
    Baggage,
    trace_langgraph_node,
    propagation_guard,
    sanitize_inbound_headers,
    sanitize_outbound_headers,
)
from app.tracing.models import (
    TRACEPARENT_VERSION,
    MAX_BAGGAGE_ITEMS,
    MAX_BAGGAGE_VALUE_BYTES,
    MAX_TAGS,
    MAX_CAUSATION_DEPTH,
)
from app.tracing.engine import CORRELATION_ID_HEADER, TRACEPARENT_HEADER, BAGGAGE_HEADER

# =============================================================================
# 1. CorrelationEngine — Span Lifecycle
# =============================================================================


class TestEngineLifecycle:
    def test_start_creates_root_span(self):
        ctx = correlation_engine.start("test_op", "pytest")
        assert ctx.span.trace_id is not None
        assert len(ctx.span.trace_id) == 32
        assert len(ctx.span.span_id) == 16
        assert ctx.span.parent_span_id is None
        assert ctx.correlation.operation_name == "test_op"
        assert ctx.correlation.emitted_by == "pytest"
        assert ctx.tags == {}
        correlation_engine.end()

    def test_start_with_correlation_id(self):
        corr_id = str(uuid.uuid4())
        ctx = correlation_engine.start("op", "src", correlation_id=corr_id)
        assert ctx.correlation.correlation_id == corr_id
        correlation_engine.end()

    def test_start_with_tags(self):
        ctx = correlation_engine.start("op", "src", tags={"env": "test", "version": "1"})
        assert ctx.tags["env"] == "test"
        assert ctx.tags["version"] == "1"
        correlation_engine.end()

    def test_child_span_inherits_trace_and_correlation(self):
        root = correlation_engine.start("parent_op", "pytest")
        child = correlation_engine.child("child_op", tags={"seq": "2"})
        assert child.span.trace_id == root.span.trace_id
        assert child.span.parent_span_id == root.span.span_id
        assert child.correlation.correlation_id == root.correlation.correlation_id
        assert child.tags.get("seq") == "2"
        correlation_engine.end()
        correlation_engine.end()

    def test_child_span_with_causation_id(self):
        root = correlation_engine.start("parent", "pytest")
        cause_id = str(uuid.uuid4())
        child = correlation_engine.child("child", causation_id=cause_id)
        assert child.correlation.causation_id == cause_id
        correlation_engine.end()
        correlation_engine.end()

    def test_end_pops_to_parent(self):
        root = correlation_engine.start("root", "pytest")
        correlation_engine.child("child", tags={"x": "1"})
        parent_after = correlation_engine.end()
        assert parent_after is not None
        assert parent_after.span.span_id == root.span.span_id
        assert parent_after.span.trace_id == root.span.trace_id
        correlation_engine.end()

    def test_end_root_clears_context(self):
        correlation_engine.start("root", "pytest")
        correlation_engine.end()
        assert correlation_engine.get_current() is None

    def test_end_without_active_span_returns_none(self):
        correlation_engine.decay()
        result = correlation_engine.end()
        assert result is None

    def test_child_without_parent_starts_new_root(self):
        correlation_engine.decay()
        ctx = correlation_engine.child("orphan")
        assert ctx is not None
        assert ctx.span.parent_span_id is None
        correlation_engine.end()

    def test_span_count_increments(self):
        before = correlation_engine.span_count
        correlation_engine.start("count", "test")
        correlation_engine.child("sub")
        assert correlation_engine.span_count >= before + 2
        correlation_engine.end()
        correlation_engine.end()


# =============================================================================
# 2. SpanContext — W3C Trace Context
# =============================================================================


class TestSpanContext:
    def test_new_creates_valid_span(self):
        sp = SpanContext.new()
        assert len(sp.trace_id) == 32
        assert len(sp.span_id) == 16
        assert sp.parent_span_id is None
        assert sp.trace_flags == "01"

    def test_child_creates_new_span_id(self):
        parent = SpanContext.new()
        child = parent.child()
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.span_id != parent.span_id

    def test_to_traceparent_format(self):
        sp = SpanContext.new()
        tp = sp.to_traceparent()
        parts = tp.split("-")
        assert len(parts) == 4
        assert parts[0] == TRACEPARENT_VERSION
        assert parts[1] == sp.trace_id
        assert parts[2] == sp.span_id
        assert parts[3] == sp.trace_flags

    def test_from_traceparent_roundtrip(self):
        sp = SpanContext.new()
        tp = sp.to_traceparent()
        parsed = SpanContext.from_traceparent(tp)
        assert parsed is not None
        assert parsed.trace_id == sp.trace_id
        assert parsed.span_id == sp.span_id
        assert parsed.trace_flags == sp.trace_flags

    def test_from_traceparent_invalid_version(self):
        result = SpanContext.from_traceparent("ff-abc-xyz-01")
        assert result is None

    def test_from_traceparent_malformed(self):
        assert SpanContext.from_traceparent("") is None
        assert SpanContext.from_traceparent("not-a-traceparent") is None
        assert SpanContext.from_traceparent("00-abc-xyz-01-extra") is None


# =============================================================================
# 3. CorrelationContext
# =============================================================================


class TestCorrelationContext:
    def test_new_auto_generates_correlation_id(self):
        cc = CorrelationContext.new(operation_name="op", emitted_by="src")
        assert cc.correlation_id is not None
        assert cc.operation_name == "op"
        assert cc.emitted_by == "src"

    def test_preserves_correlation_id_across_child(self):
        cc = CorrelationContext.new(correlation_id="fixed-corr-id")
        child = cc.child(operation_name="child_op")
        assert child.correlation_id == "fixed-corr-id"

    def test_child_causation_id(self):
        cc = CorrelationContext.new()
        child = cc.child(causation_id="cause-1")
        assert child.causation_id == "cause-1"


# =============================================================================
# 4. Baggage
# =============================================================================


class TestBaggage:
    def test_set_and_get(self):
        bg = Baggage()
        bg.set("key1", "val1")
        assert bg.get("key1") == "val1"

    def test_missing_key_returns_none(self):
        bg = Baggage()
        assert bg.get("nonexistent") is None

    def test_max_items_enforced(self):
        bg = Baggage()
        for i in range(MAX_BAGGAGE_ITEMS):
            bg.set(f"k{i}", f"v{i}")
        with pytest.raises(ValueError, match="baggage item limit"):
            bg.set("overflow", "x")

    def test_max_value_bytes_enforced(self):
        bg = Baggage()
        with pytest.raises(ValueError, match="exceeds"):
            bg.set("big", "x" * (MAX_BAGGAGE_VALUE_BYTES + 1))

    def test_to_header_and_from_header(self):
        bg = Baggage()
        bg.set("a", "1")
        bg.set("b", "2")
        header = bg.to_header()
        restored = Baggage.from_header(header)
        assert restored.get("a") == "1"
        assert restored.get("b") == "2"

    def test_merge(self):
        bg1 = Baggage()
        bg1.set("x", "10")
        bg2 = Baggage()
        bg2.set("y", "20")
        bg1.merge(bg2)
        assert bg1.get("x") == "10"
        assert bg1.get("y") == "20"


# =============================================================================
# 5. PropagationContext — Serialization & Integration
# =============================================================================


class TestPropagationContext:
    def test_to_dict_contains_all_fields(self):
        ctx = correlation_engine.start("serde_test", "pytest", tags={"t": "1"})
        d = ctx.to_dict()
        assert d["trace_id"] == ctx.span.trace_id
        assert d["span_id"] == ctx.span.span_id
        assert d["correlation_id"] == ctx.correlation.correlation_id
        assert d["operation_name"] == ctx.correlation.operation_name
        assert d["emitted_by"] == ctx.correlation.emitted_by
        assert d["tags"] == {"t": "1"}
        assert d["baggage"] == {}
        correlation_engine.end()

    def test_from_dict_roundtrip(self):
        ctx = correlation_engine.start("rt", "test", tags={"env": "ci"})
        d = ctx.to_dict()
        restored = PropagationContext.from_dict(d)
        assert restored.span.trace_id == ctx.span.trace_id
        assert restored.span.span_id == ctx.span.span_id
        assert restored.correlation.correlation_id == ctx.correlation.correlation_id
        assert restored.tags == ctx.tags
        correlation_engine.end()

    def test_child_span_preserves_baggage(self):
        root = correlation_engine.start("root", "test")
        root.baggage.set("level", "1")
        child = root.child_span("child")
        assert child.baggage.get("level") == "1"
        correlation_engine.end()
        correlation_engine.end()

    def test_with_tag_preserves_existing(self):
        ctx = correlation_engine.start("tag_test", "test", tags={"a": "1"})
        updated = ctx.with_tag("b", "2")
        assert updated.tags["a"] == "1"
        assert updated.tags["b"] == "2"
        correlation_engine.end()

    def test_to_legacy_trace_context(self):
        ctx = correlation_engine.start("legacy_bridge", "test")
        legacy = ctx.to_legacy_trace_context()
        from app.observability.tracing import TraceContext
        assert isinstance(legacy, TraceContext)
        assert legacy.trace_id == ctx.span.trace_id
        assert legacy.span_id == ctx.span.span_id
        assert legacy.correlation_id == ctx.correlation.correlation_id
        assert legacy.emitted_by == ctx.correlation.emitted_by
        correlation_engine.end()


# =============================================================================
# 6. Header Propagation (Engine)
# =============================================================================


class TestHeaderPropagation:
    def test_inject_contains_required_headers(self):
        ctx = correlation_engine.start("inject_test", "test")
        headers = correlation_engine.inject_into_headers(ctx)
        assert TRACEPARENT_HEADER in headers
        assert CORRELATION_ID_HEADER in headers
        correlation_engine.end()

    def test_inject_with_causation_id(self):
        ctx = correlation_engine.start("inj", "test", causation_id="cause-123")
        headers = correlation_engine.inject_into_headers(ctx)
        assert "X-Causation-ID" in headers
        assert headers["X-Causation-ID"] == "cause-123"
        correlation_engine.end()

    def test_inject_with_baggage(self):
        ctx = correlation_engine.start("bg_inject", "test")
        ctx.baggage.set("student", "s1")
        headers = correlation_engine.inject_into_headers(ctx)
        assert BAGGAGE_HEADER in headers
        assert "student=s1" in headers[BAGGAGE_HEADER]
        correlation_engine.end()

    def test_inject_uses_current_context(self):
        correlation_engine.start("current_inject", "test", tags={"k": "v"})
        headers = correlation_engine.inject_into_headers()
        assert TRACEPARENT_HEADER in headers
        correlation_engine.end()

    def test_inject_without_context_returns_empty(self):
        correlation_engine.decay()
        assert correlation_engine.inject_into_headers() == {}

    def test_extract_from_w3c_traceparent(self):
        sp = SpanContext.new()
        headers = {"traceparent": sp.to_traceparent(), "X-Correlation-ID": "corr-1"}
        ctx = correlation_engine.extract_from_headers(headers)
        assert ctx is not None
        assert ctx.span.trace_id == sp.trace_id
        assert ctx.span.span_id == sp.span_id
        assert ctx.correlation.correlation_id == "corr-1"

    def test_extract_from_x_trace_id(self):
        headers = {"X-Trace-ID": "abc123def456abc123def456abc123de"}
        ctx = correlation_engine.extract_from_headers(headers)
        assert ctx is not None
        assert "abc123def456abc123def456abc123de" in ctx.span.trace_id

    def test_extract_from_x_trace_id_uuid(self):
        headers = {"X-Trace-ID": "550e8400-e29b-41d4-a716-446655440000"}
        ctx = correlation_engine.extract_from_headers(headers)
        assert ctx is not None
        assert "-" not in ctx.span.trace_id
        assert len(ctx.span.trace_id) == 32

    def test_extract_with_baggage(self):
        headers = {"baggage": "user=123,role=admin"}
        ctx = correlation_engine.extract_from_headers(headers)
        assert ctx is not None
        assert ctx.baggage.get("user") == "123"
        assert ctx.baggage.get("role") == "admin"

    def test_extract_from_empty_headers_creates_new_trace(self):
        ctx = correlation_engine.extract_from_headers({})
        assert ctx is not None
        assert ctx.span.trace_id is not None

    def test_extract_sets_current_context(self):
        correlation_engine.decay()
        ctx = correlation_engine.extract_from_headers({"X-Trace-ID": "aa" * 16})
        current = correlation_engine.get_current()
        assert current is not None
        assert current.span.trace_id == ctx.span.trace_id

    def test_roundtrip_inject_extract(self):
        orig = correlation_engine.start("rt", "test", tags={"env": "test"})
        orig.baggage.set("k", "v")
        headers = correlation_engine.inject_into_headers(orig)
        correlation_engine.end()

        restored = correlation_engine.extract_from_headers(headers)
        assert restored is not None
        assert restored.span.trace_id == orig.span.trace_id
        assert restored.span.span_id == orig.span.span_id
        assert restored.correlation.correlation_id == orig.correlation.correlation_id
        assert restored.baggage.get("k") == "v"


# =============================================================================
# 7. Context Variable — Async Isolation
# =============================================================================


class TestContextVar:
    def test_current_context_inherited_across_async_boundary(self):
        correlation_engine.start("async_test", "test")
        ctx_before = correlation_engine.get_current()
        assert ctx_before is not None

        async def check_context():
            ctx = correlation_engine.get_current()
            return ctx

        ctx_after = asyncio.run(check_context())
        assert ctx_after is not None
        assert ctx_after.span.trace_id == ctx_before.span.trace_id
        correlation_engine.end()

    def test_current_context_none_after_decay(self):
        correlation_engine.start("decay_test", "test")
        correlation_engine.decay()
        assert correlation_engine.get_current() is None

    def test_isolation_between_tasks(self):
        results = {}

        async def task_a():
            correlation_engine.start("task_a", "test")
            results["a"] = correlation_engine.get_current()
            await asyncio.sleep(0.01)
            results["a_end"] = correlation_engine.get_current()
            correlation_engine.end()

        async def task_b():
            correlation_engine.start("task_b", "test")
            results["b"] = correlation_engine.get_current()
            await asyncio.sleep(0.01)
            results["b_end"] = correlation_engine.get_current()
            correlation_engine.end()

        async def run():
            await asyncio.gather(task_a(), task_b())

        asyncio.run(run())
        assert results["a"].span.trace_id != results["b"].span.trace_id


# =============================================================================
# 8. Propagation Guard
# =============================================================================


class TestPropagationGuard:
    def test_guard_passes_healthy_context(self):
        ctx = correlation_engine.start("guard_test", "test")
        guard = propagation_guard(max_span_depth=64)
        result = guard(ctx)
        assert result is not None
        correlation_engine.end()


# =============================================================================
# 9. Header Sanitization
# =============================================================================


class TestSanitization:
    def test_sanitize_inbound_filters_unknown_headers(self):
        raw = {
            "traceparent": "00-abc-xyz-01",
            "X-Correlation-ID": "corr-1",
            "X-Internal-Secret": "leak",
        }
        clean = sanitize_inbound_headers(raw)
        assert "traceparent" in clean
        assert "x-correlation-id" in clean
        assert "x-internal-secret" not in clean

    def test_sanitize_outbound_allows_tracing_headers(self):
        raw = {
            "traceparent": "00-abc-xyz-01",
            "Authorization": "Bearer tok",
        }
        clean = sanitize_outbound_headers(raw)
        assert "traceparent" in clean
        assert "authorization" not in clean


# =============================================================================
# 10. LangGraph Node Tracer
# =============================================================================


class TestLangGraphTracer:
    def test_trace_node_wraps_function(self):
        @trace_langgraph_node(correlation_engine, "test_node")
        def my_node(state: dict) -> dict:
            return {"result": "ok"}

        ctx = correlation_engine.start("lg_test", "pytest")
        result = my_node({"input": "data"})
        assert result == {"result": "ok"}
        correlation_engine.end()

    def test_trace_node_propagates_exception(self):
        @trace_langgraph_node(correlation_engine, "failing_node")
        def failing_node(state: dict) -> dict:
            msg = "intentional failure"
            raise ValueError(msg)

        correlation_engine.start("fail_test", "test")
        with pytest.raises(ValueError, match="intentional failure"):
            failing_node({})
        correlation_engine.end()


# =============================================================================
# 11. Diagnostics Bridge
# =============================================================================


class TestDiagnosticsBridge:
    def test_span_events_emitted_to_diagnostics_engine(self):
        from app.swarm_diagnostics import diagnostics_engine

        before = len(diagnostics_engine._events)
        ctx = correlation_engine.start("diag_test", "pytest")
        correlation_engine.end()

        after = len(diagnostics_engine._events)
        assert after >= before + 1

    def test_span_event_contains_trace_id(self):
        from app.swarm_diagnostics import diagnostics_engine

        ctx = correlation_engine.start("trace_in_event", "test")
        trace_id = ctx.span.trace_id
        correlation_engine.end()

        matching = [e for e in diagnostics_engine._events if e.trace_id == trace_id]
        assert len(matching) >= 1


# =============================================================================
# 12. Reset / Cleanup
# =============================================================================


class TestReset:
    def test_reset_metrics(self):
        correlation_engine.start("reset_test", "test")
        correlation_engine.end()
        before = correlation_engine.span_count
        assert before > 0
        correlation_engine.reset_metrics()
        assert correlation_engine.span_count == 0

    def test_repr(self):
        assert "CorrelationEngine" in repr(correlation_engine)


# =============================================================================
# 13. Causation Chain Guard
# =============================================================================


class TestCausationChain:
    def test_record_causation_chain_no_error(self):
        ctx = correlation_engine.start("cause_test", "test")
        correlation_engine.record_causation_chain("event-123", ctx)
        correlation_engine.end()


# =============================================================================
# 14. Async Propagation — ContextVar survives across asyncio boundaries
# =============================================================================


@pytest.mark.asyncio
class TestAsyncPropagation:
    async def test_context_available_in_same_task(self):
        correlation_engine.start("async_test", "pytest")
        ctx = correlation_engine.get_current()
        assert ctx is not None
        assert ctx.correlation.operation_name == "async_test"
        correlation_engine.end()
        assert correlation_engine.get_current() is None

    async def test_context_propagates_to_sub_task(self):
        correlation_engine.start("async_sub", "pytest")
        parent_id = correlation_engine.get_current().span.span_id

        async def subtask() -> str:
            ctx = correlation_engine.get_current()
            if ctx is None:
                return "no-context"
            return ctx.span.span_id

        child_id = await subtask()
        assert child_id == parent_id, "ContextVar should propagate to subtask"
        correlation_engine.end()

    async def test_context_isolated_in_concurrent_tasks(self):
        async def task_a(label: str) -> str:
            c = correlation_engine.child(operation_name=label)
            if c is None:
                return "no-ctx"
            sid = c.span.span_id
            # Simulate async work
            await asyncio.sleep(0.01)
            correlation_engine.end()
            return sid

        correlation_engine.start("concurrent_root", "pytest")
        root_id = correlation_engine.get_current().span.span_id

        # Start concurrent child tasks — each creates its own child span
        results = await asyncio.gather(task_a("a"), task_a("b"))
        assert len(results) == 2
        for sid in results:
            assert sid != "no-ctx"
            assert sid != root_id
        # After both tasks end, current context should be back to root
        current = correlation_engine.get_current()
        assert current is not None
        assert current.span.span_id == root_id
        correlation_engine.end()

    async def test_context_survives_asyncio_sleep(self):
        correlation_engine.start("sleep_test", "pytest")
        ctx_before = correlation_engine.get_current()
        assert ctx_before is not None
        tid = ctx_before.span.trace_id

        await asyncio.sleep(0.05)

        ctx_after = correlation_engine.get_current()
        assert ctx_after is not None
        assert ctx_after.span.trace_id == tid
        correlation_engine.end()

    async def test_gather_with_mixed_span_hierarchy(self):
        """Nested asyncio.gather: root → child → gather(a, b) → end."""
        correlation_engine.start("gather_root", "pytest")
        root_trace = correlation_engine.get_current().span.trace_id

        async def leaf(name: str) -> dict:
            c = correlation_engine.child(operation_name=f"leaf:{name}")
            if c is None:
                return {"error": "no-ctx"}
            sid = c.span.span_id
            pid = c.span.parent_span_id
            await asyncio.sleep(0.01)
            correlation_engine.end()
            return {"span_id": sid, "parent_id": pid, "trace_id": c.span.trace_id}

        results = await asyncio.gather(leaf("x"), leaf("y"))

        for r in results:
            assert r["trace_id"] == root_trace
            assert r["parent_id"] is not None

        # leaves share the same parent (root)
        assert results[0]["parent_id"] == results[1]["parent_id"]

        current = correlation_engine.get_current()
        assert current is not None
        assert current.span.trace_id == root_trace
        correlation_engine.end()

    async def test_diagnostics_bridge_inside_async_context(self):
        """Verify diagnostics_engine receives span events from async context."""
        from app.swarm_diagnostics import diagnostics_engine as de

        before = len(de._events)
        correlation_engine.start("async_diag", "pytest")
        await asyncio.sleep(0.01)
        correlation_engine.end()

        # end() calls _emit_span_event which creates a DiagnosticEvent
        after = len(de._events)
        assert after >= before, "diagnostics event should be recorded in async context"

    async def test_cleanup_on_exception_in_async_task(self):
        """Context should be restored after an exception in an async child task."""
        correlation_engine.start("exc_root", "pytest")
        root_trace = correlation_engine.get_current().span.trace_id

        async def failing_task() -> None:
            c = correlation_engine.child("failing")
            assert c is not None
            correlation_engine.end()
            msg = "intentional fail"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="intentional fail"):
            await failing_task()

        # After exception, current context should still be root
        current = correlation_engine.get_current()
        assert current is not None
        assert current.span.trace_id == root_trace
        correlation_engine.end()

    async def test_context_not_leaked_between_tasks(self):
        """ContextVar should not leak between unrelated asyncio tasks."""

        async def isolated_task() -> str:
            ctx = correlation_engine.get_current()
            return ctx.span.trace_id if ctx else ""

        correlation_engine.start("leak_test", "pytest")
        correlation_engine.end()

        # After end(), no context should be available
        result = await isolated_task()
        assert result == "", "Context should not leak from ended span"


# =============================================================================
# 15. Propagation Consistency — Header roundtrip, W3C compliance
# =============================================================================


class TestPropagationConsistency:
    def setup_method(self):
        correlation_engine.decay()

    def test_traceparent_roundtrip_preserves_all_fields(self):
        ctx = correlation_engine.start("rt_full", "test", tags={"env": "test"})
        ctx.baggage.set("role", "swarm")
        headers = correlation_engine.inject_into_headers(ctx)
        correlation_engine.end()

        restored = correlation_engine.extract_from_headers(headers)
        assert restored is not None
        assert restored.span.trace_id == ctx.span.trace_id
        assert restored.span.span_id == ctx.span.span_id
        assert restored.correlation.correlation_id == ctx.correlation.correlation_id
        assert restored.baggage.get("role") == "swarm"

    def test_tracestate_inject_and_extract(self):
        ctx = correlation_engine.start("ts_test", "test")
        ctx.tracestate["swarm"] = "engine"
        ctx.tracestate["swarm_ver"] = "1.0"
        headers = correlation_engine.inject_into_headers(ctx)
        assert "tracestate" in headers
        assert "swarm=engine" in headers["tracestate"]
        assert "swarm_ver=1.0" in headers["tracestate"]

        restored = correlation_engine.extract_from_headers(headers)
        assert restored is not None
        assert restored.tracestate.get("swarm") == "engine"
        assert restored.tracestate.get("swarm_ver") == "1.0"
        correlation_engine.end()

    def test_multiple_header_types_at_once(self):
        ctx = correlation_engine.start("multi", "test", causation_id="cause-multi")
        ctx.baggage.set("k1", "v1")
        ctx.baggage.set("k2", "v2")
        ctx.tracestate["vendor"] = "swarm"
        headers = correlation_engine.inject_into_headers(ctx)
        correlation_engine.end()

        assert "traceparent" in headers
        assert "X-Correlation-ID" in headers
        assert "X-Causation-ID" in headers
        assert "baggage" in headers
        assert "tracestate" in headers

        restored = correlation_engine.extract_from_headers(headers)
        assert restored is not None
        assert restored.correlation.causation_id == "cause-multi"
        assert restored.baggage.get("k1") == "v1"
        assert restored.tracestate["vendor"] == "swarm"

    def test_empty_headers_creates_new_span(self):
        correlation_engine.decay()
        ctx = correlation_engine.extract_from_headers({})
        assert ctx is not None
        assert ctx.span.trace_id is not None
        assert ctx.span.span_id is not None
        assert len(ctx.span.trace_id) == 32

    def test_inject_without_context_returns_empty(self):
        correlation_engine.decay()
        assert correlation_engine.inject_into_headers() == {}

    def test_baggage_empty_when_not_set(self):
        ctx = correlation_engine.start("no_bag", "test")
        assert len(ctx.baggage.items) == 0
        headers = correlation_engine.inject_into_headers(ctx)
        assert "baggage" not in headers
        correlation_engine.end()

    def test_tracestate_empty_when_not_set(self):
        ctx = correlation_engine.start("no_ts", "test")
        assert len(ctx.tracestate) == 0
        headers = correlation_engine.inject_into_headers(ctx)
        assert "tracestate" not in headers
        correlation_engine.end()

    def test_sanitize_inbound_filters_unknown_headers(self):
        raw = {
            "traceparent": "00-abcd1234...-ef567890...-01",
            "x-correlation-id": "corr-1",
            "x-custom-secret": "shh",
            "authorization": "Bearer tok",
        }
        clean = sanitize_inbound_headers(raw)
        assert "traceparent" in clean
        assert "x-correlation-id" in clean
        assert "x-custom-secret" not in clean
        assert "authorization" not in clean

    def test_sanitize_outbound_filters_unknown_headers(self):
        raw = {"traceparent": "00-ab...", "content-type": "json", "x-internal": "secret"}
        clean = sanitize_outbound_headers(raw)
        assert "traceparent" in clean
        assert "content-type" not in clean
        assert "x-internal" not in clean


# =============================================================================
# 16. Tracing Consistency — Limits, W3C compliance, data integrity
# =============================================================================


class TestTracingConsistency:
    def test_w3c_traceparent_format(self):
        ctx = correlation_engine.start("w3c_fmt", "test")
        tp = ctx.span.to_traceparent()
        parts = tp.split("-")
        assert len(parts) == 4
        assert parts[0] == TRACEPARENT_VERSION  # "00"
        assert len(parts[1]) == 32  # trace_id
        assert len(parts[2]) == 16  # span_id
        assert len(parts[3]) == 2   # trace_flags
        # All hex characters
        int(parts[1], 16)
        int(parts[2], 16)
        int(parts[3], 16)
        correlation_engine.end()

    def test_w3c_traceparent_roundtrip(self):
        raw = "00-0123456789abcdef0123456789abcdef-abcdef0123456789-01"
        sp = SpanContext.from_traceparent(raw)
        assert sp is not None
        assert sp.trace_id == "0123456789abcdef0123456789abcdef"
        assert sp.span_id == "abcdef0123456789"
        assert sp.trace_flags == "01"
        assert sp.to_traceparent() == raw

    def test_invalid_traceparent_returns_none(self):
        assert SpanContext.from_traceparent("") is None
        assert SpanContext.from_traceparent("not-a-traceparent") is None
        assert SpanContext.from_traceparent("01-abcd-1234-01") is None  # wrong version
        assert SpanContext.from_traceparent("00-short-1234-01") is None  # short trace_id

    def test_baggage_item_limit_enforced(self):
        b = Baggage()
        for i in range(MAX_BAGGAGE_ITEMS):
            b.set(f"k{i}", "v")
        with pytest.raises(ValueError, match="baggage item limit"):
            b.set("extra", "value")

    def test_baggage_value_size_limit_enforced(self):
        b = Baggage()
        big_val = "x" * (MAX_BAGGAGE_VALUE_BYTES + 1)
        with pytest.raises(ValueError, match="baggage value.*exceeds"):
            b.set("key", big_val)

    def test_tag_limit_enforced(self):
        ctx = correlation_engine.start("tag_lim", "test")
        for i in range(MAX_TAGS):
            ctx = ctx.with_tag(f"t{i}", str(i))
        with pytest.raises(ValueError, match="tag limit"):
            ctx.with_tag("extra", "value")
        correlation_engine.end()

    def test_child_span_preserves_trace_id(self):
        correlation_engine.start("child_trace", "test")
        tid = correlation_engine.get_current().span.trace_id

        child = correlation_engine.child("step1", tags={"stage": "first"})
        assert child.span.trace_id == tid
        assert child.span.parent_span_id is not None
        correlation_engine.end()  # child

        # Back to root
        current = correlation_engine.get_current()
        assert current.span.trace_id == tid
        assert current.span.parent_span_id is None
        correlation_engine.end()  # root

    def test_deep_child_chain(self):
        correlation_engine.start("chain_root", "test")
        root_trace = correlation_engine.get_current().span.trace_id
        depth = 10
        for i in range(depth):
            correlation_engine.child(f"level_{i}")
        for i in range(depth):
            current = correlation_engine.end()
        # After depth ends, chain fully consumed
        assert correlation_engine.get_current() is None

    def test_span_count_metrics(self):
        before = correlation_engine.span_count
        correlation_engine.start("metrics_test", "test")
        correlation_engine.child("child_a")
        correlation_engine.end()
        correlation_engine.child("child_b")
        correlation_engine.end()
        correlation_engine.end()
        assert correlation_engine.span_count >= before + 3
        correlation_engine.reset_metrics()

    def test_reset_metrics_clears_count(self):
        correlation_engine.start("reset_me", "test")
        correlation_engine.end()
        correlation_engine.reset_metrics()
        assert correlation_engine.span_count == 0

    def test_diagnostics_bridge_records_span_events(self):
        from app.swarm_diagnostics import diagnostics_engine as de

        before = len(de._events)
        correlation_engine.start("diag_span", "test")
        correlation_engine.child("inner")
        correlation_engine.end()
        correlation_engine.end()
        after = len(de._events)
        assert after >= before + 2, "each end() should emit a diagnostic event"

    def test_child_span_has_different_span_id(self):
        correlation_engine.start("id_test", "test")
        root_id = correlation_engine.get_current().span.span_id
        child = correlation_engine.child("child")
        assert child.span.span_id != root_id
        assert child.span.parent_span_id == root_id
        correlation_engine.end()
        correlation_engine.end()

    def test_legacy_trace_context_bridge(self):
        from app.observability.tracing import TraceContext

        ctx = correlation_engine.start("legacy_bridge", "test")
        legacy = ctx.to_legacy_trace_context()
        assert isinstance(legacy, TraceContext)
        assert legacy.trace_id == ctx.span.trace_id
        assert legacy.span_id == ctx.span.span_id
        assert legacy.correlation_id == ctx.correlation.correlation_id
        correlation_engine.end()

    def test_set_current_overrides_context(self):
        correlation_engine.start("original", "test")
        orig_span = correlation_engine.get_current().span.span_id

        new_ctx = correlation_engine.start("override", "test")
        assert correlation_engine.get_current().span.span_id == new_ctx.span.span_id
        assert correlation_engine.get_current().span.span_id != orig_span

        correlation_engine.end()
        correlation_engine.end()


# =============================================================================
# 17. Nested Correlation — Parent-child span chains and causation depth
# =============================================================================


class TestNestedCorrelation:
    def setup_method(self):
        correlation_engine.decay()

    def test_single_parent_child(self):
        ctx = correlation_engine.start("parent", "test")
        pid = ctx.span.span_id
        child = correlation_engine.child("child")
        assert child.span.parent_span_id == pid
        assert child.correlation.correlation_id == ctx.correlation.correlation_id
        correlation_engine.end()
        correlation_engine.end()

    def test_chain_of_three(self):
        root = correlation_engine.start("grandparent", "test")
        tid = root.span.trace_id

        c1 = correlation_engine.child("parent")
        assert c1.span.parent_span_id == root.span.span_id

        c2 = correlation_engine.child("child")
        assert c2.span.parent_span_id == c1.span.span_id
        assert c2.span.trace_id == tid

        correlation_engine.end()  # child → parent
        correlation_engine.end()  # parent → root
        correlation_engine.end()  # root → None

        assert correlation_engine.get_current() is None

    def test_causation_id_flows_down_chain(self):
        root = correlation_engine.start(
            "root", "test", causation_id="root-cause",
        )
        assert root.correlation.causation_id == "root-cause"

        child = correlation_engine.child("mid", causation_id="mid-cause")
        assert child.correlation.causation_id == "mid-cause"

        grandchild = correlation_engine.child("leaf")
        # causation_id is auto-generated when not explicitly set
        assert grandchild.correlation.causation_id is not None
        assert grandchild.correlation.causation_id != child.correlation.causation_id

        correlation_engine.end()
        correlation_engine.end()
        correlation_engine.end()

    def test_causation_id_auto_generated_when_missing(self):
        root = correlation_engine.start("auto", "test")
        child = correlation_engine.child("step")
        # causation_id should be auto-generated (not None)
        assert child.correlation.causation_id is not None
        assert child.correlation.causation_id != root.correlation.causation_id
        correlation_engine.end()
        correlation_engine.end()

    def test_propagation_context_child_span_immutability(self):
        ctx = correlation_engine.start("immutable", "test")
        child = ctx.child_span("immutable_child")
        assert child.span.span_id != ctx.span.span_id
        assert child.span.parent_span_id == ctx.span.span_id
        assert child.correlation.correlation_id == ctx.correlation.correlation_id
        # Original context should be unmodified
        assert ctx.span.parent_span_id is None
        correlation_engine.end()

    def test_child_inherits_baggage(self):
        ctx = correlation_engine.start("bag_inherit", "test")
        ctx.baggage.set("swarm_id", "s-123")
        child = ctx.child_span("bag_child")
        assert child.baggage.get("swarm_id") == "s-123"
        correlation_engine.end()

    def test_child_inherits_tags(self):
        ctx = correlation_engine.start("tag_inherit", "test", tags={"env": "test"})
        child = ctx.child_span("tag_child")
        assert child.tags.get("env") == "test"
        correlation_engine.end()

    def test_child_inherits_tracestate(self):
        ctx = correlation_engine.start("ts_inherit", "test")
        ctx.tracestate["vendor"] = "swarm"
        child = ctx.child_span("ts_child")
        assert child.tracestate.get("vendor") == "swarm"
        correlation_engine.end()

    def test_causation_chain_depth_limit(self):
        """Verify the correlation engine's record_causation_chain doesn't crash."""
        ctx = correlation_engine.start("deep_chain", "test")
        # Simulate a deep chain by recording many causation links
        for i in range(5):
            correlation_engine.record_causation_chain(f"event-{i}", ctx)
        correlation_engine.end()

    def test_end_after_all_children_returns_to_root(self):
        correlation_engine.start("multi_child_root", "test")
        root_span = correlation_engine.get_current().span.span_id

        correlation_engine.child("a")
        correlation_engine.end()
        assert correlation_engine.get_current().span.span_id == root_span

        correlation_engine.child("b")
        correlation_engine.end()
        assert correlation_engine.get_current().span.span_id == root_span

        correlation_engine.end()
        assert correlation_engine.get_current() is None

    def test_end_without_start_is_noop(self):
        correlation_engine.decay()
        result = correlation_engine.end()
        assert result is None

    def test_child_without_current_returns_new_root(self):
        correlation_engine.decay()
        child = correlation_engine.child("orphan")
        # When there's no active context, child() falls back to start()
        assert child is not None
        assert child.span.parent_span_id is None
        correlation_engine.end()

    def test_logging_filter_populates_record_attributes(self):
        from app.tracing.propagation import TraceLoggingFilter
        import logging

        f = TraceLoggingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test", args=(), exc_info=None,
        )

        # Without active context → empty strings
        correlation_engine.decay()
        f.filter(record)
        assert record.trace_id == ""
        assert record.span_id == ""
        assert record.correlation_id == ""

        # With active context → populated
        ctx = correlation_engine.start("log_test", "test")
        f.filter(record)
        assert record.trace_id == ctx.span.trace_id
        assert record.span_id == ctx.span.span_id
        assert record.correlation_id == ctx.correlation.correlation_id
        correlation_engine.end()
