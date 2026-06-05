"""Schemas for the pedagogical Tavily retrieval pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SearchDepth(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"


class QueryCategory(str, Enum):
    INTRODUCTION = "introduction"
    CONCEPTUAL = "conceptual"
    PRACTICAL = "practical"
    MISCONCEPTION = "misconception"
    REAL_APPLICATION = "real_application"
    BLOOM_LEVEL = "bloom_level"
    EXERCISE = "exercise"
    MULTIMODAL = "multimodal"


@dataclass
class RetrievalContext:
    topic: str
    objectives: list[str] = field(default_factory=list)
    bloom_target: int = 3
    language: str = "es"
    max_results_per_query: int = 3
    search_depth: SearchDepth = SearchDepth.BASIC
    learning_style: str = ""  # visual | auditory | reading | kinesthetic
    preferred_analogies: list[str] = field(default_factory=list)


@dataclass
class TavilySource:
    title: str
    url: str
    content: str
    score: float = 0.0

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "TavilySource":
        return cls(
            title=str(data.get("title") or ""),
            url=str(data.get("url") or ""),
            content=str(data.get("content") or data.get("snippet") or ""),
            score=max(0.0, min(1.0, float(data.get("score") or 0.0))),
        )


@dataclass
class TavilySearchResponse:
    query: str
    results: list[TavilySource] = field(default_factory=list)
    answer: str = ""
    response_time_ms: float = 0.0

    @classmethod
    def from_mapping(cls, data: dict[str, Any], *, query: str, response_time_ms: float = 0.0) -> "TavilySearchResponse":
        raw_results = data.get("results") or []
        if not isinstance(raw_results, list):
            raw_results = []
        return cls(
            query=str(data.get("query") or query),
            results=[
                TavilySource.from_mapping(item)
                for item in raw_results
                if isinstance(item, dict)
            ],
            answer=str(data.get("answer") or ""),
            response_time_ms=response_time_ms,
        )


@dataclass
class TavilyQueryResult:
    query: str
    category: QueryCategory
    response: TavilySearchResponse | None = None
    query_time_ms: float = 0.0
    confidence: float = 0.0
    cached: bool = False
    degraded: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.response is not None and self.error is None


@dataclass
class PedagogicalMetrics:
    retrieval_confidence: float = 0.0
    pedagogical_confidence: float = 0.0
    contradiction_score: float = 0.0
    diversity_score: float = 0.0
    prompt_grounding_score: float = 0.0
    misconception_coverage: float = 0.0
    bloom_alignment_score: float = 0.0
    semantic_redundancy_score: float = 0.0
    cognitive_load_score: float = 0.0
    source_count: int = 0
    unique_domains: int = 0
    contradiction_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "retrieval_confidence": self.retrieval_confidence,
            "pedagogical_confidence": self.pedagogical_confidence,
            "contradiction_score": self.contradiction_score,
            "diversity_score": self.diversity_score,
            "prompt_grounding_score": self.prompt_grounding_score,
            "misconception_coverage": self.misconception_coverage,
            "bloom_alignment_score": self.bloom_alignment_score,
            "semantic_redundancy_score": self.semantic_redundancy_score,
            "cognitive_load_score": self.cognitive_load_score,
            "source_count": self.source_count,
            "unique_domains": self.unique_domains,
            "contradiction_count": self.contradiction_count,
        }


@dataclass
class AggregatedResearch:
    topic: str
    concepts: list[dict[str, Any]] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    analogies: list[dict[str, Any]] = field(default_factory=list)
    real_applications: list[dict[str, Any]] = field(default_factory=list)
    misconceptions: list[dict[str, Any]] = field(default_factory=list)
    exercises: list[dict[str, Any]] = field(default_factory=list)
    multimodal_prompts: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    query_results: list[TavilyQueryResult] = field(default_factory=list)
    total_sources: int = 0
    unique_domains: int = 0
    confidence_score: float = 0.0
    degraded: bool = False

    def compute_pedagogical_metrics(self, bloom_target: int = 3) -> PedagogicalMetrics:
        categories_present = [
            bool(self.concepts),
            bool(self.examples),
            bool(self.analogies),
            bool(self.real_applications),
            bool(self.misconceptions),
            bool(self.exercises),
        ]
        pedagogical_coverage = sum(categories_present) / len(categories_present)
        diversity = self.unique_domains / self.total_sources if self.total_sources else 0.0
        contradiction_score = 1.0 - min(1.0, len(self.contradictions) / max(1, self.total_sources))
        misconception_coverage = min(1.0, len(self.misconceptions) / 2.0)
        bloom_hits = [
            item for item in self.exercises + self.multimodal_prompts
            if int(item.get("bloom_level", bloom_target) or bloom_target) == bloom_target
        ]
        bloom_alignment = min(1.0, len(bloom_hits) / max(1, len(self.exercises) + len(self.multimodal_prompts)))
        grounded_prompts = [
            item for item in self.multimodal_prompts
            if item.get("grounded_sources") or item.get("source_url")
        ]
        grounding = min(1.0, len(grounded_prompts) / max(1, len(self.multimodal_prompts)))
        redundancy = self._semantic_redundancy_score()
        cognitive_load = self._cognitive_load_score()
        pedagogical_confidence = (
            pedagogical_coverage * 0.30
            + contradiction_score * 0.20
            + diversity * 0.15
            + misconception_coverage * 0.15
            + bloom_alignment * 0.10
            + grounding * 0.10
        )
        return PedagogicalMetrics(
            retrieval_confidence=round(self.confidence_score, 4),
            pedagogical_confidence=round(max(0.0, min(1.0, pedagogical_confidence)), 4),
            contradiction_score=round(contradiction_score, 4),
            diversity_score=round(max(0.0, min(1.0, diversity)), 4),
            prompt_grounding_score=round(grounding, 4),
            misconception_coverage=round(misconception_coverage, 4),
            bloom_alignment_score=round(bloom_alignment, 4),
            semantic_redundancy_score=round(redundancy, 4),
            cognitive_load_score=round(cognitive_load, 4),
            source_count=self.total_sources,
            unique_domains=self.unique_domains,
            contradiction_count=len(self.contradictions),
        )

    @property
    def metrics(self) -> PedagogicalMetrics:
        return self.compute_pedagogical_metrics()

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "concepts": self.concepts,
            "examples": self.examples,
            "analogies": self.analogies,
            "real_applications": self.real_applications,
            "misconceptions": self.misconceptions,
            "exercises": self.exercises,
            "multimodal_prompts": self.multimodal_prompts,
            "contradictions": self.contradictions,
            "sources": self.sources,
            "total_sources": self.total_sources,
            "unique_domains": self.unique_domains,
            "confidence_score": self.confidence_score,
            "degraded": self.degraded,
            "metrics": self.metrics.to_dict(),
        }

    def _semantic_redundancy_score(self) -> float:
        previews = [str(s.get("content_preview") or "") for s in self.sources]
        if len(previews) < 2:
            return 0.0
        normalized = {_fingerprint(text) for text in previews if text}
        return 1.0 - (len(normalized) / len(previews))

    def _cognitive_load_score(self) -> float:
        items = len(self.concepts) + len(self.examples) + len(self.exercises) + len(self.multimodal_prompts)
        if items <= 10:
            return 0.2
        if items <= 20:
            return 0.5
        return 0.85


def _fingerprint(text: str) -> str:
    words = [w.strip(".,;:!?()[]{}").lower() for w in text.split()]
    words = [w for w in words if len(w) > 3]
    return " ".join(sorted(set(words))[:24])
