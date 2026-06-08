"""
Benchmark Metrics — 13 métricas de evaluación académica para el sistema
multi-agente pedagógico.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any

from app.experiment.benchmark.scenarios import BenchmarkScenario, GroundTruth


@dataclass
class BenchmarkMetrics:
    """Las 13 métricas del benchmark académico."""

    pass_at_1: float = 0.0
    correction_rate: float = 0.0
    grounding_score: float = 0.0
    misconception_coverage: float = 0.0
    bloom_alignment: float = 0.0
    adaptation_impact: float = 0.0
    hallucination_reduction: float = 0.0
    sandbox_validation_success: float = 0.0
    execution_success: float = 0.0
    consensus_confidence: float = 0.0
    retrieval_confidence: float = 0.0
    prompt_grounding_score: float = 0.0
    personalization_impact: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> BenchmarkMetrics:
        return cls(**{k: float(v) for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class BenchmarkResult:
    """Resultado completo de una ejecución del benchmark."""

    condition_name: str
    seed: int
    scenario_id: str
    metrics: BenchmarkMetrics = field(default_factory=BenchmarkMetrics)
    system_output: dict[str, Any] = field(default_factory=dict)
    ground_truth: GroundTruth | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0


class MetricsCalculator:
    """Calcula las 13 métricas del benchmark para cada escenario.

    Opera sobre el output del sistema y el ground truth para producir
    métricas comparables entre condiciones.
    """

    @staticmethod
    def pass_at_1(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Pass@1: 1.0 si el sistema genera un plan/pase correcto al primer intento."""
        expected = ground_truth.expected_pass
        actual = system_output.get("first_attempt_pass", False)
        return 1.0 if actual == expected else 0.0

    @staticmethod
    def correction_rate(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Tasa de corrección: detección y corrección de errores."""
        errors_detected = system_output.get("errors_detected", [])
        errors_corrected = system_output.get("errors_corrected", [])
        total = len(errors_detected)
        if total == 0:
            return 1.0
        return len(errors_corrected) / total

    @staticmethod
    def grounding_score(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Grounding: qué tan fundamentada está la respuesta en teoría educativa."""
        objectives_aligned = system_output.get("objectives_aligned", [])
        expected_bloom = ground_truth.expected_bloom_level
        if not objectives_aligned:
            return 0.0
        aligned = sum(
            1 for o in objectives_aligned
            if abs(o.get("bloom_level", 0) - expected_bloom) <= 1
        )
        return aligned / len(objectives_aligned)

    @staticmethod
    def misconception_coverage(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Cobertura de misconceptions: proporción de misconceptions conocidas abordadas."""
        known = set(ground_truth.expected_misconceptions)
        addressed = set(system_output.get("misconceptions_addressed", []))
        if not known:
            return 1.0
        return len(known & addressed) / len(known)

    @staticmethod
    def bloom_alignment(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Alineación Bloom: qué tan cerca está el nivel Bloom asignado del esperado."""
        expected = ground_truth.expected_bloom_level
        assigned = system_output.get("bloom_level_assigned", expected)
        diff = abs(assigned - expected)
        return max(0.0, 1.0 - diff * 0.2)

    @staticmethod
    def adaptation_impact(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Impacto de adaptación: mejora del contenido adaptado vs baseline."""
        baseline_score = system_output.get("baseline_score", 0.0)
        adapted_score = system_output.get("adapted_score", 0.0)
        if baseline_score <= 0:
            return adapted_score
        return (adapted_score - baseline_score) / baseline_score

    @staticmethod
    def hallucination_reduction(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Reducción de alucinación: 1 - (contenido alucinado / contenido total)."""
        total_claims = system_output.get("total_claims", 1)
        hallucinated = system_output.get("hallucinated_claims", 0)
        if total_claims == 0:
            return 1.0
        return 1.0 - (hallucinated / total_claims)

    @staticmethod
    def sandbox_validation_success(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Éxito de validación en sandbox: código generado que compila/ejecuta."""
        sandbox_results = system_output.get("sandbox_results", [])
        if not sandbox_results:
            return 0.0
        passed = sum(1 for r in sandbox_results if r.get("success", False))
        return passed / len(sandbox_results)

    @staticmethod
    def execution_success(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Éxito de ejecución: proporción de pasos de la pipeline que completan."""
        pipeline_steps = system_output.get("pipeline_steps", [])
        if not pipeline_steps:
            return 0.0
        completed = sum(1 for s in pipeline_steps if s.get("status") == "completed")
        return completed / len(pipeline_steps)

    @staticmethod
    def consensus_confidence(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Confianza del consenso: promedio de confianza de los voters."""
        confidences = system_output.get("voter_confidences", [])
        if not confidences:
            return 0.0
        return sum(confidences) / len(confidences)

    @staticmethod
    def retrieval_confidence(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Confianza de recuperación: calidad del contenido recuperado."""
        retrieval_scores = system_output.get("retrieval_scores", [])
        if not retrieval_scores:
            return 0.0
        return sum(retrieval_scores) / len(retrieval_scores)

    @staticmethod
    def prompt_grounding_score(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Grounding de prompts: qué tan contextualizados están los prompts generados."""
        prompt_context = system_output.get("prompt_context_fields", [])
        expected_fields = {"student_profile", "learning_objectives", "bloom_level"}
        if not prompt_context:
            return 0.0
        matched = set(prompt_context) & expected_fields
        return len(matched) / len(expected_fields)

    @staticmethod
    def personalization_impact(
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> float:
        """Impacto de personalización: grado de adaptación al perfil del estudiante."""
        profile_fields_used = system_output.get("profile_fields_used", [])
        expected_profile_fields = {
            "estilo_aprendizaje", "ritmo", "modalidad",
            "nivel_dominio", "preferencias",
        }
        if not profile_fields_used:
            return 0.0
        matched = set(profile_fields_used) & expected_profile_fields
        return len(matched) / len(expected_profile_fields)

    def compute_all(
        self,
        system_output: dict[str, Any],
        ground_truth: GroundTruth,
    ) -> BenchmarkMetrics:
        return BenchmarkMetrics(
            pass_at_1=self.pass_at_1(system_output, ground_truth),
            correction_rate=self.correction_rate(system_output, ground_truth),
            grounding_score=self.grounding_score(system_output, ground_truth),
            misconception_coverage=self.misconception_coverage(system_output, ground_truth),
            bloom_alignment=self.bloom_alignment(system_output, ground_truth),
            adaptation_impact=self.adaptation_impact(system_output, ground_truth),
            hallucination_reduction=self.hallucination_reduction(system_output, ground_truth),
            sandbox_validation_success=self.sandbox_validation_success(system_output, ground_truth),
            execution_success=self.execution_success(system_output, ground_truth),
            consensus_confidence=self.consensus_confidence(system_output, ground_truth),
            retrieval_confidence=self.retrieval_confidence(system_output, ground_truth),
            prompt_grounding_score=self.prompt_grounding_score(system_output, ground_truth),
            personalization_impact=self.personalization_impact(system_output, ground_truth),
        )


def aggregate_metrics(results: list[BenchmarkResult]) -> dict[str, float]:
    """Agrega métricas a través de múltiples resultados."""
    if not results:
        return {k: 0.0 for k in BenchmarkMetrics.__dataclass_fields__}

    keys = list(BenchmarkMetrics.__dataclass_fields__.keys())
    sums = {k: 0.0 for k in keys}

    for r in results:
        for k in keys:
            sums[k] += getattr(r.metrics, k, 0.0)

    n = len(results)
    return {k: round(v / n, 4) for k, v in sums.items()}


def condition_summary(
    results: list[BenchmarkResult],
) -> dict[str, dict[str, float]]:
    """Resumen por condición: métricas agregadas + desviación."""
    from collections import defaultdict

    by_condition: dict[str, list[BenchmarkResult]] = defaultdict(list)
    for r in results:
        by_condition[r.condition_name].append(r)

    summary: dict[str, dict[str, float]] = {}
    keys = list(BenchmarkMetrics.__dataclass_fields__.keys())

    for cond, runs in by_condition.items():
        means = {}
        stds = {}
        for k in keys:
            values = [getattr(r.metrics, k, 0.0) for r in runs]
            means[k] = round(sum(values) / len(values), 4)
            if len(values) > 1:
                var = sum((v - means[k]) ** 2 for v in values) / (len(values) - 1)
                stds[k] = round(math.sqrt(var), 4)
            else:
                stds[k] = 0.0
        summary[cond] = {k: means[k] for k in keys}
        summary[cond]["_count"] = len(runs)

    return summary
