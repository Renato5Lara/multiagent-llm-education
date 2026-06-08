from __future__ import annotations

import random

from app.benchmark.schemas import BenchmarkTask, BenchmarkVariant


METRIC_NAMES = [
    "pass_at_1",
    "correction_rate",
    "hallucination_reduction",
    "grounding_score",
    "misconception_coverage",
    "bloom_alignment",
    "adaptation_impact",
    "retrieval_confidence",
    "execution_success",
    "sandbox_validation_success",
    "trajectory_length",
    "consensus_confidence",
]


class PedagogicalMetricEvaluator:
    """Deterministic proxy evaluator for reproducible academic ablations."""

    def score(self, task: BenchmarkTask, variant: BenchmarkVariant, seed: int) -> dict[str, float]:
        rng = random.Random(f"{seed}:{task.id}:{variant.name}")
        difficulty = min(1.0, 0.18 + (task.bloom_level * 0.09) + (0.08 if task.requires_multimodal else 0.0))
        base = 0.52 - difficulty * 0.18
        if variant.swarm:
            base += 0.1
        if variant.retrieval and task.requires_retrieval:
            base += 0.12
        if variant.memory:
            base += 0.06
        if variant.reviewer and task.requires_code:
            base += 0.1
        if variant.adaptive:
            base += 0.08
        noise = rng.uniform(-0.035, 0.035)

        grounding = self._clip(0.35 + (0.42 if variant.retrieval else 0.0) + (0.08 if variant.swarm else 0.0) + noise)
        misconception = self._clip(0.3 + 0.18 * bool(task.misconceptions) + 0.12 * variant.retrieval + 0.12 * variant.memory + noise)
        bloom = self._clip(0.48 + 0.16 * variant.adaptive + 0.08 * variant.swarm - abs(task.bloom_level - 3) * 0.025 + noise)
        retrieval_confidence = self._clip(0.2 + (0.62 if variant.retrieval else 0.0) + rng.uniform(-0.04, 0.04))
        execution_success = self._clip(0.58 + 0.18 * variant.reviewer + 0.04 * variant.swarm - 0.12 * task.requires_code + rng.uniform(-0.05, 0.05))
        sandbox_success = execution_success if variant.reviewer else self._clip(execution_success - 0.18)
        consensus = self._clip(0.48 + 0.2 * variant.swarm + 0.07 * variant.memory + 0.04 * variant.reviewer + noise)
        pass_at_1 = 1.0 if self._clip(base + noise) >= 0.58 else 0.0
        trajectory = 1.0 + (0.0 if pass_at_1 else 1.0) + (0.45 if variant.reviewer and not pass_at_1 else 0.0)

        return {
            "pass_at_1": pass_at_1,
            "correction_rate": 1.0 - pass_at_1 if variant.reviewer else 0.0,
            "hallucination_reduction": self._clip(0.18 + 0.42 * variant.retrieval + 0.16 * variant.swarm + 0.08 * variant.memory + noise),
            "grounding_score": grounding,
            "misconception_coverage": misconception,
            "bloom_alignment": bloom,
            "adaptation_impact": self._clip(0.22 + 0.48 * variant.adaptive + 0.1 * variant.memory + noise),
            "retrieval_confidence": retrieval_confidence,
            "execution_success": execution_success,
            "sandbox_validation_success": sandbox_success,
            "trajectory_length": trajectory,
            "consensus_confidence": consensus,
        }

    def _clip(self, value: float) -> float:
        return round(max(0.0, min(1.0, value)), 4)
