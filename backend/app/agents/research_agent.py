"""ResearchAgent — investiga contenido usando Tavily Search API con estrategia pedagógica."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
import time
from typing import Any

from app.agents.base import BaseAgent
from app.integrations.tavily.cache import TavilyCache, get_tavily_cache
from app.integrations.tavily.observability import get_tavily_diagnostics
from app.integrations.tavily.rate_limit import get_rate_limiter_chain
from app.integrations.tavily.retrieval import PedagogicalRetrievalStrategy
from app.integrations.tavily.schemas import AggregatedResearch, RetrievalContext, SearchDepth

logger = logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Investiga contenido automáticamente usando Tavily + LLM con estrategia pedagógica.

    Responsabilidades:
    - Investigar contenido del tema (Tavily multi-query + LLM fallback)
    - Buscar ejemplos relevantes, aplicaciones reales, analogías
    - Detectar conceptos clave, subconceptos, dificultades comunes
    - Buscar referencias educativas
    - Degradación elegante si Tavily no está disponible

    Publica en shared memory:
    - research:findings — hallazgos completos
    - research:examples — ejemplos seleccionados
    - research:analogies — analogías identificadas
    - research:concepts — conceptos clave extraídos
    - research:retrieval — resultado agregado de Tavily
    """

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._retrieval: PedagogicalRetrievalStrategy | None = None
        self._degraded: bool = False

    @property
    def agent_type(self) -> str:
        return "research"

    def _init_retrieval(self) -> PedagogicalRetrievalStrategy:
        if self._retrieval is None:
            from app.integrations.tavily.client import get_tavily_client

            self._retrieval = PedagogicalRetrievalStrategy(
                client=get_tavily_client(),
                cache=get_tavily_cache(),
                rate_limiter=get_rate_limiter_chain(),
            )
        return self._retrieval

    async def analyze(self, state: dict[str, Any]) -> dict[str, Any]:
        topic = state.get("topic", "")
        objectives = state.get("learning_objectives", [])
        syllabus = state.get("syllabus", "")
        bloom_target = state.get("bloom_target", 3)

        start_time = time.monotonic()
        aggregated: AggregatedResearch | None = None

        # Phase 1: Tavily retrieval (real Web search)
        try:
            retrieval = self._init_retrieval()
            context = RetrievalContext(
                topic=topic,
                objectives=objectives,
                syllabus=syllabus[:1000],
                bloom_target=bloom_target,
                search_depth=SearchDepth.BASIC,
            )
            aggregated = await retrieval.research(context)
            logger.info(
                "Tavily retrieval: %d sources, %d domains, confidence=%.2f",
                aggregated.total_sources, aggregated.unique_domains, aggregated.confidence_score,
            )
        except Exception as e:
            logger.warning("Tavily retrieval failed, falling back to LLM research: %s", e)
            self._degraded = True
            get_tavily_diagnostics().research_degraded(topic, str(e)[:200])

        # Phase 2: LLM enrichment (always, to complement retrieval)
        llm_findings = await self._research_topic(topic, objectives, syllabus)

        # Merge Tavily + LLM into unified result
        result = self._merge_results(topic, aggregated, llm_findings, objectives, syllabus)

        elapsed_ms = (time.monotonic() - start_time) * 1000
        result["research_duration_ms"] = round(elapsed_ms, 2)
        result["degraded"] = self._degraded

        # Publish to shared memory
        await self.publish_observation(
            f"{self.context_key}:research:findings",
            result,
            memory_type="inference",
            confidence=result.get("confidence", 0.7),
        )

        return result

    def _merge_results(
        self,
        topic: str,
        aggregated: AggregatedResearch | None,
        llm_findings: list[dict[str, Any]],
        objectives: list[str],
        syllabus: str,
    ) -> dict[str, Any]:
        # Build examples from Tavily + LLM
        examples: list[str] = []
        if aggregated and aggregated.examples:
            examples = [e.get("example", "") for e in aggregated.examples if e.get("example")]
        if not examples:
            for f in llm_findings:
                if f.get("category") in ("ejemplos", "examples", "conceptos", "conexiones"):
                    examples.append(f["content"])
        if not examples:
            examples.append(f"Ejemplo ilustrativo del concepto: {topic}")

        # Analogies
        analogies: list[str] = []
        if aggregated and aggregated.analogies:
            analogies = [a.get("analogy", "") for a in aggregated.analogies if a.get("analogy")]
        if not analogies:
            for f in llm_findings:
                if f.get("category") in ("estrategias", "analogías"):
                    analogies.append(f["content"])
        if not analogies:
            analogies.append(f"Analogía pedagógica para explicar {topic}")

        # Real applications
        real_applications: list[str] = []
        if aggregated and aggregated.real_applications:
            real_applications = [
                a.get("application", "") for a in aggregated.real_applications if a.get("application")
            ]
        if not real_applications:
            for f in llm_findings:
                if f.get("category") in ("aplicaciones", "conexiones", "subtemas"):
                    real_applications.append(f["content"])
        if not real_applications:
            real_applications.append(f"Aplicación práctica de {topic} en contexto real")

        # Concepts
        concepts: list[str] = []
        if aggregated and aggregated.concepts:
            concepts = [c.get("concept", "") for c in aggregated.concepts if c.get("concept")]
        if not concepts:
            for f in llm_findings:
                if f.get("category") in ("conceptos", "subtemas"):
                    concepts.append(f["content"])

        # Misconceptions
        misconceptions: list[str] = []
        if aggregated and aggregated.misconceptions:
            misconceptions = [
                m.get("misconception", "") for m in aggregated.misconceptions if m.get("misconception")
            ]

        # Contradictions
        contradictions: list[dict] = []
        if aggregated and aggregated.contradictions:
            contradictions = aggregated.contradictions

        # Sources
        sources: list[dict] = []
        if aggregated and aggregated.sources:
            sources = aggregated.sources

        findings = llm_findings

        confidence = aggregated.confidence_score if aggregated else 0.5

        return {
            "topic": topic,
            "findings": findings,
            "examples": examples[:5],
            "real_applications": real_applications[:5],
            "analogies": analogies[:3],
            "concepts": concepts[:10],
            "misconceptions": misconceptions[:5],
            "contradictions": contradictions[:5],
            "sources": sources[:20],
            "retrieval": asdict(aggregated) if aggregated else None,
            "confidence": confidence,
            "summary": self._build_summary(topic, findings, examples, analogies),
            "finding_count": len(findings),
        }

    async def _research_topic(self, topic: str, objectives: list[str], syllabus: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        llm_result = await self._call_llm_for_research(topic, objectives, syllabus)

        if llm_result:
            try:
                data = llm_result.get("parsed") or json.loads(llm_result.get("content", "{}"))
                if isinstance(data, dict):
                    for category_key in ("conceptos", "subtemas", "conexiones", "dificultades", "estrategias"):
                        items = data.get(category_key, [])
                        if isinstance(items, list):
                            for item in items:
                                text = str(item) if not isinstance(item, str) else item
                                findings.append({
                                    "source": "llm_research",
                                    "content": text,
                                    "relevance": 0.8,
                                    "category": category_key,
                                })
            except (json.JSONDecodeError, TypeError, AttributeError):
                findings.append({
                    "source": "llm_research",
                    "content": llm_result.get("content", "")[:500],
                    "relevance": 0.7,
                    "category": "general",
                })

        if not findings:
            findings.append({
                "source": "heuristic",
                "content": f"Investigación base sobre: {topic}",
                "relevance": 0.5,
                "category": "general",
            })

        return findings

    async def _call_llm_for_research(self, topic: str, objectives: list[str], syllabus: str) -> dict | None:
        try:
            from app.llm.service import LLMService
            from app.llm.config import LLMConfig, ProviderKind

            service = LLMService()
            prompt = (
                f"Investiga el siguiente tema educativo: '{topic}'.\n"
                f"Objetivos: {', '.join(objectives) if objectives else 'No especificados'}\n"
                f"Sílabo: {syllabus[:500] if syllabus else 'No disponible'}\n\n"
                "Proporciona un análisis estructurado en JSON con:\n"
                '{{"conceptos": ["concepto1", "concepto2"],\n'
                '"subtemas": ["subtema1", "subtema2"],\n'
                '"conexiones": ["conexión1"],\n'
                '"dificultades": ["dificultad común 1"],\n'
                '"estrategias": ["estrategia de enseñanza 1"]}}'
            )

            response = await service.generate(
                messages=[
                    {"role": "system", "content": "Eres un investigador educativo experto en pedagogía y diseño instruccional. Respondes SOLO con JSON válido."},
                    {"role": "user", "content": prompt},
                ],
                voter_name="research",
                response_format="json",
            )
            return {
                "content": response.content,
                "parsed": response.parsed,
                "success": response.success,
            }
        except Exception as e:
            logger.debug("LLM research call failed: %s", e)
            return None

    def _build_summary(self, topic: str, findings: list[dict], examples: list[str], analogies: list[str]) -> str:
        return (
            f"Investigación completada para '{topic}': "
            f"{len(findings)} hallazgos, {len(examples)} ejemplos, {len(analogies)} analogías."
        )
