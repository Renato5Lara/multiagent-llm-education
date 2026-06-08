from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.research_agent import ResearchAgent
from app.db.uow import UnitOfWork
from app.integrations.tavily.cache import TavilyCache
from app.integrations.tavily.client import TavilyClient
from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import (
    AggregatedResearch,
    QueryCategory,
    RetrievalContext,
    TavilySearchResponse,
    TavilySource,
)
from app.memory.shared_memory import SharedMemoryStore


def make_response(
    *,
    title: str = "Arrays tutorial",
    url: str = "https://example.edu/arrays",
    content: str = "Arrays store indexed values and support traversal, search, and insertion.",
    score: float = 0.82,
    answer: str = "Arrays are indexed collections.",
) -> TavilySearchResponse:
    return TavilySearchResponse(
        query="arrays",
        results=[TavilySource(title=title, url=url, content=content, score=score)],
        answer=answer,
        response_time_ms=12,
    )


def make_multi_response(domain: str, idx: int, category_hint: str = "") -> TavilySearchResponse:
    return make_response(
        title=f"Arrays source {idx}",
        url=f"https://{domain}/arrays/{idx}",
        content=(
            f"{category_hint} Arrays in programming can be traversed with loops, "
            "searched by comparing elements, and inserted by shifting positions."
        ),
        score=0.72 + (idx % 3) * 0.08,
        answer=f"Source {idx} explains arrays with traversal, search, and insertion.",
    )


@pytest.mark.asyncio
async def test_real_case_arrays_generates_queries_and_metrics():
    calls: list[str] = []

    async def search(query: str, **kwargs):
        calls.append(query)
        domain = ["example.edu", "docs.python.org", "cs.university.edu", "developer.mozilla.org"][len(calls) % 4]
        return make_multi_response(domain, len(calls), category_hint=query)

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None, timeout_seconds=1)

    context = RetrievalContext(
        topic="Arreglos en programacion",
        objectives=["comprender recorrido", "comprender busqueda", "comprender insercion"],
        bloom_target=3,
    )

    result = await strategy.research(context)
    metrics = result.compute_pedagogical_metrics(bloom_target=3)

    assert len(calls) == 8
    assert any("recorrido" in q for q in calls)
    assert any("busqueda" in q for q in calls)
    assert any("insercion" in q for q in calls)
    assert result.total_sources == 8
    assert result.unique_domains >= 3
    assert result.concepts
    assert result.examples
    assert result.misconceptions
    assert result.real_applications
    assert result.exercises
    assert result.multimodal_prompts
    assert metrics.retrieval_confidence > 0.45
    assert metrics.pedagogical_confidence > 0.55
    assert metrics.diversity_score >= 0.35
    assert metrics.prompt_grounding_score == 1.0
    assert metrics.misconception_coverage > 0
    assert metrics.bloom_alignment_score == 1.0


@pytest.mark.asyncio
async def test_tavily_unavailable_degrades_without_hallucinated_sources():
    client = MagicMock()
    client.search = AsyncMock(side_effect=RuntimeError("Tavily unavailable"))
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None, timeout_seconds=1)

    result = await strategy.research(RetrievalContext(topic="Arreglos en programacion"))

    assert result.degraded is True
    assert result.total_sources == 0
    assert result.confidence_score == 0.0
    assert result.concepts == []
    assert all(q.error for q in result.query_results)


@pytest.mark.asyncio
async def test_cache_only_mode_uses_cache_and_marks_misses_degraded():
    cache = TavilyCache()
    strategy_for_queries = PedagogicalRetrievalStrategy(client=MagicMock(), cache=cache)
    context = RetrievalContext(topic="Arreglos en programacion")
    first_query, _ = strategy_for_queries._generate_queries(context)[0]
    await cache.set(first_query, make_response(title="Cached arrays", url="https://cache.edu/arrays"))

    client = MagicMock()
    client.search = AsyncMock()
    strategy = PedagogicalRetrievalStrategy(client=client, cache=cache)

    result = await strategy.research(context, cache_only=True)

    assert result.total_sources == 1
    assert result.degraded is True
    assert client.search.await_count == 0
    assert any(q.cached for q in result.query_results)
    assert sum(1 for q in result.query_results if q.error == "cache_miss") == 7


@pytest.mark.asyncio
async def test_conflicting_sources_are_reported_and_lower_consistency():
    async def search(query: str, **kwargs):
        if "introdu" in query:
            return make_response(answer="Arrays should always be resized in place.", url="https://a.edu/always")
        return make_response(answer="Arrays should never be resized in place.", url=f"https://b.edu/{abs(hash(query))}")

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None)

    result = await strategy.research(RetrievalContext(topic="Arrays"))
    metrics = result.metrics

    assert result.contradictions
    assert metrics.contradiction_count >= 1
    assert metrics.contradiction_score < 1.0


