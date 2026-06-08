"""Observability for Tavily retrieval — diagnostics events, metrics, and tracing."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integrations.tavily.schemas import AggregatedResearch, TavilyQueryResult
from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)


class TavilyDiagnostics:
    """Emits structured diagnostics events for the Tavily retrieval lifecycle.

    Event naming convention: ``tavily:<domain>:<action>``
    Events integrate with the swarm's ``diagnostics_engine`` for SSE delivery.
    """

    def __init__(self, diagnostics_engine: Any | None = None):
        self._engine = diagnostics_engine

    # ── Query lifecycle ───────────────────────────────────────────

    def query_start(self, query: str, category: str, context: dict | None = None) -> None:
        self._emit("tavily:query:start", {
            "query": query[:80],
            "category": category,
            "context": context or {},
        })

    def query_cache_hit(self, query: str, category: str, latency_ms: float) -> None:
        self._emit("tavily:query:cache_hit", {
            "query": query[:80],
            "category": category,
            "latency_ms": latency_ms,
        })
        exporter.inc_counter("tavily_cache_hits")

    def query_cache_miss(self, query: str, category: str) -> None:
        self._emit("tavily:query:cache_miss", {
            "query": query[:80],
            "category": category,
        })
        exporter.inc_counter("tavily_cache_misses")

    def query_ok(self, result: TavilyQueryResult) -> None:
        self._emit("tavily:query:ok", {
            "query": result.query[:80],
            "category": result.category.value,
            "sources": result.response.source_count if result.response else 0,
            "latency_ms": result.query_time_ms,
            "confidence": result.confidence,
            "cached": result.cached,
        })
        exporter.inc_counter("tavily_query_successes")

    def query_error(self, result: TavilyQueryResult) -> None:
        self._emit("tavily:query:error", {
            "query": result.query[:80],
            "category": result.category.value,
            "error": result.error,
            "latency_ms": result.query_time_ms,
            "confidence": result.confidence,
        })
        exporter.inc_counter("tavily_query_errors")

    def query_skipped(self, query: str, category: str, reason: str) -> None:
        self._emit("tavily:query:skipped", {
            "query": query[:80],
            "category": category,
            "reason": reason,
        })
        exporter.inc_counter("tavily_queries_skipped")

    # ── Research session lifecycle ────────────────────────────────

    def research_start(self, topic: str, objectives: list[str], bloom_target: int) -> None:
        self._emit("tavily:research:start", {
            "topic": topic[:60],
            "objectives": objectives,
            "bloom_target": bloom_target,
        })
        exporter.inc_counter("tavily_research_started")

    def research_complete(self, result: AggregatedResearch, latency_ms: float) -> None:
        self._emit("tavily:research:complete", {
            "topic": result.topic[:60],
            "total_sources": result.total_sources,
            "unique_domains": result.unique_domains,
            "confidence": result.confidence_score,
            "latency_ms": latency_ms,
            "concepts": len(result.concepts),
            "examples": len(result.examples),
            "analogies": len(result.analogies),
            "real_applications": len(result.real_applications),
            "misconceptions": len(result.misconceptions),
            "exercises": len(result.exercises),
            "contradictions": len(result.contradictions),
        })
        exporter.inc_counter("tavily_research_completed")
        exporter.observe_histogram("tavily_research_sources", result.total_sources)
        exporter.observe_histogram("tavily_research_duration_ms", latency_ms)

    def research_degraded(self, topic: str, reason: str) -> None:
        self._emit("tavily:research:degraded", {
            "topic": topic[:60],
            "reason": reason,
        })
        exporter.inc_counter("tavily_research_degraded")

    def research_failed(self, topic: str, error: str) -> None:
        self._emit("tavily:research:failed", {
            "topic": topic[:60],
            "error": error[:300],
        })
        exporter.inc_counter("tavily_research_failures")

    # ── Contradictions ────────────────────────────────────────────

    def contradiction_detected(
        self,
        topic: str,
        statements: list[str],
        sources: list[str],
        severity: str,
        confidence: float,
    ) -> None:
        self._emit("tavily:contradiction:detected", {
            "topic": topic[:60],
            "statements": statements,
            "sources": sources,
            "severity": severity,
            "confidence": confidence,
        })
        exporter.inc_counter("tavily_contradictions_detected")

    # ── Rate limiter / circuit breaker ────────────────────────────

    def rate_limited(self) -> None:
        self._emit("tavily:rate_limiter:limit_reached", {})
        exporter.inc_counter("tavily_rate_limited")

    def circuit_open(self, name: str, failure_count: int) -> None:
        self._emit("tavily:circuit_breaker:open", {
            "name": name,
            "failure_count": failure_count,
        })
        exporter.set_gauge(f"circuit_breaker_{name}", 1.0)
        exporter.inc_counter(f"circuit_breaker_{name}_open")

    def circuit_closed(self, name: str) -> None:
        self._emit("tavily:circuit_breaker:closed", {"name": name})
        exporter.set_gauge(f"circuit_breaker_{name}", 0.0)

    def circuit_half_open(self, name: str) -> None:
        self._emit("tavily:circuit_breaker:half_open", {"name": name})
        exporter.set_gauge(f"circuit_breaker_{name}", 0.5)

    # ── Aggregation ───────────────────────────────────────────────

    def aggregation_summary(self, result: AggregatedResearch) -> None:
        self._emit("tavily:aggregation:summary", {
            "topic": result.topic[:60],
            "sources_after_dedup": result.total_sources,
            "domains": result.unique_domains,
            "confidence": result.confidence_score,
        })

    # ── Internal ──────────────────────────────────────────────────

    def _emit(self, event_type: str, data: dict[str, Any]) -> None:
        if self._engine is not None and hasattr(self._engine, "record_event"):
            try:
                self._engine.record_event(event_type, data)
            except Exception as e:
                logger.debug("Failed to emit diagnostics event %s: %s", event_type, e)
        logger.debug("Diagnostics event: %s %s", event_type, data)


# Singleton
_diagnostics: TavilyDiagnostics | None = None


def get_tavily_diagnostics(diagnostics_engine: Any | None = None) -> TavilyDiagnostics:
    global _diagnostics
    if _diagnostics is None:
        _diagnostics = TavilyDiagnostics(diagnostics_engine=diagnostics_engine)
    return _diagnostics
