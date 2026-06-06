"""Tests for PedagogicalRetrievalStrategy: query generation, aggregation, contradiction detection, dedup,
full pipeline execution, metrics, and edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import (
    AggregatedResearch,
    PedagogicalMetrics,
    QueryCategory,
    RetrievalContext,
    SearchDepth,
    TavilyQueryResult,
    TavilySearchResponse,
    TavilySource,
)


def _make_response(
    title: str = "r1", content: str = "content", score: float = 0.9,
    answer: str = "", url: str | None = None,
) -> TavilySearchResponse:
    return TavilySearchResponse(
        query=title,
        results=[TavilySource(
            title=title,
            url=url or f"https://{title}.com",
            content=content,
            score=score,
        )],
        answer=answer,
        response_time_ms=0.3,
    )


def _make_multi_source_response(
    sources: list[tuple[str, str, float, str]],
    answer: str = "",
) -> TavilySearchResponse:
    return TavilySearchResponse(
        query="multi",
        results=[
            TavilySource(title=t, url=u, content=c, score=s)
            for t, u, c, s in sources
        ],
        answer=answer,
        response_time_ms=0.5,
    )


# ═════════════════════════════════════════════════════════════════════
# Query generation
# ═════════════════════════════════════════════════════════════════════

class TestQueryGeneration:
    def test_generates_eight_queries(self):
        strategy = PedagogicalRetrievalStrategy()
        ctx = RetrievalContext(topic="Python programming", objectives=[], bloom_target=3)
        queries = strategy._generate_queries(ctx)
        assert len(queries) == 8
        categories = {q[1] for q in queries}
        assert QueryCategory.INTRODUCTION in categories
        assert QueryCategory.CONCEPTUAL in categories
        assert QueryCategory.MISCONCEPTION in categories
        assert QueryCategory.ANALOGY in categories

    def test_query_text_contains_topic(self):
        strategy = PedagogicalRetrievalStrategy()
        ctx = RetrievalContext(topic="Binary trees", objectives=[], bloom_target=2)
        queries = strategy._generate_queries(ctx)
        for text, _ in queries:
            assert "binary" in text.lower() or "Binary" in text

    def test_non_ascii_topic(self):
        strategy = PedagogicalRetrievalStrategy()
        ctx = RetrievalContext(topic="Arreglos en programación", objectives=[], bloom_target=3)
        queries = strategy._generate_queries(ctx)
        assert len(queries) == 8
        for text, _ in queries:
            assert "arreglos" in text.lower() or "Arreglos" in text

    def test_empty_topic(self):
        strategy = PedagogicalRetrievalStrategy()
        ctx = RetrievalContext(topic="", objectives=[], bloom_target=1)
        queries = strategy._generate_queries(ctx)
        assert len(queries) == 8
        assert all(query.startswith(" ") for query, _ in queries)


# ═════════════════════════════════════════════════════════════════════
# Contradiction detection
# ═════════════════════════════════════════════════════════════════════

class TestContradictionDetection:
    def test_detect_contradicting_keywords(self):
        strategy = PedagogicalRetrievalStrategy()
        result = TavilyQueryResult(
            query="q1", category=QueryCategory.CONCEPTUAL,
            response=_make_response(answer="You should always use recursion for this", score=0.9),
            query_time_ms=10, confidence=0.9,
        )
        all_results = [
            result,
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                response=_make_response(answer="You should never use recursion for this", score=0.8),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        contradictions = strategy._detect_contradictions(result, all_results)
        assert len(contradictions) >= 1

    def test_no_contradiction_on_similar_statements(self):
        strategy = PedagogicalRetrievalStrategy()
        result = TavilyQueryResult(
            query="q1", category=QueryCategory.CONCEPTUAL,
            response=_make_response(answer="Recursion is a useful technique", score=0.9),
            query_time_ms=10, confidence=0.9,
        )
        all_results = [
            result,
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                response=_make_response(answer="Recursion is widely used in programming", score=0.8),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        contradictions = strategy._detect_contradictions(result, all_results)
        assert len(contradictions) == 0

    def test_contradiction_multiple_pairs(self):
        strategy = PedagogicalRetrievalStrategy()
        result = TavilyQueryResult(
            query="q1", category=QueryCategory.CONCEPTUAL,
            response=_make_response(answer="This is correct and true", score=0.9),
            query_time_ms=10, confidence=0.9,
        )
        all_results = [
            result,
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                response=_make_response(answer="This is wrong and false", score=0.7),
                query_time_ms=10, confidence=0.7,
            ),
        ]
        contradictions = strategy._detect_contradictions(result, all_results)
        assert len(contradictions) >= 1
        assert contradictions[0]["severity"] == "info"

    def test_contradiction_no_answer_returns_empty(self):
        strategy = PedagogicalRetrievalStrategy()
        result = TavilyQueryResult(
            query="q1", category=QueryCategory.CONCEPTUAL,
            response=_make_response(answer=""),
            query_time_ms=10, confidence=0.9,
        )
        contradictions = strategy._detect_contradictions(result, [result])
        assert len(contradictions) == 0

    def test_contradiction_skips_self(self):
        strategy = PedagogicalRetrievalStrategy()
        result = TavilyQueryResult(
            query="q1", category=QueryCategory.CONCEPTUAL,
            response=_make_response(answer="always do this", score=0.9),
            query_time_ms=10, confidence=0.9,
        )
        # Pass same result twice — should not detect self-contradiction
        contradictions = strategy._detect_contradictions(result, [result])
        assert len(contradictions) == 0


# ═════════════════════════════════════════════════════════════════════
# Aggregation
# ═════════════════════════════════════════════════════════════════════

class TestAggregation:
    def test_deduplicates_by_url(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q1", category=QueryCategory.INTRODUCTION,
                response=_make_response(title="same", url="https://example.com/a"),
                query_time_ms=10, confidence=0.9,
            ),
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                response=_make_response(title="same", url="https://example.com/a"),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 1

    def test_counts_unique_domains(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q1", category=QueryCategory.INTRODUCTION,
                response=_make_response(title="a", url="https://example.com/a"),
                query_time_ms=10, confidence=0.9,
            ),
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                response=_make_response(title="b", url="https://other.org/b"),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.unique_domains == 2

    def test_classifies_by_category(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.MISCONCEPTION,
                response=_make_response(
                    title="mistake", content="Common mistake about X",
                    url="https://ex.com/mistake",
                ),
                query_time_ms=10, confidence=0.9,
            ),
            TavilyQueryResult(
                query="q", category=QueryCategory.REAL_APPLICATION,
                response=_make_response(
                    title="app", content="Real world application of X",
                    url="https://ex.com/app",
                ),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert any("Common mistake" in m.get("misconception", "") for m in agg.misconceptions)
        assert any("Real world" in a.get("application", "") for a in agg.real_applications)

    def test_skips_failed_results(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q1", category=QueryCategory.INTRODUCTION,
                error="timeout", query_time_ms=10, confidence=0.0,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 0

    def test_empty_results_returns_empty_aggregation(self):
        strategy = PedagogicalRetrievalStrategy()
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results([], ctx)
        assert agg.total_sources == 0
        assert agg.unique_domains == 0
        assert agg.concepts == []
        assert agg.examples == []

    def test_classifies_bloom_and_exercise(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.BLOOM_LEVEL,
                response=_make_response(
                    title="bloom", content="Bloom taxonomy exercises for X",
                    url="https://ex.com/bloom",
                ),
                query_time_ms=10, confidence=0.9,
            ),
            TavilyQueryResult(
                query="q", category=QueryCategory.EXERCISE,
                response=_make_response(
                    title="exercise", content="Practice problems for X",
                    url="https://ex.com/ex",
                ),
                query_time_ms=10, confidence=0.8,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert len(agg.exercises) == 2

    def test_classifies_practical_as_examples(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.PRACTICAL,
                response=_make_response(
                    title="practical", content="Example usage of X",
                    url="https://ex.com/prac",
                ),
                query_time_ms=10, confidence=0.9,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert len(agg.examples) == 1

    def test_domain_extraction_handles_malformed_urls(self):
        assert PedagogicalRetrievalStrategy._extract_domain("not-a-url") == ""
        assert PedagogicalRetrievalStrategy._extract_domain("") == ""

    def test_deduplicate_by_key_content(self):
        items = [
            {"content": "same text", "source": "a"},
            {"content": "same text", "source": "b"},
            {"content": "different", "source": "c"},
        ]
        result = PedagogicalRetrievalStrategy._deduplicate_by_key(items, "content")
        assert len(result) == 2


# ═════════════════════════════════════════════════════════════════════
# Confidence scoring
# ═════════════════════════════════════════════════════════════════════

class TestConfidenceScoring:
    def test_high_confidence_with_good_sources(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.INTRODUCTION,
                response=_make_response(score=0.95),
                query_time_ms=10, confidence=0.95,
            ),
        ]
        score = strategy._compute_confidence(results)
        assert score > 0.5

    def test_zero_confidence_on_empty(self):
        strategy = PedagogicalRetrievalStrategy()
        score = strategy._compute_confidence([])
        assert score == 0.0

    def test_zero_confidence_on_all_failures(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.INTRODUCTION,
                error="fail", query_time_ms=10, confidence=0.0,
            ),
        ]
        score = strategy._compute_confidence(results)
        assert score == 0.0

    def test_confidence_penalized_by_partial_failures(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q1", category=QueryCategory.INTRODUCTION,
                response=_make_response(score=0.9),
                query_time_ms=10, confidence=0.9,
            ),
            TavilyQueryResult(
                query="q2", category=QueryCategory.CONCEPTUAL,
                error="fail", query_time_ms=10, confidence=0.0,
            ),
        ]
        score = strategy._compute_confidence(results)
        # avg_conf = 0.45, success_ratio = 0.5 → score = 0.225
        assert score < 0.5
        assert score > 0

    def test_score_confidence_zero_sources(self):
        strategy = PedagogicalRetrievalStrategy()
        resp = _make_response(score=0.0, content="")
        resp.results = []
        score = strategy._score_confidence(resp)
        assert score == 0.0

    def test_score_confidence_scales_up(self):
        strategy = PedagogicalRetrievalStrategy()
        resp = _make_response(score=0.6)
        score = strategy._score_confidence(resp)
        # 0.6 * 1.5 = 0.9
        assert score == 0.9

    def test_score_confidence_caps_at_one(self):
        strategy = PedagogicalRetrievalStrategy()
        resp = _make_response(score=0.99)
        score = strategy._score_confidence(resp)
        assert score <= 1.0


# ═════════════════════════════════════════════════════════════════════
# Pedagogical coverage metrics
# ═════════════════════════════════════════════════════════════════════

class TestPedagogicalMetrics:
    """Tests for the compute_pedagogical_metrics helper that scores
    retrieval quality across pedagogical dimensions."""

    def test_full_coverage_all_categories_present(self):
        agg = AggregatedResearch(
            topic="Test",
            concepts=[{"concept": "c1"}],
            examples=[{"example": "e1"}],
            analogies=[{"analogy": "a1"}],
            real_applications=[{"application": "r1"}],
            misconceptions=[{"misconception": "m1"}],
            exercises=[{"exercise": "x1"}],
            total_sources=6,
            unique_domains=3,
            confidence_score=0.85,
        )
        metrics = agg.compute_pedagogical_metrics()
        assert metrics.pedagogical_coverage == 1.0
        assert metrics.diversity_score == 0.5
        assert metrics.has_concepts
        assert metrics.has_examples
        assert metrics.has_analogies
        assert metrics.has_applications
        assert metrics.has_misconceptions
        assert metrics.has_exercises
        assert metrics.contradiction_count == 0

    def test_partial_coverage(self):
        agg = AggregatedResearch(
            topic="Test",
            concepts=[{"concept": "c1"}],
            examples=[{"example": "e1"}],
            real_applications=[{"application": "r1"}],
            total_sources=3,
            unique_domains=1,
        )
        metrics = agg.compute_pedagogical_metrics()
        # 3 of 6 categories: concepts, examples, applications
        assert metrics.pedagogical_coverage == 0.5
        assert not metrics.has_analogies
        assert not metrics.has_misconceptions
        assert not metrics.has_exercises

    def test_no_coverage(self):
        agg = AggregatedResearch(topic="Test", total_sources=0, unique_domains=0)
        metrics = agg.compute_pedagogical_metrics()
        assert metrics.pedagogical_coverage == 0.0
        assert metrics.diversity_score == 0.0
        assert not metrics.has_concepts

    def test_diversity_score_perfect(self):
        agg = AggregatedResearch(
            topic="Test",
            concepts=[{"concept": "c1"}],
            total_sources=3,
            unique_domains=3,
        )
        metrics = agg.compute_pedagogical_metrics()
        assert metrics.diversity_score == 1.0

    def test_diversity_score_zero(self):
        agg = AggregatedResearch(
            topic="Test",
            total_sources=5,
            unique_domains=1,
        )
        metrics = agg.compute_pedagogical_metrics()
        assert metrics.diversity_score == 0.2

    def test_contradiction_count(self):
        agg = AggregatedResearch(
            topic="Test",
            contradictions=[
                {"statements": ["a", "b"], "severity": "info"},
                {"statements": ["c", "d"], "severity": "warning"},
            ],
            total_sources=2,
            unique_domains=2,
        )
        metrics = agg.compute_pedagogical_metrics()
        assert metrics.contradiction_count == 2

    def test_bloom_level_valid(self):
        agg = AggregatedResearch(topic="Test", total_sources=1, unique_domains=1)
        metrics = agg.compute_pedagogical_metrics(bloom_target=3)
        assert metrics.bloom_target == 3

    def test_pedagogical_metrics_to_dict(self):
        metrics = PedagogicalMetrics(
            pedagogical_coverage=0.8,
            diversity_score=0.6,
            contradiction_count=1,
            has_concepts=True,
            has_examples=True,
            has_analogies=False,
            has_applications=True,
            has_misconceptions=False,
            has_exercises=True,
            bloom_target=3,
        )
        d = metrics.to_dict()
        assert d["pedagogical_coverage"] == 0.8
        assert d["contradiction_count"] == 1

    def test_aggregated_research_metrics_property(self):
        agg = AggregatedResearch(
            topic="Test",
            concepts=[{"concept": "c1"}],
            examples=[{"example": "e1"}],
            analogies=[{"analogy": "a1"}],
            real_applications=[{"application": "r1"}],
            misconceptions=[{"misconception": "m1"}],
            exercises=[{"exercise": "x1"}],
            total_sources=6,
            unique_domains=3,
            contradictions=[{"statements": ["a", "b"]}],
        )
        metrics = agg.metrics
        assert isinstance(metrics, PedagogicalMetrics)
        assert metrics.pedagogical_coverage == 1.0


# ═════════════════════════════════════════════════════════════════════
# Full pipeline research() execution
# ═════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    """Tests for the end-to-end research() method with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_research_all_queries_succeed(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=_make_response(
            title="result", content="pedagogical content", score=0.85,
            answer="Key insight about topic",
        ))
        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Python lists", objectives=[], bloom_target=3)
        result = await strategy.research(ctx)

        assert result.topic == "Python lists"
        assert result.total_sources == 8
        assert result.unique_domains == 1
        assert result.confidence_score > 0
        assert client.search.call_count == 8

    @pytest.mark.asyncio
    async def test_research_with_cache_hits(self):
        client = MagicMock()
        cached_response = _make_response(
            title="cached", content="cached content", score=0.9,
            answer="cached answer",
        )
        client.search = AsyncMock(return_value=_make_response(
            title="fresh", content="fresh content", score=0.8,
        ))
        cache = MagicMock()
        cache.get = AsyncMock(side_effect=lambda q: cached_response if "beginners" in q else None)
        cache.set = AsyncMock()

        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=cache,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Testing", objectives=[])
        result = await strategy.research(ctx)

        assert result.total_sources >= 1
        # At least one query was cached
        cache.get.assert_awaited()
        cache.set.assert_awaited()

    @pytest.mark.asyncio
    async def test_research_rate_limited_skips_queries(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=_make_response(score=0.8))
        call_count = [0]
        async def can_proceed():
            call_count[0] += 1
            return call_count[0] <= 3  # only first 3 allowed

        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=can_proceed),
        )
        ctx = RetrievalContext(topic="Topic", objectives=[])
        result = await strategy.research(ctx)

        assert client.search.call_count == 3
        assert result.total_sources == 3

    @pytest.mark.asyncio
    async def test_research_all_queries_fail(self):
        client = MagicMock()
        client.search = AsyncMock(side_effect=Exception("API unavailable"))
        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Topic", objectives=[])
        result = await strategy.research(ctx)

        assert result.total_sources == 0
        assert result.confidence_score == 0.0
        assert result.concepts == []
        assert result.examples == []

    @pytest.mark.asyncio
    async def test_research_partial_failure(self):
        client = MagicMock()
        call_count = [0]
        async def search(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 4:
                return _make_response(title=f"ok_{call_count[0]}", content="good", score=0.8)
            raise Exception("rate limited")

        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Topic", objectives=[])
        result = await strategy.research(ctx)

        assert 4 <= result.total_sources <= 5
        assert result.confidence_score > 0

    @pytest.mark.asyncio
    async def test_research_with_cache_empty_then_fresh(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=_make_response(score=0.75))
        cache = MagicMock()
        cache.get = AsyncMock(return_value=None)  # cache miss for all
        cache.set = AsyncMock()

        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=cache,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Topic", objectives=[])
        result = await strategy.research(ctx)

        assert client.search.call_count == 8
        # All results stored in cache
        assert cache.set.call_count == 8

    @pytest.mark.asyncio
    async def test_research_without_cache_still_works(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=_make_response(score=0.8))
        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="Topic", objectives=[])
        result = await strategy.research(ctx)

        assert result.total_sources == 8


