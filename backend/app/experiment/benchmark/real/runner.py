"""SwarmExecutionBenchmarkRunner — runs real swarm pipeline across all benchmark conditions."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.experiment.benchmark.conditions import (
    BenchmarkCondition,
    BenchmarkConditions,
    get_all_conditions,
    get_condition,
)
from app.experiment.benchmark.metrics import (
    BenchmarkMetrics,
    BenchmarkResult,
    MetricsCalculator,
    condition_summary,
)
from app.experiment.benchmark.scenarios import ScenarioGenerator
from app.experiment.benchmark.real.executor import execute_condition_pipeline
from app.experiment.benchmark.real.mapper import map_real_output_to_metric_input
from app.experiment.benchmark.real.safety import SafetyConfig

logger = logging.getLogger(__name__)


class SwarmExecutionConfig:
    """Configuration for the real swarm benchmark execution."""

    def __init__(
        self,
        seed: int = 42,
        n_scenarios: int = 20,
        n_runs_per_condition: int = 3,
        conditions: list[str] | None = None,
        output_dir: str = "benchmark_real_results",
        timeout_per_experiment: float = 120.0,
        max_retries: int = 2,
        graceful: bool = True,
        enable_tracing: bool = False,
    ):
        self.seed = seed
        self.n_scenarios = n_scenarios
        self.n_runs_per_condition = n_runs_per_condition
        self.conditions = conditions or [c.value for c in BenchmarkConditions]
        self.output_dir = output_dir
        self.timeout_per_experiment = timeout_per_experiment
        self.max_retries = max_retries
        self.graceful = graceful
        self.enable_tracing = enable_tracing


class SwarmExecutionBenchmarkRunner:
    """Benchmark runner that executes the REAL swarm pipeline.

    Unlike BenchmarkOrchestrator (which uses synthetic proxy data),
    this runner creates actual database connections, spins up real
    agent instances, executes the LLM pipeline, and measures real
    latencies and outcomes.
    """

    def __init__(self, config: SwarmExecutionConfig | None = None):
        self.config = config or SwarmExecutionConfig()
        self.results: list[BenchmarkResult] = []
        self.metrics_calculator = MetricsCalculator()
        self.safety_config = SafetyConfig(
            timeout_per_experiment_seconds=self.config.timeout_per_experiment,
            max_retries=self.config.max_retries,
            graceful_degradation=self.config.graceful,
        )

        all_conditions = get_all_conditions()
        self.conditions: list[BenchmarkCondition] = [
            c for c in all_conditions if c.name in self.config.conditions
        ]

        logger.info(
            "SwarmExecutionBenchmarkRunner initialized: %d conditions, %d scenarios, %d runs",
            len(self.conditions), self.config.n_scenarios, self.config.n_runs_per_condition,
        )

    async def run(self) -> list[BenchmarkResult]:
        """Execute the full real benchmark.

        For each condition × run × scenario:
        1. Create a fresh async UoW + AgentFactory
        2. Execute the condition-specific pipeline
        3. Map real output → metric input format
        4. Compute metrics
        5. Collect timing data
        """
        logger.info("Generating %d benchmark scenarios (seed=%d)...",
                     self.config.n_scenarios, self.config.seed)
        generator = ScenarioGenerator(
            seed=self.config.seed,
            n_scenarios=self.config.n_scenarios,
        )
        scenarios = generator.generate()
        logger.info("Generated %d scenarios", len(scenarios))

        total = (
            len(self.conditions)
            * self.config.n_runs_per_condition
            * self.config.n_scenarios
        )
        completed = 0
        degraded = 0
        failed = 0

        for condition in self.conditions:
            logger.info("Condition: %s (%s)", condition.name, condition.label)

            for run_idx in range(self.config.n_runs_per_condition):
                run_seed = self.config.seed + run_idx

                for scenario in scenarios:
                    outcome = await execute_condition_pipeline(
                        scenario=scenario,
                        condition=condition,
                        seed=run_seed,
                        safety=self.safety_config,
                    )

                    if outcome.degraded:
                        degraded += 1
                    if not outcome.success and not outcome.degraded:
                        failed += 1

                    system_output = {}
                    metrics = BenchmarkMetrics()

                    if outcome.result:
                        outcome.result["_benchmark_retries"] = outcome.retries
                        outcome.result["_benchmark_timed_out"] = outcome.error and "Timeout" in outcome.error
                        system_output = map_real_output_to_metric_input(
                            outcome.result, condition
                        )
                        try:
                            metrics = self.metrics_calculator.compute_all(
                                system_output,
                                scenario.ground_truth,
                            )
                        except Exception as e:
                            logger.error("Metrics computation failed: %s", e)

                    metadata: dict[str, Any] = {
                        "real_execution": True,
                        "degraded": outcome.degraded,
                        "error": outcome.error or "",
                        "phase_timings_ms": {},
                        "retries": outcome.retries,
                        "condition_config": condition.config_dict(),
                    }

                    if outcome.result:
                        exec_summary = outcome.result.get("execution_summary", {})
                        metadata["phase_timings_ms"] = exec_summary.get("phase_timings_ms", {})
                        metadata["session_id"] = exec_summary.get("session_id", "")
                        metadata["phase_count"] = len(
                            exec_summary.get("phase_timings_ms", {})
                        )
                        metadata["sandbox_validated"] = outcome.result.get("sandbox_validated", False)
                        metadata["sandbox_snippets"] = len(outcome.result.get("sandbox_results", []))
                        metadata["consistency_passed"] = (
                            outcome.result.get("consistency_result", {})
                            .get("report", {})
                            .get("passed", True)
                        )

                    result = BenchmarkResult(
                        condition_name=condition.name,
                        seed=run_seed,
                        scenario_id=scenario.scenario_id,
                        metrics=metrics,
                        system_output=system_output,
                        ground_truth=scenario.ground_truth,
                        metadata=metadata,
                        execution_time_ms=outcome.duration_ms,
                    )
                    self.results.append(result)

                    completed += 1
                    if completed % 10 == 0:
                        logger.info(
                            "Progress: %d/%d (degraded=%d, failed=%d)",
                            completed, total, degraded, failed,
                        )

        logger.info(
            "Benchmark complete: %d runs (%d degraded, %d failed)",
            completed, degraded, failed,
        )
        return self.results

    def get_results_by_condition(self, condition_name: str) -> list[BenchmarkResult]:
        return [r for r in self.results if r.condition_name == condition_name]

    def summary(self) -> dict[str, dict[str, float]]:
        return condition_summary(self.results) if self.results else {}