@pytest.mark.asyncio
async def test_repeated_retrieval_is_deduplicated_semantically_and_by_url():
    duplicate = make_response(
        title="Same arrays",
        url="https://same.edu/arrays",
        content="Arrays traversal search insertion same duplicated content.",
        score=0.9,
    )
    client = MagicMock()
    client.search = AsyncMock(return_value=duplicate)
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None)

    result = await strategy.research(RetrievalContext(topic="Arrays"))

    assert result.total_sources == 1
    assert result.metrics.semantic_redundancy_score == 0.0


@pytest.mark.asyncio
async def test_low_diversity_retrieval_is_measurable():
    async def search(query: str, **kwargs):
        return make_response(
            title=f"Arrays {query[:12]}",
            url=f"https://single-domain.edu/{abs(hash(query))}",
            content=f"Unique content for {query} with traversal search insertion.",
            score=0.8,
        )

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None)

    result = await strategy.research(RetrievalContext(topic="Arrays"))

    assert result.total_sources == 8
    assert result.unique_domains == 1
    assert result.metrics.diversity_score == pytest.approx(0.125)


def test_malformed_tavily_response_is_safely_parsed():
    parsed = TavilySearchResponse.from_mapping(
        {"answer": None, "results": {"bad": "shape"}},
        query="bad response",
    )

    assert parsed.query == "bad response"
    assert parsed.results == []
    assert parsed.answer == ""


@pytest.mark.asyncio
async def test_async_concurrency_and_timeout_scenarios():
    started = 0

    async def search(query: str, **kwargs):
        nonlocal started
        started += 1
        await asyncio.sleep(0.05)
        return make_response(url=f"https://timeout.edu/{abs(hash(query))}")

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    strategy = PedagogicalRetrievalStrategy(
        client=client,
        cache=None,
        timeout_seconds=0.01,
        max_concurrency=8,
    )

    result = await strategy.research(RetrievalContext(topic="Arrays"))

    assert started == 8
    assert result.total_sources == 0
    assert all(q.error == "timeout" for q in result.query_results)


@pytest.mark.asyncio
async def test_research_agent_publishes_memory_and_consensus_payload(db):
    async def search(query: str, **kwargs):
        domains = {
            QueryCategory.INTRODUCTION.value: "intro.edu",
            QueryCategory.CONCEPTUAL.value: "concept.edu",
        }
        domain = "agent.edu"
        for category in QueryCategory:
            if category.value in query:
                domain = domains.get(category.value, "agent.edu")
        return make_response(
            title=f"Grounded {query[:20]}",
            url=f"https://{domain}/{abs(hash(query))}",
            content=f"Grounded source for {query}: traversal, search, insertion, misconceptions, applications.",
            score=0.88,
        )

    client = MagicMock()
    client.search = AsyncMock(side_effect=search)
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None)
    uow = UnitOfWork(lambda: db)
    store = SharedMemoryStore(uow)
    agent = ResearchAgent(retrieval_strategy=strategy, shared_memory_store=store)

    state = await agent.analyze(
        {
            "topic": "Arreglos en programacion",
            "objectives": ["comprender recorrido", "comprender busqueda", "comprender insercion"],
            "bloom_target": 3,
            "student_id": "stu-arrays",
            "module_id": "mod-arrays",
        }
    )
    uow.commit()

    assert state["research"]["total_sources"] == 8
    assert state["research_metrics"]["prompt_grounding_score"] == 1.0
    assert state["memory_ids"]
    assert state["consensus_payload"]["voter_name"] == "research_agent"
    assert state["consensus_payload"]["decision"] in {"approve", "abstain"}

    records = store.query(student_id="stu-arrays", module_id="mod-arrays", memory_type="research")
    assert {record.key for record in records} >= {
        "research:summary",
        "research:metrics",
        "research:misconceptions",
    }


def test_research_agent_validation_detects_bloom_and_grounding_gaps():
    agent = ResearchAgent(retrieval_strategy=MagicMock())
    research = AggregatedResearch(
        topic="Arrays",
        concepts=[{"concept": "Arrays"}],
        total_sources=1,
        unique_domains=1,
        confidence_score=0.7,
    )

    validation = agent._validate_consistency(research, RetrievalContext(topic="Arrays", bloom_target=4))

    issue_types = {issue["type"] for issue in validation["issues"]}
    assert "weak_misconception_coverage" in issue_types
    assert "bloom_alignment_gap" in issue_types
    assert "weak_prompt_grounding" in issue_types


@pytest.mark.asyncio
async def test_no_asyncio_run_or_nested_loop_in_research_path():
    import ast
    from pathlib import Path

    files = [
        Path("app/agents/research_agent.py"),
        Path("app/integrations/tavily/retrieval.py"),
        Path("app/integrations/tavily/client.py"),
    ]
    forbidden = {"asyncio.run", "run_until_complete", "new_event_loop"}
    found: list[str] = []
    root = Path(__file__).resolve().parents[1]

    for relative in files:
        tree = ast.parse((root / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    name = f"{getattr(node.func.value, 'id', '')}.{node.func.attr}"
                elif isinstance(node.func, ast.Name):
                    name = node.func.id
                else:
                    name = ""
                if name in forbidden or node.func.__class__.__name__ in forbidden:
                    found.append(f"{relative}:{name}")

    assert found == []
