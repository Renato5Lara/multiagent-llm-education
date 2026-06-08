#!/usr/bin/env python3
"""
run_real_benchmark.py — Benchmark REAL UPAO-MAS-EDU v1.0.0

Ejecuta el benchmark ejecutando el PIPELINE REAL del swarm pedagógico
(no proxy ni datos sintéticos).

A diferencia de run_academic_benchmark.py, este script:
  - Crea conexiones reales a PostgreSQL
  - Instancia agentes reales (Research, StructuralPedagogical, etc.)
  - Ejecuta LLM real (OpenAI/Ollama)
  - Mide latencia real por fase
  - Soporta timeout, retry, cancelación y graceful degradation

Uso:
    python scripts/run_real_benchmark.py
    python scripts/run_real_benchmark.py --scenarios 10 --runs 2 --timeout 60
    python scripts/run_real_benchmark.py --conditions swarm_full single_agent_static
    python scripts/run_real_benchmark.py --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="UPAO-MAS-EDU Real Swarm Benchmark v1.0.0",
    )
    parser.add_argument(
        "--scenarios", type=int, default=10,
        help="Number of scenarios per condition (default: 10)",
    )
    parser.add_argument(
        "--runs", type=int, default=2,
        help="Number of runs per condition (default: 2)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default="benchmark_real_results",
        help="Output directory (default: benchmark_real_results)",
    )
    parser.add_argument(
        "--conditions", type=str, nargs="*",
        help="Specific conditions to run (default: all 6)",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0,
        help="Timeout per experiment in seconds (default: 120)",
    )
    parser.add_argument(
        "--max-retries", type=int, default=2,
        help="Max retries per experiment (default: 2)",
    )
    parser.add_argument(
        "--no-graceful", action="store_true",
        help="Disable graceful degradation (fail fast)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print configuration and exit without executing",
    )
    parser.add_argument(
        "--enable-tracing", action="store_true",
        help="Enable distributed tracing during benchmark",
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="Override DATABASE_URL for the benchmark session",
    )
    return parser.parse_args()


def print_banner(config: dict) -> None:
    print()
    print("=" * 72)
    print("  UPAO-MAS-EDU — REAL SWARM BENCHMARK v1.0.0")
    print("  Ejecución REAL del pipeline pedagógico (no proxy)")
    print("=" * 72)
    print()
    for k, v in config.items():
        print(f"  {k:30s} {v}")
    print()
    print(f"  Total experiments: {config['total_experiments']}")
    print()


async def main_async() -> int:
    args = parse_args()

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    # ── Override DB URL if provided ───────────────────────────────
    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    from app.experiment.benchmark.real import (
        SwarmExecutionBenchmarkRunner,
        SwarmExecutionConfig,
        export_real_all,
    )

    conditions = args.conditions or [
        "single-agent_static",
        "swarm_full",
        "swarm_no_retrieval",
        "swarm_no_memory",
        "swarm_no_reviewer",
        "swarm_static_pedagogy",
    ]

    total = len(conditions) * args.runs * args.scenarios

    config_data = {
        "scenarios_per_condition": args.scenarios,
        "runs_per_condition": args.runs,
        "total_experiments": total,
        "seed": args.seed,
        "conditions": ", ".join(conditions),
        "timeout_per_experiment_s": args.timeout,
        "max_retries": args.max_retries,
        "graceful_degradation": not args.no_graceful,
        "output_dir": os.path.abspath(args.output),
        "dry_run": args.dry_run,
    }

    print_banner(config_data)

    if args.dry_run:
        print("  Dry-run mode. Set --dry-run to execute.")
        print()
        return 0

    swarm_config = SwarmExecutionConfig(
        seed=args.seed,
        n_scenarios=args.scenarios,
        n_runs_per_condition=args.runs,
        conditions=conditions,
        output_dir=os.path.abspath(args.output),
        timeout_per_experiment=args.timeout,
        max_retries=args.max_retries,
        graceful=not args.no_graceful,
        enable_tracing=args.enable_tracing,
    )

    runner = SwarmExecutionBenchmarkRunner(swarm_config)

    print("  Initializing database connections...")
    print("  Executing real swarm pipeline...")
    print()

    t_start = time.time()

    try:
        results = await runner.run()
    except KeyboardInterrupt:
        print()
        print("  ⚠  Benchmark cancelled by user (KeyboardInterrupt)")
        return 130
    except Exception as e:
        print(f"  ❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    t_elapsed = time.time() - t_start
    degraded = sum(1 for r in results if r.metadata.get("degraded", False))
    errors = sum(1 for r in results if r.metadata.get("error", ""))

    print()
    print(f"  Completed {len(results)} real experiments in {t_elapsed:.1f}s")
    print(f"  Degraded: {degraded} | Errors: {errors}")
    print()

    # ── Show summary ──────────────────────────────────────────────
    summary = runner.summary()
    if summary:
        conditions_order = [
            "single-agent_static", "swarm_full",
            "swarm_no_retrieval", "swarm_no_memory",
            "swarm_no_reviewer", "swarm_static_pedagogy",
        ]
        labels = {
            "single-agent_static": "Single-Agent Static",
            "swarm_full": "Swarm Full",
            "swarm_no_retrieval": "Swarm No Retrieval",
            "swarm_no_memory": "Swarm No Memory",
            "swarm_no_reviewer": "Swarm No Reviewer",
            "swarm_static_pedagogy": "Swarm Static Pedagogy",
        }

        print("  ┌─────────────────────────────────────────────────────────┐")
        print("  │                  REAL BENCHMARK RESULTS                 │")
        print("  ├─────────────────────────────────────────────────────────┤")
        print(f"  │  Total real executions: {len(results):>5}                            │")
        print(f"  │  Time:                  {t_elapsed:>5.1f}s                           │")
        print("  ├─────────────────────────────────────────────────────────┤")

        for cond in conditions_order:
            if cond in summary:
                s = summary[cond]
                label = labels.get(cond, cond)
                pass1 = s.get("pass_at_1", 0)
                hall = s.get("hallucination_reduction", 0)
                adapt = s.get("adaptation_impact", 0)
                ground = s.get("grounding_score", 0)
                avg_ms = _avg_timing(results, cond)
                avg_tokens = _avg_tokens(results, cond)
                print(f"  │  {label:<27} │")
                print(f"  │    Pass@1: {pass1:.3f}  Hall.Red: {hall:.3f}  │")
                print(f"  │    Adapt:  {adapt:.3f}  Ground:  {ground:.3f}  │")
                print(f"  │    Ø Time: {avg_ms:>6.0f}ms  Ø Tokens: {avg_tokens:>6.0f}        │")
                print(f"  │    Runs:   {s.get('_count', 0):>4}                              │")

        print("  └─────────────────────────────────────────────────────────┘")
        print()

    # ── Export results ────────────────────────────────────────────
    print("  Exporting real benchmark results...")
    paths = export_real_all(results, swarm_config)

    for name, path in paths.items():
        print(f"    ✅ {name}: {path}")

    print()
    print("=" * 72)
    print("  REAL BENCHMARK COMPLETE")
    print("=" * 72)
    print()

    return 0


def _avg_timing(results, condition: str) -> float:
    """Average execution time for a condition."""
    timings = [
        r.execution_time_ms
        for r in results
        if r.condition_name == condition and r.execution_time_ms > 0
    ]
    return sum(timings) / len(timings) if timings else 0.0


def _avg_tokens(results, condition: str) -> float:
    """Approximate token usage from phase timings (proxy metric)."""
    totals = []
    for r in results:
        if r.condition_name != condition:
            continue
        timings = r.metadata.get("phase_timings_ms", {})
        total_ms = sum(v for v in timings.values() if v > 0)
        totals.append(total_ms)
    return sum(totals) / len(totals) if totals else 0.0


def main() -> int:
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
