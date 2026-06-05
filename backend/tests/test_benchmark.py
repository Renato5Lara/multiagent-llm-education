from __future__ import annotations

from pathlib import Path

from app.benchmark.mermaid import MermaidGenerator, MermaidValidator
from app.benchmark.runner import BenchmarkRunner
from app.benchmark.schemas import BenchmarkConfig
from app.benchmark.statistics import cohens_d, mann_whitney_u, mcnemar, rank_biserial


DATASETS = [
    "../datasets/humaneval_pedagogical.jsonl",
    "../datasets/mbpp_pedagogical.jsonl",
    "../datasets/multimodal_pedagogical_tasks.jsonl",
    "../datasets/misconception_dataset.jsonl",
    "../datasets/bloom_level_tasks.jsonl",
]


def test_benchmark_runner_exports_academic_artifacts(tmp_path: Path):
    result = BenchmarkRunner().run(
        BenchmarkConfig(
            dataset_paths=DATASETS,
            output_dir=str(tmp_path),
            seed=7,
            max_tasks=5,
        )
    )

    assert result.records
    assert any(row["metric"] == "pass_at_1" for row in result.aggregate_metrics)
    assert any(item.metric == "grounding_score" for item in result.comparisons)
    for path in result.exports.values():
        assert Path(path).exists()
    assert "swarm_full" in Path(result.exports["markdown"]).read_text(encoding="utf-8")


def test_statistical_functions_are_reproducible():
    x = [0, 0, 1, 1]
    y = [1, 1, 1, 1]
    u = mann_whitney_u(x, y)
    assert u >= 0
    assert -1 <= rank_biserial(u, len(x), len(y)) <= 1
    assert cohens_d(x, y) > 0
    chi2, p_value = mcnemar([False, False, True], [True, True, True])
    assert chi2 >= 0
    assert 0 <= p_value <= 1


def test_mermaid_generator_outputs_valid_diagrams():
    generator = MermaidGenerator()
    validator = MermaidValidator()
    for diagram in [generator.architecture(), generator.pedagogical_flow(), generator.sse_observability()]:
        result = validator.validate(diagram)
        assert result.valid, result.errors


def test_mermaid_validator_rejects_broken_flowchart():
    result = MermaidValidator().validate("flowchart LR\nA -->")
    assert not result.valid
    assert result.errors
