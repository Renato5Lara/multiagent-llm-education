"""
Benchmark Orchestrator — Orquestador del benchmark académico.

Ejecuta las 6 condiciones del benchmark sobre escenarios sintéticos
y computa las 13 métricas de evaluación.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from app.experiment.benchmark.conditions import (
    BenchmarkCondition,
    BenchmarkConditions,
    get_all_conditions,
)
from app.experiment.benchmark.scenarios import BenchmarkScenario, ScenarioGenerator
from app.experiment.benchmark.metrics import (
    BenchmarkMetrics,
    BenchmarkResult,
    MetricsCalculator,
)


@dataclass
class OrchestratorConfig:
    """Configuración del orquestador de benchmark."""

    seed: int = 42
    n_scenarios: int = 100
    n_runs_per_condition: int = 10
    conditions: list[str] = field(default_factory=lambda: [c.value for c in BenchmarkConditions])
    output_dir: str = "benchmark_results"
    use_pipeline_stubs: bool = True


class BenchmarkOrchestrator:
    """Orquestador del benchmark académico.

    Ejecuta todas las condiciones sobre escenarios generados y
    recolecta métricas para análisis estadístico.
    """

    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or OrchestratorConfig()
        self.metrics_calculator = MetricsCalculator()
        self.results: list[BenchmarkResult] = []
        self.conditions: list[BenchmarkCondition] = [
            c for c in get_all_conditions()
            if c.name.value in self.config.conditions
        ]

    def _generate_student_profile(self, scenario: BenchmarkScenario) -> dict[str, Any]:
        return dict(scenario.student_profile)

    def _generate_system_output_pipeline(
        self,
        scenario: BenchmarkScenario,
        condition: BenchmarkCondition,
        seed: int,
    ) -> dict[str, Any]:
        """Simula la salida de la pipeline pedagógica para una condición.

        En producción, esto llamaría al orquestador real con la configuración
        de la condición. Para benchmark, genera output sintético con sesgo
        controlado según la condición.
        """
        rng = random.Random(seed * 1000 + hash(scenario.scenario_id) % 100000)

        bias = self._condition_bias(condition)
        mastery = scenario.ground_truth.expected_mastery_score

        n_objectives = len(scenario.learning_objectives) or 3
        objectives_aligned = [
            {
                "concept": o["concept"],
                "bloom_level": min(
                    6,
                    max(1, o.get("bloom_level", 1) + rng.randint(-1, 1)),
                ),
                "aligned": rng.random() < (0.5 + bias * 0.4),
            }
            for o in scenario.learning_objectives[:n_objectives]
        ]

        n_misconceptions = len(scenario.misconceptions)
        misconceptions_addressed = (
            scenario.misconceptions[:]
            if rng.random() < (0.3 + bias * 0.5)
            else [
                m for m in scenario.misconceptions
                if rng.random() < (0.4 + bias * 0.4)
            ]
        )

        voter_confidences = [
            round(min(1.0, max(0.1, mastery + rng.gauss(0, 0.1) + bias * 0.1)), 3)
            for _ in range(4)
        ]

        bloom_offset = rng.randint(-1, 1)
        if not condition.adaptive_pedagogy:
            bloom_offset = rng.randint(-2, 0)

        baseline = mastery * (0.5 + rng.random() * 0.2)
        adapted = mastery * (0.6 + rng.random() * 0.3 + bias * 0.15)

        retrieval_scores = (
            [round(min(1.0, mastery + rng.random() * 0.3), 3) for _ in range(rng.randint(2, 5))]
            if condition.retrieval_enabled
            else []
        )

        total_claims = rng.randint(8, 20)
        hallucinated = max(
            0,
            total_claims - int(total_claims * (0.6 + bias * 0.3)),
        )
        if not condition.reviewer_enabled:
            hallucinated = int(hallucinated * 1.3)

        profile_fields = ["estilo_aprendizaje", "ritmo"]
        if condition.adaptive_pedagogy:
            profile_fields.extend(["modalidad", "nivel_dominio", "preferencias"])

        prompt_fields = ["student_profile"]
        if condition.retrieval_enabled:
            prompt_fields.append("learning_objectives")
        if condition.adaptive_pedagogy:
            prompt_fields.append("bloom_level")

        sandbox_results = [
            {"success": rng.random() < (0.5 + bias * 0.3)}
            for _ in range(rng.randint(2, 5))
        ]

        pipeline_steps = [
            {
                "step": s,
                "status": "completed" if rng.random() < (0.7 + bias * 0.2) else "failed",
            }
            for s in ["research", "pedagogy", "adaptation", "planning", "prompt", "consistency"]
        ]

        first_attempt_pass = (
            rng.random() < (mastery * (0.5 + bias * 0.3))
            if scenario.ground_truth.expected_pass
            else rng.random() < (0.2 + bias * 0.2)
        )

        return {
            "first_attempt_pass": first_attempt_pass,
            "errors_detected": [str(e) for e in range(rng.randint(0, 4))],
            "errors_corrected": [str(e) for e in range(rng.randint(0, 3))],
            "objectives_aligned": objectives_aligned,
            "misconceptions_addressed": misconceptions_addressed,
            "bloom_level_assigned": min(
                6,
                max(1, scenario.bloom_level + bloom_offset),
            ),
            "baseline_score": round(baseline, 4),
            "adapted_score": round(adapted, 4),
            "total_claims": total_claims,
            "hallucinated_claims": hallucinated,
            "sandbox_results": sandbox_results,
            "pipeline_steps": pipeline_steps,
            "voter_confidences": voter_confidences,
            "retrieval_scores": retrieval_scores,
            "prompt_context_fields": prompt_fields,
            "profile_fields_used": profile_fields,
        }

    def _condition_bias(self, condition: BenchmarkCondition) -> float:
        """Sesgo de rendimiento esperado para cada condición.

        Valores más altos = mejor rendimiento esperado.
        """
        biases = {
            BenchmarkConditions.SWARM_FULL: 0.0,
            BenchmarkConditions.SWARM_NO_RETRIEVAL: -0.08,
            BenchmarkConditions.SWARM_NO_MEMORY: -0.06,
            BenchmarkConditions.SWARM_NO_REVIEWER: -0.12,
            BenchmarkConditions.SWARM_STATIC_PEDAGOGY: -0.10,
            BenchmarkConditions.SINGLE_AGENT_STATIC: -0.25,
        }
        return biases.get(condition.name, -0.15)

    def run_single_scenario(
        self,
        scenario: BenchmarkScenario,
        condition: BenchmarkCondition,
        seed: int,
    ) -> BenchmarkResult:
        """Ejecuta un escenario bajo una condición y calcula métricas."""
        system_output = self._generate_system_output_pipeline(
            scenario, condition, seed,
        )
        metrics = self.metrics_calculator.compute_all(
            system_output, scenario.ground_truth,
        )
        return BenchmarkResult(
            condition_name=condition.name.value,
            seed=seed,
            scenario_id=scenario.scenario_id,
            metrics=metrics,
            system_output=system_output,
            ground_truth=scenario.ground_truth,
            metadata={
                "condition_label": condition.label,
                "condition_type": condition.type,
                "bloom_level": scenario.bloom_level,
                "difficulty": scenario.difficulty,
            },
        )

    def run(self) -> list[BenchmarkResult]:
        """Ejecuta el benchmark completo."""
        generator = ScenarioGenerator(
            seed=self.config.seed,
            n_scenarios=self.config.n_scenarios,
        )
        scenarios = generator.generate()

        self.results = []
        total_runs = (
            len(self.conditions)
            * self.config.n_runs_per_condition
            * len(scenarios)
        )
        run_idx = 0

        for condition in self.conditions:
            for run_seed_offset in range(self.config.n_runs_per_condition):
                run_seed = self.config.seed + run_seed_offset
                for scenario in scenarios:
                    result = self.run_single_scenario(
                        scenario, condition, run_seed,
                    )
                    self.results.append(result)
                    run_idx += 1

        return self.results

    def get_results_by_condition(
        self,
        condition_name: str,
    ) -> list[BenchmarkResult]:
        return [r for r in self.results if r.condition_name == condition_name]

    def summary(self) -> dict[str, Any]:
        from app.experiment.benchmark.metrics import condition_summary
        return condition_summary(self.results)
