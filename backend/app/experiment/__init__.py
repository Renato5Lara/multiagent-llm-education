"""
Experiment Isolation System — guaranteed non-contaminating experiment execution.

Every mutable subsystem is either injected as a fresh isolated instance
through ExperimentContext or reset via the unified reset protocol.

Submodules:
    context        — ExperimentContext, ExperimentRegistry, ExperimentState
    reset          — reset_all_global_state() unified reset protocol
    conditions     — 5 experimental conditions (treatment/control/ablation)
    pipelines      — reproducible execution pipelines
    metrics        — per-run and aggregated metrics extraction
    analysis       — ANOVA, pairwise tests, Cohen's d, power analysis
    dataset        — ground truth dataset, labeling workflow, synthetic data
    evaluation     — Fleiss' Kappa, expert evaluation protocol
    config         — ExperimentConfig, config hashing, versioning, sweep
    orchestrator   — advanced multi-condition experiment runner
    anomaly        — anomaly detection for experiment runs
    export         — CSV/JSON/LaTeX metrics export
    report         — LaTeX/Markdown scientific report generation
    replay         — deterministic replay from snapshots

Exports:
    [existing exports + dataset, evaluation, config, orchestrator, anomaly, export, report, replay]
"""

from app.experiment.context import (
    ExperimentContext,
    ExperimentRegistry,
    ExperimentSnapshot,
    ExperimentState,
)
from app.experiment.reset import reset_all_global_state
from app.experiment.conditions import (
    ExperimentCondition,
    get_all_conditions,
    get_condition,
    get_controls,
    get_treatments,
    get_ablations,
    get_hypotheses,
    FULL_SWARM,
    UNIFORM_WEIGHTS,
    SINGLE_AGENT,
    NO_TRUST,
    NO_SPECIALIZATION,
)
from app.experiment.pipelines import (
    BatchPipeline,
    SingleAgentPipeline,
    PipelineResult,
    PipelineRun,
    run_full_baseline,
)
from app.experiment.metrics import (
    PerRunMetrics,
    AggregatedMetrics,
    extract_metrics,
    aggregate_metrics,
)
from app.experiment.analysis import (
    compute_anova,
    pairwise_bonferroni,
    pairwise_holm,
    cohens_d,
    power_analysis,
    generate_statistical_report,
    significance_matrix,
)
from app.experiment.dataset import (
    ExperimentScenario,
    ScenarioLabel,
    GroundTruthConfig,
    ExperimentDataset,
    generate_synthetic_dataset,
    check_ground_truth_consistency,
)
from app.experiment.evaluation import (
    fleiss_kappa,
    agreement_matrix,
    per_category_agreement,
    kappa_interpretation,
    ExpertEvaluationRound,
    evaluate_expert_agreement,
    AgreementReport,
)
from app.experiment.config import (
    ExperimentConfig,
    ConfigVersion,
    ConfigSweep,
    config_hash,
    save_config_snapshot,
    load_config_snapshot,
)
from app.experiment.orchestrator import (
    ExperimentOrchestrator,
    OrchestratorResult,
    RunResult,
    orchestrator_summary_table,
)
from app.experiment.anomaly import (
    AnomalyReport,
    AnomalyCollection,
    detect_anomalies,
)
from app.experiment.export import (
    export_to_csv,
    export_to_json,
    export_summary,
    export_latex_table,
    export_all,
)
from app.experiment.report import (
    generate_latex_report,
    generate_markdown_report,
)
from app.experiment.replay import (
    replay_from_config,
    verify_reproducibility,
)

__all__ = [
    # Context / isolation
    "ExperimentContext",
    "ExperimentRegistry",
    "ExperimentSnapshot",
    "ExperimentState",
    "reset_all_global_state",
    # Conditions
    "ExperimentCondition",
    "get_all_conditions",
    "get_condition",
    "get_controls",
    "get_treatments",
    "get_ablations",
    "get_hypotheses",
    "FULL_SWARM",
    "UNIFORM_WEIGHTS",
    "SINGLE_AGENT",
    "NO_TRUST",
    "NO_SPECIALIZATION",
    # Pipelines
    "BatchPipeline",
    "SingleAgentPipeline",
    "PipelineResult",
    "PipelineRun",
    "run_full_baseline",
    # Metrics
    "PerRunMetrics",
    "AggregatedMetrics",
    "extract_metrics",
    "aggregate_metrics",
    # Analysis
    "compute_anova",
    "pairwise_bonferroni",
    "pairwise_holm",
    "cohens_d",
    "power_analysis",
    "generate_statistical_report",
    "significance_matrix",
    # Dataset
    "ExperimentScenario",
    "ScenarioLabel",
    "GroundTruthConfig",
    "ExperimentDataset",
    "generate_synthetic_dataset",
    "check_ground_truth_consistency",
    # Evaluation
    "fleiss_kappa",
    "agreement_matrix",
    "per_category_agreement",
    "kappa_interpretation",
    "ExpertEvaluationRound",
    "evaluate_expert_agreement",
    "AgreementReport",
    # Config
    "ExperimentConfig",
    "ConfigVersion",
    "ConfigSweep",
    "config_hash",
    "save_config_snapshot",
    "load_config_snapshot",
    # Orchestrator
    "ExperimentOrchestrator",
    "OrchestratorResult",
    "RunResult",
    "orchestrator_summary_table",
    # Anomaly
    "AnomalyReport",
    "AnomalyCollection",
    "detect_anomalies",
    # Export
    "export_to_csv",
    "export_to_json",
    "export_summary",
    "export_latex_table",
    "export_all",
    # Report
    "generate_latex_report",
    "generate_markdown_report",
    # Replay
    "replay_from_config",
    "verify_reproducibility",
]
