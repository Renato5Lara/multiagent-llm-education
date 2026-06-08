"""Tests for ResearchAgent with Tavily integration: pipeline, fallback, shared memory publishing."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.research_agent import ResearchAgent
from app.db.uow import UnitOfWork
from app.integrations.tavily.schemas import AggregatedResearch


@pytest.fixture
def mock_uow():
    return MagicMock(spec=UnitOfWork)


@pytest.fixture
def agent(mock_uow):
    return ResearchAgent(
        agent_name="research_test",
        uow=mock_uow,
        student_id="test_student",
        course_id="test_course",
        context_key="test",
    )


@pytest.fixture
def mock_tavily_disabled(agent):
    """Mock _init_retrieval to raise an exception, forcing LLM/heuristic fallback."""
    with patch.object(agent, "_init_retrieval", side_effect=Exception("Tavily unavailable")):
        yield agent


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_analyze_returns_expected_keys(self, mock_tavily_disabled):
        agent = mock_tavily_disabled
        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            result = await agent.analyze({
                "topic": "Binary Search Trees",
                "learning_objectives": ["Understand BST"],
                "syllabus": "",
            })

        assert "topic" in result
        assert "findings" in result
        assert "examples" in result
        assert "real_applications" in result
        assert "analogies" in result
        assert "concepts" in result
        assert "summary" in result
        assert "confidence" in result
        assert "research_duration_ms" in result
        assert result["topic"] == "Binary Search Trees"
        assert result["degraded"] is True

    @pytest.mark.asyncio
    async def test_publishes_to_shared_memory(self, agent):
        agent.shared_memory = MagicMock()
        mock_retrieval = MagicMock()
        mock_retrieval.research = AsyncMock(return_value=AggregatedResearch(topic="Sorting Algorithms"))
        agent._retrieval = mock_retrieval

        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            await agent.analyze({
                "topic": "Sorting Algorithms",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert agent.shared_memory.publish_observation.called

    @pytest.mark.asyncio
    async def test_fallback_when_llm_fails(self, mock_tavily_disabled):
        agent = mock_tavily_disabled
        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            result = await agent.analyze({
                "topic": "Python Lists",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert len(result["findings"]) >= 1
        assert result["findings"][0]["source"] == "heuristic"

    @pytest.mark.asyncio
    async def test_examples_from_llm_findings(self, mock_tavily_disabled):
        agent = mock_tavily_disabled
        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value={
            "content": '{"conceptos": ["lista", "tupla"], "ejemplos": ["[1,2,3]"]}',
            "parsed": None,
            "success": True,
        })):
            result = await agent.analyze({
                "topic": "Python Lists",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert len(result["findings"]) > 0

    @pytest.mark.asyncio
    async def test_confidence_default_when_no_tavily(self, mock_tavily_disabled):
        agent = mock_tavily_disabled
        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            result = await agent.analyze({
                "topic": "OOP",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert result["confidence"] == 0.5

    @pytest.mark.asyncio
    async def test_degraded_flag_when_tavily_fails(self, mock_tavily_disabled):
        agent = mock_tavily_disabled
        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            result = await agent.analyze({
                "topic": "OOP",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert result["degraded"] is True

    @pytest.mark.asyncio
    async def test_with_tavily_results(self, agent):
        agent.shared_memory = MagicMock()
        mock_retrieval = MagicMock()
        agg = AggregatedResearch(
            topic="Python",
            concepts=[{"concept": "variable", "source_title": "t1", "content": "def", "domain": "ex.com", "confidence": 0.9}],
            examples=[{"example": "x = 1", "source": "t1", "domain": "ex.com"}],
            analogies=[{"analogy": "box with label", "source": "t2"}],
            real_applications=[{"application": "data science", "source": "t3"}],
            misconceptions=[{"misconception": "dynamic typing is slow", "source": "t4"}],
            total_sources=4,
            unique_domains=2,
            confidence_score=0.85,
        )
        mock_retrieval.research = AsyncMock(return_value=agg)
        agent._retrieval = mock_retrieval

        with patch.object(agent, "_call_llm_for_research", new=AsyncMock(return_value=None)):
            result = await agent.analyze({
                "topic": "Python",
                "learning_objectives": [],
                "syllabus": "",
            })

        assert result["confidence"] == 0.85
        assert len(result["examples"]) == 1
        assert len(result["concepts"]) == 1
        assert len(result["analogies"]) == 1
        assert len(result["real_applications"]) == 1
        assert len(result["misconceptions"]) == 1
        assert result["retrieval"] is not None
        assert result["degraded"] is False
