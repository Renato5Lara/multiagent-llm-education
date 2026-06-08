#!/usr/bin/env python3
"""
run_academic_benchmark.py — Benchmark Académico Final UPAO-MAS-EDU v1.0.0

Ejecuta el benchmark completo usando el PIPELINE REAL del swarm pedagógico:
  - 6 condiciones experimentales (1 control + 1 tratamiento + 4 ablaciones)
  - 13 métricas de evaluación derivadas de ejecución real
  - Análisis estadístico (Mann-Whitney U, McNemar, Cohen's d)
  - Exports: report.md, executive_summary.md, results.csv, tables.tex, benchmark.json

Nota: Esta versión utiliza SwarmExecutionBenchmarkRunner (ejecución real).
      Ya no usa BenchmarkOrchestrator (datos sintéticos con sesgos hardcodeados).

Uso:
    python scripts/run_academic_benchmark.py
    python scripts/run_academic_benchmark.py --scenarios 20 --runs 3 --output /tmp/benchmark
    python scripts/run_academic_benchmark.py --conditions swarm_full single-agent_static
    python scripts/run_academic_benchmark.py --no-charts
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UPAO-MAS-EDU Academic Benchmark v1.0.0 (Real Pipeline)",
    )
    parser.add_argument(
        "--scenarios", type=int, default=20,
        help="Number of scenarios per condition (default: 20)",
    )
    parser.add_argument(
        "--runs", type=int, default=3,
        help="Number of runs per condition (default: 3)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--output", type=str, default="benchmark_results",
        help="Output directory (default: benchmark_results)",
    )
    parser.add_argument(
        "--timeout", type=float, default=120.0,
        help="Timeout per experiment in seconds (default: 120)",
    )
    parser.add_argument(
        "--no-charts", action="store_true",
        help="Skip chart generation",
    )
    parser.add_argument(
        "--conditions", type=str, nargs="*",
        help="Specific conditions to run (default: all 6)",
    )
    parser.add_argument(
        "--db-url", type=str, default=None,
        help="Override DATABASE_URL for the benchmark session",
    )
    args = parser.parse_args()

    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if args.db_url:
        os.environ["DATABASE_URL"] = args.db_url

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from app.experiment.benchmark.real import (
        SwarmExecutionBenchmarkRunner,
        SwarmExecutionConfig,
        export_real_all,
    )
    from app.experiment.benchmark.metrics import condition_summary

    conditions = args.conditions or [
        "single-agent_static",
        "swarm_full",
        "swarm_no_retrieval",
        "swarm_no_memory",
        "swarm_no_reviewer",
        "swarm_static_pedagogy",
    ]

    total = len(conditions) * args.runs * args.scenarios

    print("=" * 70)
    print("  UPAO-MAS-EDU — Academic Benchmark v1.0.0 (Real Pipeline)")
    print("=" * 70)
    print()
    print(f"  Scenarios per condition: {args.scenarios}")
    print(f"  Runs per condition:      {args.runs}")
    print(f"  Seed:                    {args.seed}")
    print(f"  Timeout per experiment:  {args.timeout}s")
    print(f"  Output:                  {output_dir}")
    print(f"  Total experiments:       {total}")
    print()

    config = SwarmExecutionConfig(
        seed=args.seed,
        n_scenarios=args.scenarios,
        n_runs_per_condition=args.runs,
        conditions=conditions,
        output_dir=output_dir,
        timeout_per_experiment=args.timeout,
        max_retries=2,
        graceful=True,
    )

    runner = SwarmExecutionBenchmarkRunner(config)

    print("  Running real swarm pipeline benchmark...")
    print()

    t_start = time.time()
    try:
        results = await runner.run()
    except KeyboardInterrupt:
        print("\n  Benchmark cancelled by user.")
        return 130
    except Exception as e:
        print(f"  Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    t_elapsed = time.time() - t_start
    degraded = sum(1 for r in results if r.metadata.get("degraded", False))
    errors = sum(1 for r in results if r.metadata.get("error", ""))

    print(f"  Completed {len(results)} experiments in {t_elapsed:.1f}s")
    print(f"  Degraded: {degraded} | Errors: {errors}")
    print()

    summary = condition_summary(results)

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
    print("  │              REAL BENCHMARK RESULTS SUMMARY             │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  Total real executions: {len(results):>4}                             │")
    print(f"  │  Wall-clock time:       {t_elapsed:>5.1f}s                            │")
    print(f"  │  Degraded:              {degraded:>4}                             │")
    print("  ├─────────────────────────────────────────────────────────┤")

    for cond in conditions_order:
        if cond not in summary:
            continue
        s = summary[cond]
        label = labels.get(cond, cond)
        pass1 = s.get("pass_at_1", 0)
        hall = s.get("hallucination_reduction", 0)
        adapt = s.get("adaptation_impact", 0)
        ground = s.get("grounding_score", 0)
        n = s.get("_count", 0)
        avg_ms = _avg_timing(results, cond)
        print(f"  │  {label:<26}  (n={n:>3})            │")
        print(f"  │    Pass@1: {pass1:.3f}  Halluc.Red: {hall:.3f}              │")
        print(f"  │    Adapt:  {adapt:.3f}  Grounding:  {ground:.3f}              │")
        print(f"  │    Avg latency: {avg_ms:>7.0f}ms                          │")

    print("  └─────────────────────────────────────────────────────────┘")
    print()

    print("  Exporting results...")
    paths = export_real_all(results, config)

    for name, path in paths.items():
        print(f"    {name}: {path}")

    if not args.no_charts:
        try:
            print()
            print("  Generating charts...")
            from app.experiment.benchmark.visualization import VisualizationEngine, ChartConfig
            chart_config = ChartConfig(output_dir=os.path.join(output_dir, "charts"))
            viz = VisualizationEngine(results, chart_config)
            chart_paths = viz.generate_all()
            for name, path in chart_paths.items():
                if path:
                    print(f"    {name}: {path}")
                else:
                    print(f"    {name}: skipped (matplotlib not available)")
        except Exception as e:
            print(f"    Charts failed: {e}")

    print()
    print("=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)
    print()
    return 0


def _avg_timing(results, condition: str) -> float:
    timings = [
        r.execution_time_ms
        for r in results
        if r.condition_name == condition and r.execution_time_ms > 0
    ]
    return sum(timings) / len(timings) if timings else 0.0


if __name__ == "__main__":
    sys.exit(main())
