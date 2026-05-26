from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

from app.tracing.engine import CorrelationEngine

logger = logging.getLogger(__name__)


def trace_langgraph_node(
    engine: CorrelationEngine,
    node_name: str,
) -> Callable:
    """Decorator that wraps a LangGraph node function with distributed tracing.

    On entry: creates a child span from the current PropagationContext.
    On exit: ends the span and records duration + results as span tags.

    Usage:
        @trace_langgraph_node(engine, "diagnostic_analyzer")
        def diagnostic_analyzer(state: dict) -> dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(state: dict, **kwargs: Any) -> dict:
            ctx = engine.child(
                operation_name=f"langgraph:{node_name}",
                tags={"node": node_name, "graph_type": "StateGraph"},
            )
            start_ns = time.monotonic_ns()
            error: str | None = None
            try:
                result = func(state, **kwargs)
                return result
            except Exception as exc:
                error = str(exc)
                raise
            finally:
                duration_ms = (time.monotonic_ns() - start_ns) / 1_000_000
                if ctx:
                    tagged = ctx.with_tag("duration_ms", f"{duration_ms:.3f}")
                    if error:
                        tagged = tagged.with_tag("error", error)
                    engine.set_current(tagged)
                engine.end()

        return wrapper
    return decorator


class TracingLangGraph:
    """Wraps a compiled LangGraph with per-node tracing.

    Usage:
        graph = build_agent_graph()
        tracing_graph = TracingLangGraph(engine, graph)
        result = tracing_graph.invoke(state)
    """

    def __init__(self, engine: CorrelationEngine, compiled_graph: Any) -> None:
        self._engine = engine
        self._graph = compiled_graph
        self._wrapped_nodes: dict[str, Callable] = {}

    def wrap_node(self, node_name: str, node_func: Callable) -> None:
        wrapped = trace_langgraph_node(self._engine, node_name)(node_func)
        self._wrapped_nodes[node_name] = wrapped

    def invoke(self, state: dict, config: Any = None, **kwargs: Any) -> dict:
        root_ctx = self._engine.child(
            operation_name="langgraph:invoke",
            tags={"graph_type": "StateGraph"},
        )
        start_ns = time.monotonic_ns()
        error: str | None = None
        try:
            result = self._graph.invoke(state, config=config, **kwargs)
            return result
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration_ms = (time.monotonic_ns() - start_ns) / 1_000_000
            if root_ctx:
                tagged = root_ctx.with_tag("graph_duration_ms", f"{duration_ms:.3f}")
                if error:
                    tagged = tagged.with_tag("graph_error", error)
                self._engine.set_current(tagged)
            self._engine.end()

    @property
    def graph(self) -> Any:
        return self._graph
