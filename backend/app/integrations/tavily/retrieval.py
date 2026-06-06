"""PedagogicalRetrievalStrategy — generates optimized queries and aggregates retrieval into pedagogical knowledge."""

from __future__ import annotations

import logging
import time
from typing import Any

from app.integrations.tavily.cache import TavilyCache
from app.integrations.tavily.client import TavilyClient, get_tavily_client
from app.integrations.tavily.rate_limit import TavilyRateLimiterChain, get_rate_limiter_chain
from app.integrations.tavily.schemas import (
    AggregatedResearch,
    QueryCategory,
    RetrievalContext,
    SearchDepth,
    TavilyQueryResult,
    TavilySearchResponse,
)
from app.observability.metrics_exporter import exporter

logger = logging.getLogger(__name__)

MAX_CONCURRENT_QUERIES = 3
SOURCE_DIVERSITY_MIN_DOMAINS = 2
CONFIDENCE_THRESHOLD = 0.3


class PedagogicalRetrievalStrategy:
    """Generates pedagogically-optimized search queries and aggregates results.

    Query generation strategies:
    - introductory: "X for beginners", "X explained simply"
    - conceptual: "X definition", "X fundamentals"
    - practical: "X examples", "X exercises"
    - misconception: "common mistakes X", "X pitfalls"
    - beginner_friendly: "X easy explanation"
    - bloom_level: "X Bloom taxonomy", "teach X"
    - analogy: "X analogy", "X compared to"
    - real_application: "real world applications X"
    - exercise: "X practice problems", "X exercises for students"

    Aggregation deduplicates across queries and ranks by:
    - Source score (Tavily relevance)
    - Source diversity (unique domains)
    - Content richness (length, structure)
    """

    def __init__(
        self,
        client: TavilyClient | None = None,
        cache: TavilyCache | None = None,
        rate_limiter: TavilyRateLimiterChain | None = None,
    ):
        self._client = client or get_tavily_client()
        self._cache = cache
        self._rate_limiter = rate_limiter or get_rate_limiter_chain()

    # ── Public API ────────────────────────────────────────────────

    async def research(self, context: RetrievalContext) -> AggregatedResearch:
        """Execute full pedagogical research for a given context.

        Generates multi-query search, executes with concurrency,
        deduplicates, and aggregates into structured pedagogical knowledge.
        """
        start_time = time.monotonic()
        queries = self._generate_queries(context)
        logger.info(
            "Pedagogical research: topic='%s' queries=%d",
            context.topic[:40], len(queries),
        )

        results = await self._execute_queries(queries, context)
        aggregated = self._aggregate_results(results, context)
        aggregated.confidence_score = self._compute_confidence(results)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        logger.info(
            "Research complete: topic='%s' sources=%d domains=%d confidence=%.2f time=%.0fms",
            context.topic[:40], aggregated.total_sources,
            aggregated.unique_domains, aggregated.confidence_score, elapsed_ms,
        )

        exporter.observe_histogram("tavily_research_duration_ms", elapsed_ms)
        exporter.inc_counter("tavily_research_completed")

        return aggregated

    # ── Query generation ──────────────────────────────────────────

    def _generate_queries(self, context: RetrievalContext) -> list[tuple[str, QueryCategory]]:
        topic = context.topic
        queries: list[tuple[str, QueryCategory]] = []

        queries.append((f"{topic} for beginners explained simply", QueryCategory.INTRODUCTION))
        queries.append((f"{topic} definition fundamentals concepts", QueryCategory.CONCEPTUAL))
        queries.append((f"{topic} examples and practical exercises", QueryCategory.PRACTICAL))
        queries.append((f"common mistakes misconceptions {topic}", QueryCategory.MISCONCEPTION))
        queries.append((f"{topic} easy explanation pedagogical", QueryCategory.BEGINNER))
        queries.append((f"real world applications {topic}", QueryCategory.REAL_APPLICATION))
        queries.append((f"{topic} analogy example teaching", QueryCategory.ANALOGY))
        queries.append((f"{topic} Bloom taxonomy exercises", QueryCategory.BLOOM_LEVEL))

        return queries

    def _bloom_level_label(self, level: int) -> str:
        labels = {
            1: "remember",
            2: "understand",
            3: "apply",
            4: "analyze",
            5: "evaluate",
            6: "create",
        }
        return labels.get(level, "understand")

    # ── Query execution ──────────────────────────────────────────

    async def _execute_queries(
        self,
        queries: list[tuple[str, QueryCategory]],
        context: RetrievalContext,
    ) -> list[TavilyQueryResult]:
        results: list[TavilyQueryResult] = []

        for query_text, category in queries:
            start_q = time.monotonic()

            # Check cache first
            if self._cache:
                cached = await self._cache.get(query_text)
                if cached is not None:
                    elapsed_ms = (time.monotonic() - start_q) * 1000
                    results.append(TavilyQueryResult(
                        query=query_text,
                        category=category,
                        response=cached,
                        cached=True,
                        query_time_ms=elapsed_ms,
                        confidence=self._score_confidence(cached),
                    ))
                    exporter.inc_counter("tavily_query_cached")
                    continue

            # Check rate limiter + circuit breaker
            if not await self._rate_limiter.can_proceed():
                logger.warning("Rate limited or circuit open — skipping query: '%s'", query_text[:40])
                exporter.inc_counter("tavily_queries_skipped")
                continue

            # Execute search
            try:
                response = await self._client.search(
                    query=query_text,
                    max_results=5,
                    include_answer=True,
                )

                elapsed_ms = (time.monotonic() - start_q) * 1000
                self._rate_limiter.record_success()

                result = TavilyQueryResult(
                    query=query_text,
                    category=category,
                    response=response,
                    query_time_ms=elapsed_ms,
                    confidence=self._score_confidence(response),
                )
                results.append(result)

                # Store in cache
                if self._cache and response.source_count > 0:
                    await self._cache.set(query_text, response)

                exporter.inc_counter("tavily_query_ok")

            except Exception as e:
                elapsed_ms = (time.monotonic() - start_q) * 1000
                self._rate_limiter.record_failure()
                results.append(TavilyQueryResult(
                    query=query_text,
                    category=category,
                    error=str(e)[:200],
                    query_time_ms=elapsed_ms,
                    confidence=0.0,
                ))
                exporter.inc_counter("tavily_query_errors")
                logger.warning("Query failed: '%s' — %s", query_text[:40], e)

        return results

    # ── Aggregation ───────────────────────────────────────────────

    def _aggregate_results(
        self,
        results: list[TavilyQueryResult],
        context: RetrievalContext,
    ) -> AggregatedResearch:
        all_sources: list[dict] = []
        seen_urls: set[str] = set()
        seen_domains: set[str] = set()

        concepts: list[dict] = []
        examples: list[dict] = []
        analogies: list[dict] = []
        real_apps: list[dict] = []
        misconceptions: list[dict] = []
        exercises: list[dict] = []
        contradictions: list[dict] = []

        for qr in results:
            if not qr.success or qr.response is None:
                continue

            for source in qr.response.results:
                if source.url in seen_urls:
                    continue
                seen_urls.add(source.url)

                domain = self._extract_domain(source.url)
                if domain:
                    seen_domains.add(domain)

                source_dict = {
                    "title": source.title,
                    "url": source.url,
                    "domain": domain,
                    "score": source.score,
                    "content_preview": source.content[:300],
                    "category": qr.category.value,
                }
                all_sources.append(source_dict)

                # Classify content by query category
                content_lower = source.content.lower()
                category = qr.category

                if category in (QueryCategory.CONCEPTUAL, QueryCategory.INTRODUCTION):
                    concepts.append({
                        "concept": context.topic,
                        "source_title": source.title,
                        "content": source.content[:500],
                        "domain": domain,
                        "confidence": source.score,
                    })

                elif category == QueryCategory.PRACTICAL:
                    examples.append({
                        "example": source.content[:400],
                        "source": source.title,
                        "domain": domain,
                    })

                elif category == QueryCategory.MISCONCEPTION:
                    misconceptions.append({
                        "misconception": source.content[:400],
                        "source": source.title,
                    })

                elif category == QueryCategory.REAL_APPLICATION:
                    real_apps.append({
                        "application": source.content[:400],
                        "source": source.title,
                    })

                elif category == QueryCategory.ANALOGY:
                    analogies.append({
                        "analogy": source.content[:400],
                        "source": source.title,
                    })

                elif category in (QueryCategory.BLOOM_LEVEL, QueryCategory.EXERCISE):
                    exercises.append({
                        "exercise": source.content[:400],
                        "source": source.title,
                    })

            # Check for contradictions in answers
            if qr.response.answer:
                contradictions.extend(
                    self._detect_contradictions(qr, results)
                )

        # Deduplicate
        concepts = self._deduplicate_by_key(concepts, "content")
        examples = self._deduplicate_by_key(examples, "example")
        misconceptions = self._deduplicate_by_key(misconceptions, "misconception")
        analogies = self._deduplicate_by_key(analogies, "analogy")
        real_apps = self._deduplicate_by_key(real_apps, "application")
        exercises = self._deduplicate_by_key(exercises, "exercise")
        contradictions = contradictions[:5]

        return AggregatedResearch(
            topic=context.topic,
            concepts=concepts,
            examples=examples,
            analogies=analogies,
            real_applications=real_apps,
            misconceptions=misconceptions,
            exercises=exercises,
            sources=all_sources,
            contradictions=contradictions,
            total_sources=len(all_sources),
            unique_domains=len(seen_domains),
        )

    # ── Scoring ────────────────────────────────────────────────────

    def _score_confidence(self, response: TavilySearchResponse) -> float:
        if response.source_count == 0:
            return 0.0
        avg_score = sum(s.score for s in response.results) / response.source_count
        return min(1.0, avg_score * 1.5)

    def _compute_confidence(self, results: list[TavilyQueryResult]) -> float:
        successful = [r for r in results if r.success]
        if not successful:
            return 0.0
        avg_conf = sum(r.confidence for r in successful) / len(successful)
        success_ratio = len(successful) / max(len(results), 1)
        return round(avg_conf * success_ratio, 4)

    # ── Contradiction detection ────────────────────────────────────

    def _detect_contradictions(
        self,
        result: TavilyQueryResult,
        all_results: list[TavilyQueryResult],
    ) -> list[dict]:
        contradictions = []
        if not result.response or not result.response.answer:
            return contradictions

        for other in all_results:
            if other is result or not other.success or not other.response:
                continue
            if other.response.answer:
                if self._contradicts(result.response.answer, other.response.answer):
                    contradictions.append({
                        "statements": [
                            result.response.answer[:200],
                            other.response.answer[:200],
                        ],
                        "sources": [
                            result.response.top_sources[0].url if result.response.top_sources else "",
                            other.response.top_sources[0].url if other.response.top_sources else "",
                        ],
                        "severity": "info",
                        "confidence": min(result.confidence, other.confidence),
                    })
        return contradictions

    def _contradicts(self, a: str, b: str) -> bool:
        """Simple heuristic contradiction detection between two statements.

        Looks for opposing keywords. In production, this would use
        an LLM-based contradiction classifier.
        """
        a_lower = a.lower()
        b_lower = b.lower()
        contradict_pairs = [
            ("always", "never"),
            ("must", "must not"),
            ("cannot", "can"),
            ("is not", "is"),
            ("incorrect", "correct"),
            ("wrong", "right"),
            ("false", "true"),
        ]
        a_words = set(a_lower.split())
        b_words = set(b_lower.split())
        for w1, w2 in contradict_pairs:
            if (w1 in a_words and w2 in b_words) or (w2 in a_words and w1 in b_words):
                return True
        return False

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc or ""
        except Exception:
            return ""

    @staticmethod
    def _deduplicate_by_key(items: list[dict], key: str) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            val = item.get(key, "")
            if val not in seen:
                seen.add(val)
                result.append(item)
        return result
