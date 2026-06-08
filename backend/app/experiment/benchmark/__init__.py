"""
Academic Benchmark — UPAO-MAS-EDU v1.0.0

Sistema de evaluación académica para tesis de inteligencia de enjambre
en educación personalizada de programación.

Evalúa 6 condiciones pedagógicas a través de 13 métricas con análisis
estadístico completo (Mann-Whitney U, McNemar, Cohen's d, Rank-Biserial)
y genera exports académicos (report.md, CSV, LaTeX, JSON, visualizaciones).
"""

from app.experiment.benchmark.conditions import (
    BenchmarkCondition,
    BenchmarkConditions,
    get_all_conditions,
    get_condition,
)
from app.experiment.benchmark.scenarios import (
    BenchmarkScenario,
    ScenarioGenerator,
    GroundTruth,
)
from app.experiment.benchmark.metrics import (
    BenchmarkMetrics,
    MetricsCalculator,
    BenchmarkResult,
)
from app.experiment.benchmark.statistics import (
    StatisticalTestSuite,
    StatisticalReport,
    HypothesisTest,
)
from app.experiment.benchmark.orchestrator import (
    BenchmarkOrchestrator,
    OrchestratorConfig,
)
from app.experiment.benchmark.exports import (
    ExportManager,
    ReportGenerator,
    LaTeXTableGenerator,
)
from app.experiment.benchmark.visualization import (
    VisualizationEngine,
    ChartConfig,
)

__all__ = [
    "BenchmarkCondition",
    "BenchmarkConditions",
    "get_all_conditions",
    "get_condition",
    "BenchmarkScenario",
    "ScenarioGenerator",
    "GroundTruth",
    "BenchmarkMetrics",
    "MetricsCalculator",
    "BenchmarkResult",
    "StatisticalTestSuite",
    "StatisticalReport",
    "EffectSize",
    "HypothesisTest",
    "BenchmarkOrchestrator",
    "OrchestratorConfig",
    "BenchmarkRun",
    "ExportManager",
    "ReportGenerator",
    "LaTeXTableGenerator",
    "VisualizationEngine",
    "ChartConfig",
]
