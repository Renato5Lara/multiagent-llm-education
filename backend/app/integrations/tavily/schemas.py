"""Schemas for Tavily Search API — query, response, source, and aggregated research."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SearchDepth(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"


class QueryCategory(str, Enum):
    INTRODUCTION = "introductory"
    CONCEPTUAL = "conceptual"
    PRACTICAL = "practical"
    MISCONCEPTION = "misconception"
    BEGINNER = "beginner_friendly"
    BLOOM_LEVEL = "bloom_level"
    ANALOGY = "analogy"
    REAL_APPLICATION = "real_application"
    EXERCISE = "exercise"


@dataclass(frozen=True)
class TavilySource:
    title: str
    url: str
    content: str
    score: float = 0.0
    raw_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content[:500],
            "score": self.score,
        }


@dataclass
class TavilySearchResponse:
    query: str
    results: list[TavilySource]
    answer: str | None = None
    response_time_ms: float = 0.0
    tokens_used: int = 0

    @property
    def source_count(self) -> int:
        return len(self.results)

    @property
    def top_sources(self) -> list[TavilySource]:
        return sorted(self.results, key=lambda s: s.score, reverse=True)[:5]

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "result_count": self.source_count,
            "answer": self.answer[:300] if self.answer else None,
            "response_time_ms": self.response_time_ms,
            "tokens_used": self.tokens_used,
            "top_sources": [s.to_dict() for s in self.top_sources],
        }


@dataclass
class TavilyQueryResult:
    query: str
    category: QueryCategory
    response: TavilySearchResponse | None = None
    cached: bool = False
    error: str | None = None
    query_time_ms: float = 0.0
    confidence: float = 0.0

    @property
    def success(self) -> bool:
        return self.error is None and self.response is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "category": self.category.value,
            "cached": self.cached,
            "success": self.success,
            "error": self.error,
            "query_time_ms": self.query_time_ms,
            "confidence": self.confidence,
            "response": self.response.to_dict() if self.response else None,
        }


@dataclass
class RetrievalContext:
    topic: str
    objectives: list[str] = field(default_factory=list)
    syllabus: str = ""
    student_level: str = "intermediate"
    bloom_target: int = 3
    language: str = "es"
    search_depth: SearchDepth = SearchDepth.BASIC

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "objectives": self.objectives[:3],
            "student_level": self.student_level,
            "bloom_target": self.bloom_target,
        }


@dataclass
class PedagogicalMetrics:
    """Quality metrics for pedagogical retrieval.

    Attributes:
        pedagogical_coverage: Fraction of pedagogical categories populated (0.0–1.0)
        diversity_score: Ratio of unique domains to total sources (0.0–1.0)
        contradiction_count: Number of detected contradictions
        has_concepts: Whether conceptual findings are present
        has_examples: Whether practical examples are present
        has_analogies: Whether analogies are present
        has_applications: Whether real-world applications are present
        has_misconceptions: Whether common misconceptions are present
        has_exercises: Whether exercises are present
        bloom_target: Target Bloom's taxonomy level (1–6)
    """
    pedagogical_coverage: float = 0.0
    diversity_score: float = 0.0
    contradiction_count: int = 0
    has_concepts: bool = False
    has_examples: bool = False
    has_analogies: bool = False
    has_applications: bool = False
    has_misconceptions: bool = False
    has_exercises: bool = False
    bloom_target: int = 3

    def to_dict(self) -> dict[str, Any]:
        return {
            "pedagogical_coverage": self.pedagogical_coverage,
            "diversity_score": self.diversity_score,
            "contradiction_count": self.contradiction_count,
            "has_concepts": self.has_concepts,
            "has_examples": self.has_examples,
            "has_analogies": self.has_analogies,
            "has_applications": self.has_applications,
            "has_misconceptions": self.has_misconceptions,
            "has_exercises": self.has_exercises,
            "bloom_target": self.bloom_target,
        }


CATEGORIES = ("concepts", "examples", "analogies", "real_applications", "misconceptions", "exercises")


@dataclass
class AggregatedResearch:
    topic: str
    concepts: list[dict[str, Any]] = field(default_factory=list)
    examples: list[dict[str, Any]] = field(default_factory=list)
    analogies: list[dict[str, Any]] = field(default_factory=list)
    real_applications: list[dict[str, Any]] = field(default_factory=list)
    misconceptions: list[dict[str, Any]] = field(default_factory=list)
    exercises: list[dict[str, Any]] = field(default_factory=list)
    sources: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    confidence_score: float = 0.0
    total_sources: int = 0
    unique_domains: int = 0
    aggregated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "concepts": self.concepts[:10],
            "examples": self.examples[:5],
            "analogies": self.analogies[:3],
            "real_applications": self.real_applications[:5],
            "misconceptions": self.misconceptions[:5],
            "exercises": self.exercises[:5],
            "sources": self.sources[:10],
            "contradictions": self.contradictions[:3],
            "confidence_score": self.confidence_score,
            "total_sources": self.total_sources,
            "unique_domains": self.unique_domains,
        }


@dataclass
class CacheEntry:
    query_hash: str
    query: str
    response_json: dict[str, Any]
    created_at: datetime
    ttl_seconds: int
    reuse_count: int = 0
    latency_ms: float = 0.0
    source_count: int = 0

    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_hash": self.query_hash[:12],
            "query": self.query[:60],
            "created_at": self.created_at.isoformat(),
            "ttl_seconds": self.ttl_seconds,
            "reuse_count": self.reuse_count,
            "latency_ms": self.latency_ms,
            "source_count": self.source_count,
        }
