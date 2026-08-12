"""Tests for ResearchAgent contra el contrato vigente (sin BaseAgent).

C2 (F2/F4, Gates C2-D/C2-E, 2026-08-12): los 7 tests originales de este
archivo asumían una versión de ResearchAgent(BaseAgent) — constructor
agent_name/uow/context_key, fallback heurístico vía LLM cuando Tavily
fallaba — retirada antes del 2026-07-13 sin que el test se actualizara.

De los 7:
  - test_publishes_to_shared_memory, test_degraded_flag_when_tavily_fails,
    test_with_tavily_results: retirados, cobertura equivalente ya
    demostrada en test_pedagogical_research_pipeline.py
    (test_research_agent_publishes_memory_and_consensus_payload,
    test_tavily_unavailable_degrades_without_hallucinated_sources).
  - test_fallback_when_llm_fails, test_examples_from_llm_findings:
    retirados -- protegían el fallback heurístico vía LLM, retirado
    formalmente por ADR-0018 (sin fuentes verificables, riesgo de
    contenido no fundamentado; ningún caller real depende de él).
  - test_analyze_returns_expected_keys, test_confidence_default_when_no_tavily:
    reescritos abajo contra el contrato vigente (mismo patrón que
    test_pedagogical_research_pipeline.py).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.services.research_agent import ResearchAgent


@pytest.mark.asyncio
async def test_analyze_returns_expected_keys():
    """analyze() siempre devuelve las 5 claves de nivel superior del
    contrato vigente, incluso cuando Tavily no está disponible."""
    client = MagicMock()
    client.search = AsyncMock(side_effect=RuntimeError("Tavily unavailable"))
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None, timeout_seconds=1)
    agent = ResearchAgent(retrieval_strategy=strategy)

    state = await agent.analyze({
        "topic": "Binary Search Trees",
        "objectives": ["Understand BST"],
    })

    assert "research" in state
    assert "research_metrics" in state
    assert "consistency_validation" in state
    assert "memory_ids" in state
    assert "consensus_payload" in state
    assert state["research"]["topic"] == "Binary Search Trees"
    assert state["research"]["degraded"] is True


@pytest.mark.asyncio
async def test_confidence_default_when_no_tavily():
    """Sin Tavily disponible, la confianza degrada a 0.0 -- no a un
    valor por defecto no nulo (el diseño anterior usaba 0.5; el vigente
    trata la ausencia total de evidencia como confianza cero, mismo
    principio que evidence_strength/D3 en otras capacidades del
    sistema)."""
    client = MagicMock()
    client.search = AsyncMock(side_effect=RuntimeError("Tavily unavailable"))
    strategy = PedagogicalRetrievalStrategy(client=client, cache=None, timeout_seconds=1)
    agent = ResearchAgent(retrieval_strategy=strategy)

    state = await agent.analyze({"topic": "OOP"})

    assert state["research"]["confidence_score"] == 0.0
