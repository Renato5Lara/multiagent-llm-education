from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    dataset: str
    topic: str
    prompt: str
    expected_concepts: list[str]
    misconceptions: list[str]
    bloom_level: int
    requires_code: bool = False
    requires_retrieval: bool = True
    requires_multimodal: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchmarkVariant:
    name: str
    swarm: bool
    retrieval: bool
    memory: bool
    reviewer: bool
    adaptive: bool

    def label(self) -> str:
        return self.name.replace("_", " ")


@dataclass(frozen=True)
class BenchmarkConfig:
    dataset_paths: list[str]
    output_dir: str = "outputs/benchmark"
    seed: int = 42
    max_tasks: int | None = None
    variants: list[BenchmarkVariant] = field(default_factory=list)


@dataclass(frozen=True)
class BenchmarkRunRecord:
    experiment_id: str
    task_id: str
    dataset: str
    variant: str
    metrics: dict[str, float]
    success: bool
    replay: dict[str, Any]


@dataclass(frozen=True)
class StatisticalComparison:
    metric: str
    baseline: str
    treatment: str
    baseline_mean: float
    treatment_mean: float
    delta: float
    mann_whitney_u: float
    mann_whitney_p: float
    rank_biserial: float
    cohens_d: float
    ci_low: float
    ci_high: float
    mcnemar_chi2: float | None = None
    mcnemar_p: float | None = None


@dataclass(frozen=True)
class BenchmarkResult:
    experiment_id: str
    records: list[BenchmarkRunRecord]
    aggregate_metrics: list[dict[str, float | str]]
    comparisons: list[StatisticalComparison]
    exports: dict[str, str]
