"""
Experimental Pipelines — orchestrate reproducible multi-condition experiments.

Architecture:
    SingleRunPipeline  — run one condition on one VoteContext
    BatchPipeline      — run all conditions on N VoteContexts (cross-validation style)
    FullBaseline       — run the complete thesis baseline (all 5 conditions x N runs)

Reproducibility:
    - Fixed random seed per experiment
    - Deterministic ordering of conditions and runs
    - All random state recorded in experiment metadata
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.consensus import ConsensusEngine, ConsensusResult, VoteDecision
from app.core.specialization import SpecializationTracker
from app.core.trust import TrustSystem
from app.experiment.conditions import (
    ExperimentCondition,
    get_all_conditions,
    get_condition,
)
from app.experiment.context import ExperimentContext, ExperimentState
from app.experiment.metrics import (
    AggregatedMetrics,
    PerRunMetrics,
    aggregate_metrics,
    extract_metrics,
)

logger = logging.getLogger(__name__)


@dataclass
class PipelineRun:
    """Result of a single pipeline execution."""

    condition: str
    run_index: int
    decision: str
    confidence: float
    correct: bool | None
    elapsed_ms: float
    metrics: PerRunMetrics
    result: ConsensusResult | None = None


@dataclass
class PipelineResult:
    """Aggregated result across all conditions and runs."""

    seed: int
    timestamp: str
    n_runs_per_condition: int
    experiment_id: str
    label: str
    runs: list[PipelineRun] = field(default_factory=list)
    aggregated: dict[str, AggregatedMetrics] = field(default_factory=dict)

    def summary_table(self) -> str:
        lines = [
            f"Baseline: {self.label}",
            f"Seed: {self.seed}  |  Runs per condition: {self.n_runs_per_condition}",
            f"Experiment: {self.experiment_id[:8]}",
            "",
            f"{'Condition':<22} {'n':>4} {'Accuracy':>10} {'Conf':>8} {'ECE':>8} {'Lat(ms)':>10} {'Unanim':>8}",
            "-" * 72,
        ]
        for cname in [c.name for c in get_all_conditions()]:
            agg = self.aggregated.get(cname)
            if agg is None:
                continue
            lines.append(
                f"{agg.condition_name:<22} {agg.n_runs:>4} "
                f"{agg.accuracy:>8.3f} ±{agg.accuracy_std:.3f} "
                f"{agg.avg_confidence:>7.3f} "
                f"{agg.ece:>8.4f} "
                f"{agg.avg_latency_ms:>8.1f} "
                f"{agg.unanimous_rate:>7.1%}"
            )
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "timestamp": self.timestamp,
            "n_runs_per_condition": self.n_runs_per_condition,
            "experiment_id": self.experiment_id,
            "label": self.label,
            "runs": [r.metrics.to_dict() for r in self.runs],
            "aggregated": {
                cname: {
                    "accuracy": agg.accuracy,
                    "accuracy_std": agg.accuracy_std,
                    "avg_confidence": agg.avg_confidence,
                    "ece": agg.ece,
                    "avg_latency_ms": agg.avg_latency_ms,
                    "unanimous_rate": agg.unanimous_rate,
                    "n_runs": agg.n_runs,
                }
                for cname, agg in self.aggregated.items()
            },
        }


class BatchPipeline:
    """Run all experimental conditions on multiple VoteContexts.

    Each condition receives the same VoteContexts (within-subject design).
    The order of conditions is randomized per run to control for order effects.
    """

    def __init__(
        self,
        engine: ConsensusEngine,
        seed: int = 42,
        conditions: list[ExperimentCondition] | None = None,
    ):
        self.engine = engine
        self.seed = seed
        self.conditions = conditions or get_all_conditions()
        self._rng = random.Random(seed)

    async def run(
        self,
        contexts: list[Any],
        *,
        ground_truth: list[VoteDecision] | None = None,
        n_runs: int = 1,
        label: str = "baseline",
        per_run_callback: Callable | None = None,
    ) -> PipelineResult:
        """Execute all conditions on all contexts.

        Args:
            contexts: List of VoteContext-like objects.
            ground_truth: Optional list of expected decisions (per context).
            n_runs: Number of times to repeat (for power analysis).
            label: Human-readable label.
            per_run_callback: Optional async callback (condition, run_index, result).

        Returns:
            PipelineResult with all runs and aggregated metrics.
        """
        experiment_id = hashlib.sha256(
            f"{self.seed}:{label}:{time.time()}".encode()
        ).hexdigest()[:32]

        all_runs: list[PipelineRun] = []
        completed = 0
        total = len(self.conditions) * len(contexts) * n_runs

        for run_idx in range(n_runs):
            # Randomize condition order per run to control order effects
            cond_order = list(self.conditions)
            self._rng.shuffle(cond_order)

            for cond in cond_order:
                for ctx_idx, ctx in enumerate(contexts):
                    gt = ground_truth[ctx_idx] if ground_truth else None
                    pr = await self._run_single(
                        cond, ctx, run_idx * len(contexts) + ctx_idx,
                        ground_truth=gt,
                    )
                    all_runs.append(pr)
                    completed += 1

                    if per_run_callback:
                        await per_run_callback(cond, run_idx, pr)

        # Aggregate per condition
        aggregated: dict[str, AggregatedMetrics] = {}
        for cond in self.conditions:
            cond_runs = [r for r in all_runs if r.condition == cond.name]
            if cond_runs:
                metrics_list = [r.metrics for r in cond_runs]
                aggregated[cond.name] = aggregate_metrics(metrics_list)

        return PipelineResult(
            seed=self.seed,
            timestamp=__import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat(),
            n_runs_per_condition=total // len(self.conditions) if self.conditions else 0,
            experiment_id=experiment_id,
            label=label,
            runs=all_runs,
            aggregated=aggregated,
        )

    async def _run_single(
        self,
        cond: ExperimentCondition,
        ctx: Any,
        run_index: int,
        *,
        ground_truth: VoteDecision | None = None,
    ) -> PipelineRun:
        """Execute a single condition-run."""
        async with ExperimentContext(label=f"{cond.name}-run-{run_index}") as exp:
            kwargs = cond.configure_engine(
                self.engine,
                trust_system=exp.trust_system,
                specialization_tracker=SpecializationTracker(),
            )

            start = time.monotonic()
            result = await self.engine.async_run(ctx, **kwargs)
            elapsed_ms = (time.monotonic() - start) * 1000.0

            exp.record_result(result)

            pr_metrics = extract_metrics(
                result, cond.name, run_index, ground_truth=ground_truth,
            )

            return PipelineRun(
                condition=cond.name,
                run_index=run_index,
                decision=result.decision.value,
                confidence=result.confidence,
                correct=pr_metrics.correct,
                elapsed_ms=elapsed_ms,
                metrics=pr_metrics,
                result=result,
            )


class SingleAgentPipeline:
    """Pipeline for the single-agent control condition.

    Instead of running consensus, runs a single voter in isolation.
    This measures: "what would a single agent decide without swarm?"
    """

    def __init__(self, voter_name: str = "MasteryVoter"):
        self.voter_name = voter_name

    async def run(
        self,
        engine: ConsensusEngine,
        ctx: Any,
        run_index: int = 0,
        ground_truth: VoteDecision | None = None,
    ) -> PipelineRun:
        """Run a single voter as the decision-maker."""
        # Find the named voter
        voter = None
        for v in engine.voters:
            if v.voter_name == self.voter_name:
                voter = v
                break
        if voter is None and engine.voters:
            voter = engine.voters[0]

        start = time.monotonic()
        vote = voter.vote(ctx)
        elapsed_ms = (time.monotonic() - start) * 1000.0

        # Build a minimal ConsensusResult-like object
        from app.core.consensus import ConsensusResult as CR

        result = CR(
            module_id=ctx.module_id,
            student_id=ctx.student_id,
            decision=vote.decision,
            confidence=vote.confidence,
            votes=[vote],
            trace_id=None,
            voter_timings=[{
                "voter_name": voter.voter_name,
                "decision": vote.decision.value,
                "confidence": vote.confidence,
                "duration_ms": elapsed_ms,
                "status": "ok",
            }],
            weights_used={},
            trust_scores={},
            specialization_affinities={},
            memory_ids=[],
            inference_ids=[],
            timeout_info=None,
        )

        # unanimous is a @property computed from votes (single vote = always unanimous)
        pr_metrics = extract_metrics(result, "single_agent", run_index, ground_truth=ground_truth)

        return PipelineRun(
            condition="single_agent",
            run_index=run_index,
            decision=vote.decision.value,
            confidence=vote.confidence,
            correct=pr_metrics.correct,
            elapsed_ms=elapsed_ms,
            metrics=pr_metrics,
            result=result,
        )


async def run_full_baseline(
    engine: ConsensusEngine,
    contexts: list[Any],
    *,
    ground_truth: list[VoteDecision] | None = None,
    seed: int = 42,
    n_runs: int = 1,
    label: str = "thesis-baseline",
) -> PipelineResult:
    """Run the complete thesis baseline: all 5 conditions x N contexts x runs.

    This is the top-level entrypoint for the experimental pipeline.
    """
    pipeline = BatchPipeline(
        engine=engine,
        seed=seed,
    )
    result = await pipeline.run(
        contexts=contexts,
        ground_truth=ground_truth,
        n_runs=n_runs,
        label=label,
    )

    # Add single-agent runs
    single = SingleAgentPipeline()
    for run_idx in range(n_runs):
        for ctx_idx, ctx in enumerate(contexts):
            gt = ground_truth[ctx_idx] if ground_truth else None
            pr = await single.run(
                engine, ctx,
                run_index=run_idx * len(contexts) + ctx_idx,
                ground_truth=gt,
            )
            result.runs.append(pr)

    # Re-aggregate including single_agent
    sa_runs = [r for r in result.runs if r.condition == "single_agent"]
    if sa_runs:
        result.aggregated["single_agent"] = aggregate_metrics([r.metrics for r in sa_runs])

    return result
