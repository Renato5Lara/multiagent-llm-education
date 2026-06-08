"""
Benchmark Orchestrator — DEPRECATED synthetic runner.

This class previously generated synthetic scores with hardcoded condition biases.
That approach was removed to preserve academic validity.

Use SwarmExecutionBenchmarkRunner (real/runner.py) instead:

    from app.experiment.benchmark.real import SwarmExecutionBenchmarkRunner, SwarmExecutionConfig
    runner = SwarmExecutionBenchmarkRunner(SwarmExecutionConfig(...))
    results = await runner.run()

Or from the command line:
    python scripts/run_real_benchmark.py
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.experiment.benchmark.conditions import BenchmarkConditions


@dataclass
class OrchestratorConfig:
    """Kept for interface compatibility. Ignored by the real benchmark runner."""

    seed: int = 42
    n_scenarios: int = 100
    n_runs_per_condition: int = 10
    conditions: list[str] = field(default_factory=lambda: [c.value for c in BenchmarkConditions])
    output_dir: str = "benchmark_results"


class BenchmarkOrchestrator:
    """DEPRECATED — synthetic benchmark runner removed for academic validity.

    Raises RuntimeError on use. Migrate to SwarmExecutionBenchmarkRunner.
    """

    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or OrchestratorConfig()

    def run(self):
        raise RuntimeError(
            "BenchmarkOrchestrator uses synthetic data and has been disabled.\n"
            "Use SwarmExecutionBenchmarkRunner for real pipeline execution:\n"
            "  python scripts/run_real_benchmark.py\n"
            "or:\n"
            "  from app.experiment.benchmark.real import SwarmExecutionBenchmarkRunner"
        )
