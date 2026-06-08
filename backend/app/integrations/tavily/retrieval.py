"""Pedagogical retrieval strategy with cache, consistency checks, and metrics."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse

from app.integrations.tavily.cache import TavilyCache
from app.integrations.tavily.client import TavilyClient
from app.integrations.tavily.schemas import (
    AggregatedResearch,
    QueryCategory,
    RetrievalContext,
    TavilyQueryResult,
    TavilySearchResponse,
    TavilySource,
)


class PedagogicalRetrievalStrategy:
    def __init__(
        self,
        *,
        client: TavilyClient | None = None,
        cache: TavilyCache | None = None,
        rate_limiter: object | None = None,
        timeout_seconds: float = 10.0,
        max_concurrency: int = 4,
    ):
        self.client = client or TavilyClient()
        self.cache = cache if cache is not None else TavilyCache()
        self.rate_limiter = rate_limiter
        self.timeout_seconds = timeout_seconds
        self.max_concurrency = max(1, max_concurrency)

    async def research(self, context: RetrievalContext, *, cache_only: bool = False) -> AggregatedResearch:
        query_specs = self._generate_queries(context)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def run_one(query: str, category: QueryCategory) -> TavilyQueryResult:
            async with semaphore:
                return await self._execute_query(query, category, context, cache_only=cache_only)

        results = await asyncio.gather(
            *(run_one(query, category) for query, category in query_specs),
            return_exceptions=False,
        )
        return self._aggregate_results(results, context)

    def _generate_queries(self, context: RetrievalContext) -> list[tuple[str, QueryCategory]]:
        topic = context.topic.strip()
        objectives = ", ".join(context.objectives) if context.objectives else "recorrido, busqueda e insercion"

        ls = (context.learning_style or "").strip().lower()
        analogies = context.preferred_analogies or []
        vis = " diagramas graficos visuales" if ls == "visual" else " explicacion textual" if ls == "reading" else ""
        analogy_tag = f" {analogies[0]}" if analogies else ""

        return [
            (f"{topic} explicacion introductoria para principiantes programacion{vis}", QueryCategory.INTRODUCTION),
            (f"{topic} conceptos fundamentales{vis} recorrido busqueda insercion", QueryCategory.CONCEPTUAL),
            (f"{topic} ejemplos codigo{analogy_tag} recorrido busqueda insercion", QueryCategory.PRACTICAL),
            (f"{topic} errores comunes misconceptions estudiantes programacion", QueryCategory.MISCONCEPTION),
            (f"{topic} aplicaciones reales{analogy_tag} software estructuras de datos", QueryCategory.REAL_APPLICATION),
            (f"{topic} actividades Bloom nivel {context.bloom_target} objetivos {objectives}", QueryCategory.BLOOM_LEVEL),
            (f"{topic} ejercicios practica guiada{vis} recorrido busqueda insercion", QueryCategory.EXERCISE),
            (f"{topic} prompts multimodales{vis} diagramas simulacion visual codigo", QueryCategory.MULTIMODAL),
        ]

    async def _execute_query(
        self,
        query: str,
        category: QueryCategory,
        context: RetrievalContext,
        *,
        cache_only: bool,
    ) -> TavilyQueryResult:
        started = time.perf_counter()
        cached = await self._cache_get(query)
        if cached is not None:
            return TavilyQueryResult(
                query=query,
                category=category,
                response=cached,
                query_time_ms=(time.perf_counter() - started) * 1000,
                confidence=self._score_confidence(cached),
                cached=True,
            )
        if cache_only:
            return TavilyQueryResult(
                query=query,
                category=category,
                query_time_ms=(time.perf_counter() - started) * 1000,
                confidence=0.0,
                degraded=True,
                error="cache_miss",
            )
        if not await self._can_proceed():
            return TavilyQueryResult(
                query=query,
                category=category,
                query_time_ms=(time.perf_counter() - started) * 1000,
                confidence=0.0,
                degraded=True,
                error="rate_limited",
            )
        try:
            response = await asyncio.wait_for(
                self.client.search(
                    query,
                    max_results=context.max_results_per_query,
                    search_depth=context.search_depth,
                    include_answer=True,
                ),
                timeout=self.timeout_seconds,
            )
            await self._cache_set(query, response)
            return TavilyQueryResult(
                query=query,
                category=category,
                response=response,
                query_time_ms=(time.perf_counter() - started) * 1000,
                confidence=self._score_confidence(response),
            )
        except asyncio.TimeoutError:
            error = "timeout"
        except Exception as exc:
            error = str(exc)
        return TavilyQueryResult(
            query=query,
            category=category,
            query_time_ms=(time.perf_counter() - started) * 1000,
            confidence=0.0,
            degraded=True,
            error=error,
        )

    def _aggregate_results(self, results: list[TavilyQueryResult], context: RetrievalContext) -> AggregatedResearch:
        aggregate = AggregatedResearch(topic=context.topic, query_results=results)
        seen_urls: set[str] = set()
        seen_content: set[str] = set()

        for result in results:
            if not result.ok or result.response is None:
                aggregate.degraded = True
                continue
            aggregate.contradictions.extend(self._detect_contradictions(result, results))
            for source in result.response.results:
                source_key = source.url.strip().lower()
                content_key = self._normalize_content(source.content)
                if (source_key and source_key in seen_urls) or (content_key and content_key in seen_content):
                    continue
                if source_key:
                    seen_urls.add(source_key)
                if content_key:
                    seen_content.add(content_key)
                source_item = self._source_item(source, result.category, context.bloom_target)
                aggregate.sources.append(source_item)
                self._classify_source(aggregate, source_item, result.category, context.bloom_target)

        aggregate.total_sources = len(aggregate.sources)
        aggregate.unique_domains = len({s["domain"] for s in aggregate.sources if s.get("domain")})
        aggregate.confidence_score = self._compute_confidence(results)
        aggregate.contradictions = self._deduplicate_by_key(aggregate.contradictions, "fingerprint")
        aggregate.multimodal_prompts = self._build_multimodal_prompts(aggregate, context)
        return aggregate

    def _classify_source(
        self,
        aggregate: AggregatedResearch,
        item: dict,
        category: QueryCategory,
        bloom_target: int,
    ) -> None:
        if category in {QueryCategory.INTRODUCTION, QueryCategory.CONCEPTUAL}:
            aggregate.concepts.append({"concept": item["title"], **item})
        elif category == QueryCategory.PRACTICAL:
            aggregate.examples.append({"example": item["content_preview"], **item})
        elif category == QueryCategory.MISCONCEPTION:
            aggregate.misconceptions.append({"misconception": item["content_preview"], **item})
        elif category == QueryCategory.REAL_APPLICATION:
            aggregate.real_applications.append({"application": item["content_preview"], **item})
        elif category in {QueryCategory.BLOOM_LEVEL, QueryCategory.EXERCISE}:
            aggregate.exercises.append({"exercise": item["content_preview"], "bloom_level": bloom_target, **item})
        elif category == QueryCategory.MULTIMODAL:
            aggregate.multimodal_prompts.append({"prompt": item["content_preview"], **item})

    def _build_multimodal_prompts(self, aggregate: AggregatedResearch, context: RetrievalContext) -> list[dict]:
        anchors = aggregate.concepts[:2] + aggregate.examples[:2] + aggregate.real_applications[:1]
        prompts: list[dict] = []
        for index, anchor in enumerate(anchors[:4], start=1):
            modality = ["image", "text", "video", "audio"][min(index - 1, 3)]
            prompts.append(
                {
                    "id": f"prompt-{index}",
                    "modality": modality,
                    "prompt": self._prompt_for_modality(modality, context, anchor),
                    "bloom_level": context.bloom_target,
                    "grounded_sources": [anchor.get("url")] if anchor.get("url") else [],
                    "source_url": anchor.get("url", ""),
                }
            )
        return prompts

    def _prompt_for_modality(self, modality: str, context: RetrievalContext, anchor: dict) -> str:
        source_title = anchor.get("title") or "fuente recuperada"
        objectives = ", ".join(context.objectives) if context.objectives else "recorrido, busqueda e insercion"
        if modality == "image":
            return f"Crea un diagrama paso a paso de {context.topic} usando la idea de {source_title}; objetivos: {objectives}."
        if modality == "text":
            return f"Genera un ejemplo de codigo corto sobre {context.topic}, fundamentado en {source_title}, con recorrido, busqueda e insercion."
        if modality == "video":
            return f"Disena una simulacion interactiva de {context.topic} basada en {source_title}, evitando sobrecarga cognitiva."
        return f"Formula una pregunta de reflexion Bloom {context.bloom_target} sobre {context.topic} anclada en {source_title}."

    def _source_item(self, source: TavilySource, category: QueryCategory, bloom_target: int) -> dict:
        return {
            "title": source.title,
            "url": source.url,
            "domain": self._extract_domain(source.url),
            "content_preview": source.content[:300],
            "score": source.score,
            "category": category.value,
            "bloom_level": bloom_target if category in {QueryCategory.BLOOM_LEVEL, QueryCategory.EXERCISE} else None,
        }

    def _detect_contradictions(
        self,
        result: TavilyQueryResult,
        all_results: list[TavilyQueryResult],
    ) -> list[dict]:
        if result.response is None:
            return []
        current = self._answer_text(result)
        if not current:
            return []
        contradictions: list[dict] = []
        for other in all_results:
            if other is result or other.response is None:
                continue
            other_text = self._answer_text(other)
            if self._texts_contradict(current, other_text):
                fingerprint = "|".join(sorted([result.query, other.query]))
                contradictions.append(
                    {
                        "fingerprint": fingerprint,
                        "queries": [result.query, other.query],
                        "statements": [current[:180], other_text[:180]],
                        "severity": "warning",
                    }
                )
        return contradictions

    def _texts_contradict(self, left: str, right: str) -> bool:
        l = left.lower()
        r = right.lower()
        pairs = [
            ("always", "never"),
            ("siempre", "nunca"),
            ("correct", "incorrect"),
            ("correcto", "incorrecto"),
            ("true", "false"),
            ("verdadero", "falso"),
            ("must", "must not"),
            ("debe", "no debe"),
        ]
        return any((a in l and b in r) or (b in l and a in r) for a, b in pairs)

    def _answer_text(self, result: TavilyQueryResult) -> str:
        if result.response is None:
            return ""
        answer = result.response.answer.strip()
        if answer:
            return answer
        return " ".join(s.content for s in result.response.results[:2]).strip()

    def _score_confidence(self, response: TavilySearchResponse) -> float:
        if not response.results:
            return 0.0
        scores = [max(0.0, min(1.0, source.score)) for source in response.results]
        avg_score = sum(scores) / len(scores)
        coverage_bonus = min(0.2, len(response.results) * 0.05)
        answer_bonus = 0.1 if response.answer else 0.0
        return round(min(1.0, avg_score + coverage_bonus + answer_bonus), 4)

    def _compute_confidence(self, results: list[TavilyQueryResult]) -> float:
        if not results:
            return 0.0
        success = [r for r in results if r.ok]
        if not success:
            return 0.0
        avg_conf = sum(r.confidence for r in success) / len(results)
        success_ratio = len(success) / len(results)
        return round(avg_conf * success_ratio, 4)

    async def _cache_get(self, query: str):
        if self.cache is None:
            return None
        return await self.cache.get(query)

    async def _cache_set(self, query: str, response: TavilySearchResponse) -> None:
        if self.cache is not None:
            await self.cache.set(query, response)

    async def _can_proceed(self) -> bool:
        if self.rate_limiter is None:
            return True
        can_proceed = getattr(self.rate_limiter, "can_proceed", None)
        if can_proceed is None:
            return True
        result = can_proceed()
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
        except Exception:
            return ""
        return parsed.netloc.lower()

    @staticmethod
    def _normalize_content(content: str) -> str:
        words = [w.strip(".,;:!?()[]{}").lower() for w in str(content).split()]
        words = [w for w in words if len(w) > 3]
        return " ".join(sorted(set(words))[:24])

    @staticmethod
    def _deduplicate_by_key(items: list[dict], key: str) -> list[dict]:
        seen = set()
        result = []
        for item in items:
            value = item.get(key)
            if value in seen:
                continue
            seen.add(value)
            result.append(item)
        return result
