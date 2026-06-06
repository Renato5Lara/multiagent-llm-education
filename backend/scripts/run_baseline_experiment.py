#!/usr/bin/env python3
"""
run_baseline_experiment.py — Execute the full thesis baseline.

Usage:
    python scripts/run_baseline_experiment.py [options]

Options:
    --seed INT         Random seed (default: 42)
    --n-runs INT       Number of runs per condition (default: 5)
    --n-contexts INT   Number of synthetic contexts to generate (default: 20)
    --label STR        Experiment label (default: "thesis-baseline")
    --output FILE      Save results as JSON (default: None, stdout only)
    --verbose          Enable debug logging

The script:
    1. Creates a ConsensusEngine with 4 voters
    2. Generates N synthetic VoteContexts
    3. Runs all 5 conditions on each context (within-subject)
    4. Repeats for n-runs (for power)
    5. Computes aggregated metrics per condition
    6. Runs statistical analysis (ANOVA, pairwise tests, effect sizes)
    7. Prints summary table and statistical report
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone

from app.core.consensus import ConsensusEngine, VoteContext, VoteDecision
from app.core.consensus import MasteryVoter, PrereqVoter, SequenceVoter, TimeVoter
from app.experiment import (
    get_all_conditions,
    get_hypotheses,
    run_full_baseline,
    generate_statistical_report,
    compute_anova,
)

logger = logging.getLogger(__name__)


def _build_synthetic_context(
    module_id: str,
    student_id: str,
    score: float = 0.7,
    *,
    seed: int,
) -> VoteContext:
    """Build a minimal VoteContext for testing.

    Uses fake objects (not SQLAlchemy models) so the script
    can run without a database connection.
    """

    class FakeModule:
        def __init__(self):
            self.id = module_id
            self.title = f"Module {module_id}"
            self.module_type = "exercise"
            self.bloom_level = "3"
            self.difficulty = 0.5
            self.status = "pending"

    class FakePath:
        def __init__(self):
            self.id = f"path-{module_id}"
            self.title = f"Path for {module_id}"

    class FakeUOW:
        db = None

    return VoteContext(
        uow=FakeUOW(),
        module_id=module_id,
        student_id=student_id,
        course_id=f"course-{module_id[:4]}",
        path_id=f"path-{module_id}",
        score=score,
        module=FakeModule(),
        path=FakePath(),
        timestamp=datetime.now(timezone.utc),
    )


def _generate_contexts(
    n: int,
    seed: int,
) -> list[VoteContext]:
    """Generate N synthetic VoteContexts with controlled variability."""
    import random
    rng = random.Random(seed)

    contexts: list[VoteContext] = []
    for i in range(n):
        score = round(rng.uniform(0.3, 0.95), 2)
        ctx = _build_synthetic_context(
            module_id=f"mod-{i:04d}",
            student_id=f"stu-{i:04d}",
            score=score,
            seed=seed + i,
        )
        contexts.append(ctx)
    return contexts


def _generate_ground_truth(
    contexts: list[VoteContext],
    seed: int,
) -> list[VoteDecision]:
    """Generate ground truth labels based on score threshold.

    A student with score >= 0.6 should PROBABLY be approved.
    This is a heuristic — real experiments use actual outcomes.
    """
    import random
    rng = random.Random(seed + 999)

    labels: list[VoteDecision] = []
    for ctx in contexts:
        if ctx.score >= 0.75:
            base = VoteDecision.APPROVE
        elif ctx.score <= 0.4:
            base = VoteDecision.REJECT
        else:
            base = VoteDecision.APPROVE if rng.random() < 0.5 else VoteDecision.REJECT
        labels.append(base)
    return labels


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full thesis experimental baseline",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--n-runs", type=int, default=5, help="Runs per condition")
    parser.add_argument("--n-contexts", type=int, default=20, help="Number of synthetic contexts")
    parser.add_argument("--label", type=str, default="thesis-baseline", help="Experiment label")
    parser.add_argument("--output", type=str, default=None, help="Output JSON file path")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )

    # Header
    print("=" * 72)
    print("  THESIS BASELINE — Swarm Educational Consensus")
    print("=" * 72)
    print()
    print(f"  Seed:      {args.seed}")
    print(f"  N runs:    {args.n_runs}")
    print(f"  N contexts: {args.n_contexts}")
    print(f"  Label:     {args.label}")
    print()

    # Hypotheses
    print("-" * 72)
    print("  Pre-registered Hypotheses:")
    for h in get_hypotheses():
        print(f"    {h}")
    print()

    # Build engine
    engine = ConsensusEngine()
    print(f"  Voters: {[v.voter_name for v in engine.voters]}")
    print(f"  Conditions: {[c.name for c in get_all_conditions()]}")
    print()

    # Generate contexts
    contexts = _generate_contexts(args.n_contexts, args.seed)
    ground_truth = _generate_ground_truth(contexts, args.seed)
    print(f"  Generated {len(contexts)} contexts with ground truth")
    print()

    # Run baseline
    print("-" * 72)
    print("  Running baseline...")
    sys.stdout.flush()

    t0 = time.monotonic()
    result = await run_full_baseline(
        engine,
        contexts,
        ground_truth=ground_truth,
        seed=args.seed,
        n_runs=args.n_runs,
        label=args.label,
    )
    elapsed = time.monotonic() - t0

    print(f"  Done in {elapsed:.1f}s")
    print()

    # Summary table
    print("-" * 72)
    print("  RESULTS")
    print("-" * 72)
    print()
    print(result.summary_table())
    print()

    # Statistical analysis on accuracy
    print("-" * 72)
    print("  STATISTICAL ANALYSIS")
    print("-" * 72)
    print()

    accuracy_groups: dict[str, list[float]] = {}
    for cname, agg in result.aggregated.items():
        cond_runs = [r.metrics.correct for r in result.runs if r.condition == cname and r.metrics.correct is not None]
        if cond_runs:
            accuracy_groups[cname] = [float(c) for c in cond_runs]

    if len(accuracy_groups) >= 2:
        report = generate_statistical_report(accuracy_groups, metric_name="accuracy")
        print(report)
    else:
        print("  Insufficient data for statistical analysis.")
    print()

    # Confidence calibration analysis
    print("-" * 72)
    print("  CONFIDENCE CALIBRATION")
    print("-" * 72)
    print()
    for cname, agg in result.aggregated.items():
        print(f"  {cname:22s}  ECE={agg.ece:.4f}  MCE={agg.mce:.4f}  "
              f"Avg conf={agg.avg_confidence:.3f}")
    print()

    # Summary
    print("-" * 72)
    print("  SUMMARY")
    print("-" * 72)
    print(f"  Total runs: {len(result.runs)}")
    print(f"  Conditions: {len(result.aggregated)}")
    for cname, agg in result.aggregated.items():
        sig = ""
        if accuracy_groups.get(cname) and agg.accuracy > 0.5:
            sig = "✓"
        print(f"    {cname:22s}  acc={agg.accuracy:.3f} ±{agg.accuracy_std:.3f}  "
              f"lat={agg.avg_latency_ms:.1f}ms  {sig}")

    # Save output
    if args.output:
        output = result.to_dict()
        output["statistics"] = {
            "hypotheses": get_hypotheses(),
            "seed": args.seed,
            "n_contexts": args.n_contexts,
        }
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\n  Results saved to: {args.output}")

    print()
    print("=" * 72)
    print("  Baseline complete.")
    print("=" * 72)


if __name__ == "__main__":
    asyncio.run(main())
