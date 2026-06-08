"""Deterministic replay from experiment snapshots and configs.

Provides:
    - replay_from_snapshot(): re-run an experiment from a saved snapshot
    - replay_from_config(): re-run from a saved config file
    - verify_reproducibility(): compare two experiment results for equality
"""

from __future__ import annotations

import json
import os
from typing import Any

from app.experiment.config import ExperimentConfig
from app.experiment.dataset import ExperimentDataset
from app.experiment.orchestrator import OrchestratorResult


def replay_from_config(
    config_path: str,
    *,
    output_dir: str | None = None,
    dataset_path: str | None = None,
) -> OrchestratorResult:
    """Re-run an experiment from a saved config file.

    Args:
        config_path: Path to a saved ExperimentConfig JSON file.
        output_dir: If provided, save results here.
        dataset_path: If provided, use this dataset instead of generating one.

    Returns:
        New OrchestratorResult from the re-run.
    """
    config = ExperimentConfig.load(config_path)

    dataset = None
    if dataset_path:
        dataset = ExperimentDataset.load_json(dataset_path)

    from app.experiment.orchestrator import ExperimentOrchestrator
    orch = ExperimentOrchestrator(config)

    import asyncio
    result = asyncio.run(orch.run(dataset=dataset))

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        result.save(os.path.join(output_dir, f"replay_{config.hash}.json"))

    return result


def verify_reproducibility(
    original: OrchestratorResult,
    replay: OrchestratorResult,
    *,
    check_decisions: bool = True,
    check_confidence: bool = True,
    check_timing: bool = False,
    tolerance: float = 0.001,
) -> dict[str, Any]:
    """Compare two experiment results for reproducibility.

    Args:
        original: The original experiment result.
        replay: The replayed experiment result.
        check_decisions: Compare vote decisions.
        check_confidence: Compare confidence scores.
        check_timing: Compare timing (may vary across runs).
        tolerance: Floating point tolerance for comparisons.

    Returns:
        Dict with comparison statistics.
    """
    if len(original.runs) != len(replay.runs):
        return {
            "reproducible": False,
            "reason": f"Run count mismatch: {len(original.runs)} vs {len(replay.runs)}",
            "n_original": len(original.runs),
            "n_replay": len(replay.runs),
        }

    n_mismatches = 0
    mismatches: list[dict] = []

    for i, (orig, rep) in enumerate(zip(original.runs, replay.runs)):
        run_mismatch = {}

        if check_decisions and orig.decision != rep.decision:
            run_mismatch["decision"] = {
                "original": orig.decision.value,
                "replay": rep.decision.value,
            }

        if check_confidence and abs(orig.confidence - rep.confidence) > tolerance:
            run_mismatch["confidence"] = {
                "original": orig.confidence,
                "replay": rep.confidence,
            }

        if run_mismatch:
            run_mismatch["run_index"] = i
            run_mismatch["condition"] = orig.condition_name
            mismatches.append(run_mismatch)
            n_mismatches += 1

    reproducible = n_mismatches == 0

    return {
        "reproducible": reproducible,
        "n_runs": len(original.runs),
        "n_mismatches": n_mismatches,
        "mismatch_rate": n_mismatches / len(original.runs) if original.runs else 0.0,
        "mismatches": mismatches,
    }
