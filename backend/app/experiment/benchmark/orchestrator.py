"""
Benchmark Orchestrator — DEPRECATED synthetic runner.

This class previously generated synthetic scores with hardcoded condition biases.
That approach was removed to preserve academic validity.

The real-pipeline runner it pointed to (SwarmExecutionBenchmarkRunner,
app/experiment/benchmark/real/) was retired in ADR-0011 along with
BaseAgent/AgentFactory/SwarmOrchestrator, which it depended on. There is
no replacement runner as of this ADR — this class remains disabled.
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
            "BenchmarkOrchestrator uses synthetic data and has been disabled. "
            "Its real-pipeline replacement was retired in ADR-0011 along with "
            "the legacy BaseAgent/SwarmOrchestrator stack it depended on."
        )