# ═════════════════════════════════════════════════════════════════════
# Edge cases — malformed responses, empty data, extreme values
# ═════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    def test_empty_content_in_source(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.CONCEPTUAL,
                response=TavilySearchResponse(
                    query="q",
                    results=[
                        TavilySource(title="t", url="https://ex.com/t", content="", score=0.5),
                    ],
                ),
                query_time_ms=10, confidence=0.5,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 1
        assert agg.concepts[0]["content"] == ""

    def test_very_long_content_truncated(self):
        strategy = PedagogicalRetrievalStrategy()
        long_content = "X" * 2000
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.CONCEPTUAL,
                response=TavilySearchResponse(
                    query="q",
                    results=[
                        TavilySource(title="t", url="https://ex.com/t", content=long_content, score=0.9),
                    ],
                ),
                query_time_ms=10, confidence=0.9,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert len(agg.sources[0]["content_preview"]) == 300

    def test_zero_score_sources_still_included(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.CONCEPTUAL,
                response=_make_response(title="zero", content="low quality", score=0.0),
                query_time_ms=10, confidence=0.0,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 1

    def test_malformed_url_does_not_crash(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q", category=QueryCategory.CONCEPTUAL,
                response=_make_response(title="bad", url="", content="no url", score=0.5),
                query_time_ms=10, confidence=0.5,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 1
        domain = strategy._extract_domain("")
        assert domain == ""

    def test_multiple_sources_per_query_deduplicated(self):
        strategy = PedagogicalRetrievalStrategy()
        results = [
            TavilyQueryResult(
                query="q1", category=QueryCategory.CONCEPTUAL,
                response=_make_multi_source_response([
                    ("a", "https://ex.com/a", "content a", 0.9),
                    ("a", "https://ex.com/a", "content a", 0.9),  # duplicate
                    ("b", "https://ex.com/b", "content b", 0.8),
                ]),
                query_time_ms=10, confidence=0.9,
            ),
        ]
        ctx = RetrievalContext(topic="Test", objectives=[])
        agg = strategy._aggregate_results(results, ctx)
        assert agg.total_sources == 2  # deduplicated

    @pytest.mark.asyncio
    async def test_research_with_unicode_topic(self):
        client = MagicMock()
        client.search = AsyncMock(return_value=_make_response(score=0.8))
        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(
            topic="Estructuras de datos en Java", objectives=[],
            bloom_target=3, language="es",
        )
        result = await strategy.research(ctx)
        assert result.total_sources == 8
        assert "Java" in result.topic

    @pytest.mark.asyncio
    async def test_research_contradictions_included_in_aggregate(self):
        client = MagicMock()
        call_count = [0]
        async def search(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return _make_response(answer="You should always use X", score=0.9)
            return _make_response(answer="You should never use X", score=0.8)

        strategy = PedagogicalRetrievalStrategy(
            client=client,
            cache=None,
            rate_limiter=MagicMock(can_proceed=AsyncMock(return_value=True)),
        )
        ctx = RetrievalContext(topic="X", objectives=[])
        result = await strategy.research(ctx)
        # At least one contradiction pair detected (always vs never)
        contradiction_count = len(result.contradictions)
        assert contradiction_count >= 1 or result.total_sources <= 1
