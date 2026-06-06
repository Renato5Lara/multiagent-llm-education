#!/usr/bin/env python3
"""
run_academic_benchmark.py — Benchmark Académico Final UPAO-MAS-EDU v1.0.0

Ejecuta el benchmark completo del sistema multi-agente pedagógico:
  - 6 condiciones experimentales
  - 13 métricas de evaluación
  - Análisis estadístico (Mann-Whitney U, McNemar, Cohen's d)
  - Exports: report.md, executive_summary.md, results.csv, tables.tex, benchmark.json
  - Visualizaciones: 6 gráficos académicos

Uso:
    python scripts/run_academic_benchmark.py
    python scripts/run_academic_benchmark.py --scenarios 50 --runs 5 --output /tmp/benchmark
    python scripts/run_academic_benchmark.py --no-charts
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone


def main() -> int:
    parser = argparse.ArgumentParser(
        description="UPAO-MAS-EDU Academic Benchmark v1.0.0",
    )
    parser.add_argument(
        "--scenarios", type=int, default=50,
        help="Number of scenarios per condition (default: 50)",
    )
    parser.add_argument(
        "--runs", type=int, default=5,
        help="Number of runs per condition (default: 5)",
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
        "--no-charts", action="store_true",
        help="Skip chart generation",
    )
    parser.add_argument(
        "--conditions", type=str, nargs="*",
        help="Specific conditions to run (default: all 6)",
    )
    args = parser.parse_args()

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 70)
    print("  UPAO-MAS-EDU — Academic Benchmark v1.0.0")
    print("=" * 70)
    print()
    print(f"  Scenarios per condition: {args.scenarios}")
    print(f"  Runs per condition:      {args.runs}")
    print(f"  Seed:                    {args.seed}")
    print(f"  Output:                  {output_dir}")
    print(f"  Charts:                  {'disabled' if args.no_charts else 'enabled'}")
    print()

    # ── Import benchmark modules ──
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

    from app.experiment.benchmark.orchestrator import (
        BenchmarkOrchestrator,
        OrchestratorConfig,
    )
    from app.experiment.benchmark.exports import ExportManager
    from app.experiment.benchmark.metrics import condition_summary

    # ── Configuration ──
    config = OrchestratorConfig(
        seed=args.seed,
        n_scenarios=args.scenarios,
        n_runs_per_condition=args.runs,
        output_dir=output_dir,
        conditions=args.conditions if args.conditions else [
            "single-agent_static",
            "swarm_full",
            "swarm_no_retrieval",
            "swarm_no_memory",
            "swarm_no_reviewer",
            "swarm_static_pedagogy",
        ],
    )

    # ── Execute benchmark ──
    print("  Initializing orchestrator...")
    orchestrator = BenchmarkOrchestrator(config)

    print(f"  Running {len(config.conditions)} conditions × "
          f"{config.n_scenarios} scenarios × {config.n_runs_per_condition} runs...")
    print()

    t_start = time.time()
    results = orchestrator.run()
    t_elapsed = time.time() - t_start

    print(f"  Completed {len(results)} evaluations in {t_elapsed:.2f}s")
    print()

    # ── Summary ──
    summary = condition_summary(results)

    print("  ┌─────────────────────────────────────────────────────────┐")
    print("  │                  RESULTS SUMMARY                        │")
    print("  ├─────────────────────────────────────────────────────────┤")
    print(f"  │  Total evaluations: {len(results):>5}                                    │")
    print(f"  │  Time:              {t_elapsed:>5.1f}s                                   │")
    print("  ├─────────────────────────────────────────────────────────┤")

    conditions_order = [
        "single-agent_static", "swarm_full",
        "swarm_no_retrieval", "swarm_no_memory",
        "swarm_no_reviewer", "swarm_static_pedagogy",
    ]

    for cond in conditions_order:
        if cond in summary:
            s = summary[cond]
            pass1 = s.get("pass_at_1", 0)
            hall = s.get("hallucination_reduction", 0)
            adapt = s.get("adaptation_impact", 0)
            ground = s.get("grounding_score", 0)
            label = {
                "single-agent_static": "Single-Agent Static",
                "swarm_full": "Swarm Full",
                "swarm_no_retrieval": "Swarm No Retrieval",
                "swarm_no_memory": "Swarm No Memory",
                "swarm_no_reviewer": "Swarm No Reviewer",
                "swarm_static_pedagogy": "Swarm Static Pedagogy",
            }.get(cond, cond)
            print(f"  │  {label:<25} │")
            print(f"  │    Pass@1: {pass1:.4f}  Hall.Red: {hall:.4f}  │")
            print(f"  │    Adapt:  {adapt:.4f}  Ground:  {ground:.4f}  │")

    print("  └─────────────────────────────────────────────────────────┘")
    print()

    # ── Export results ──
    print("  Exporting results...")
    export_mgr = ExportManager(results)
    paths = export_mgr.export_all(output_dir)

    for name, path in paths.items():
        print(f"    ✅ {name}: {path}")

    # ── Generate charts ──
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
                    print(f"    ✅ {name}: {path}")
                else:
                    print(f"    ⚠  {name}: skipped (matplotlib not available)")
        except Exception as e:
            print(f"    ⚠  Charts failed: {e}")

    print()
    print("=" * 70)
    print("  BENCHMARK COMPLETE")
    print("=" * 70)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
