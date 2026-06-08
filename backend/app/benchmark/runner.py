from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import asdict
from statistics import mean

from app.benchmark.datasets import BenchmarkDatasetLoader
from app.benchmark.exporters import BenchmarkExporter
from app.benchmark.metrics import METRIC_NAMES, PedagogicalMetricEvaluator
from app.benchmark.schemas import BenchmarkConfig, BenchmarkResult, BenchmarkRunRecord, BenchmarkVariant, StatisticalComparison
from app.benchmark.statistics import compare_metric, mcnemar


DEFAULT_VARIANTS = [
    BenchmarkVariant("single_agent_static", swarm=False, retrieval=False, memory=False, reviewer=False, adaptive=False),
    BenchmarkVariant("swarm_full", swarm=True, retrieval=True, memory=True, reviewer=True, adaptive=True),
    BenchmarkVariant("swarm_no_retrieval", swarm=True, retrieval=False, memory=True, reviewer=True, adaptive=True),
    BenchmarkVariant("swarm_no_memory", swarm=True, retrieval=True, memory=False, reviewer=True, adaptive=True),
    BenchmarkVariant("swarm_no_reviewer", swarm=True, retrieval=True, memory=True, reviewer=False, adaptive=True),
    BenchmarkVariant("swarm_static_pedagogy", swarm=True, retrieval=True, memory=True, reviewer=True, adaptive=False),
]


class BenchmarkRunner:
    """Runs deterministic ablations for academic hardening reports."""

    def __init__(
        self,
        loader: BenchmarkDatasetLoader | None = None,
        evaluator: PedagogicalMetricEvaluator | None = None,
        exporter: BenchmarkExporter | None = None,
    ):
        self.loader = loader or BenchmarkDatasetLoader()
        self.evaluator = evaluator or PedagogicalMetricEvaluator()
        self.exporter = exporter or BenchmarkExporter()

    def run(self, config: BenchmarkConfig) -> BenchmarkResult:
        experiment_id = f"academic-hardening-{config.seed}-{uuid.uuid4().hex[:8]}"
        variants = config.variants or DEFAULT_VARIANTS
        tasks = self.loader.load_many(config.dataset_paths, max_tasks=config.max_tasks)
        records: list[BenchmarkRunRecord] = []
        for task in tasks:
            for variant in variants:
                metrics = self.evaluator.score(task, variant, config.seed)
                records.append(
                    BenchmarkRunRecord(
                        experiment_id=experiment_id,
                        task_id=task.id,
                        dataset=task.dataset,
                        variant=variant.name,
                        metrics=metrics,
                        success=bool(metrics["pass_at_1"] >= 1.0 and metrics["sandbox_validation_success"] >= 0.5),
                        replay={
                            "topic": task.topic,
                            "dataset": task.dataset,
                            "variant": asdict(variant),
                            "metrics": metrics,
                            "pedagogical_trace": self._trace(task, variant, metrics),
                        },
                    )
                )
        aggregates = self._aggregate(records)
        comparisons = self._all_comparisons(records)
        exports = self.exporter.export(config.output_dir, experiment_id, records, aggregates, comparisons)
        return BenchmarkResult(experiment_id, records, aggregates, comparisons, exports)

    def _aggregate(self, records: list[BenchmarkRunRecord]) -> list[dict[str, float | str]]:
        by_variant_metric: dict[tuple[str, str], list[float]] = defaultdict(list)
        for record in records:
            for metric, value in record.metrics.items():
                by_variant_metric[(record.variant, metric)].append(float(value))
        return [
            {"variant": variant, "metric": metric, "mean": round(mean(values), 4), "n": len(values)}
            for (variant, metric), values in sorted(by_variant_metric.items())
        ]

    def _all_comparisons(self, records: list[BenchmarkRunRecord]) -> list[StatisticalComparison]:
        planned = [
            ("single_agent_static", "swarm_full"),
            ("swarm_no_retrieval", "swarm_full"),
            ("swarm_no_memory", "swarm_full"),
            ("swarm_no_reviewer", "swarm_full"),
            ("swarm_static_pedagogy", "swarm_full"),
        ]
        comparisons: list[StatisticalComparison] = []
        for baseline, treatment in planned:
            comparisons.extend(self._comparisons(records, baseline, treatment))
        return comparisons

    def _comparisons(self, records: list[BenchmarkRunRecord], baseline: str, treatment: str) -> list[StatisticalComparison]:
        by_variant = defaultdict(list)
        for record in records:
            by_variant[record.variant].append(record)
        comparisons: list[StatisticalComparison] = []
        for metric in METRIC_NAMES:
            left = [record.metrics[metric] for record in by_variant[baseline]]
            right = [record.metrics[metric] for record in by_variant[treatment]]
            comparison = compare_metric(metric, baseline, treatment, left, right)
            if metric in {"pass_at_1", "execution_success", "sandbox_validation_success"}:
                chi2, p_value = mcnemar([v >= 0.5 for v in left], [v >= 0.5 for v in right])
                comparison = StatisticalComparison(**{**asdict(comparison), "mcnemar_chi2": round(chi2, 4), "mcnemar_p": round(p_value, 6)})
            comparisons.append(comparison)
        return comparisons

    def _trace(self, task, variant: BenchmarkVariant, metrics: dict[str, float]) -> list[dict]:
        trace = [
            {"step": "task_loaded", "evidence": {"task_id": task.id, "bloom_level": task.bloom_level}},
            {"step": "variant_selected", "evidence": asdict(variant)},
        ]
        if variant.retrieval:
            trace.append({"step": "retrieval_grounding", "score": metrics["grounding_score"]})
        if variant.memory:
            trace.append({"step": "memory_adaptation", "score": metrics["adaptation_impact"]})
        if variant.reviewer:
            trace.append({"step": "sandbox_review", "score": metrics["sandbox_validation_success"]})
        trace.append({"step": "consensus", "score": metrics["consensus_confidence"]})
        return trace
