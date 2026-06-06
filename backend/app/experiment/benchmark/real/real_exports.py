"""Real exports — benchmark_real.json, benchmark_real.csv, benchmark_real_report.md, etc."""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from app.experiment.benchmark.metrics import BenchmarkMetrics, BenchmarkResult, condition_summary
from app.experiment.benchmark.exports import ReportGenerator, LaTeXTableGenerator
from app.experiment.benchmark.real.runner import SwarmExecutionConfig


REAL_METRIC_FIELDS = [
    "total_latency_ms",
    "latency_research_ms", "latency_pedagogical_ms", "latency_adaptive_ms",
    "latency_multimodal_planning_ms", "latency_prompt_engineering_ms",
    "latency_consistency_ms", "latency_sandbox_validation_ms", "latency_consensus_mediator_ms",
    "retry_count", "timeout_count",
    "sandbox_pass_rate", "sandbox_snippets_validated",
    "misconception_coverage", "grounding_score", "reviewer_correction_rate",
    "hallucinated_claims", "total_claims",
    "bloom_level_assigned", "baseline_score", "adapted_score",
]


def _real_path(output_dir: str, suffix: str) -> str:
    name = f"benchmark_real{suffix}"
    return os.path.join(output_dir, name)


def export_real_csv(results: list[BenchmarkResult], output_dir: str) -> str:
    """Export benchmark_real.csv with all metrics + real timings."""
    path = _real_path(output_dir, ".csv")
    fields = list(BenchmarkMetrics.__dataclass_fields__.keys())
    headers = [
        "condition", "seed", "scenario_id", *fields,
        "execution_time_ms", "degraded", "error", "retries",
        "research_ms", "pedagogical_ms", "adaptive_ms",
        "multimodal_ms", "prompt_ms", "consistency_ms", "sandbox_ms", "consensus_ms",
        *REAL_METRIC_FIELDS,
    ]

    os.makedirs(output_dir, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in results:
            timings = r.metadata.get("phase_timings_ms", {})
            system = getattr(r, "system_output", {}) or {}
            row = [
                r.condition_name,
                r.seed,
                r.scenario_id,
                *(getattr(r.metrics, f, 0.0) for f in fields),
                round(r.execution_time_ms, 2),
                r.metadata.get("degraded", False),
                r.metadata.get("error", ""),
                r.metadata.get("retries", 0),
                timings.get("research", ""),
                timings.get("pedagogical", ""),
                timings.get("adaptive", ""),
                timings.get("multimodal_planning", ""),
                timings.get("prompt_engineering", ""),
                timings.get("consistency", ""),
                timings.get("sandbox_validation", ""),
                timings.get("consensus_mediator", ""),
                *(system.get(f, 0.0) for f in REAL_METRIC_FIELDS),
            ]
            writer.writerow(row)
    return path


def export_real_json(results: list[BenchmarkResult], config: SwarmExecutionConfig, output_dir: str) -> str:
    """Export benchmark_real.json with full data + summary."""
    path = _real_path(output_dir, ".json")
    summary = condition_summary(results)

    payload = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "type": "real_swarm_execution",
        "config": {
            "seed": config.seed,
            "n_scenarios": config.n_scenarios,
            "n_runs_per_condition": config.n_runs_per_condition,
            "conditions": config.conditions,
            "timeout_per_experiment": config.timeout_per_experiment,
            "max_retries": config.max_retries,
            "graceful_degradation": config.graceful,
        },
        "total_runs": len(results),
        "conditions": sorted(set(r.condition_name for r in results)),
        "summary": summary,
        "results": [],
    }

    for r in results:
        system = getattr(r, "system_output", {}) or {}
        payload["results"].append({
            "condition_name": r.condition_name,
            "seed": r.seed,
            "scenario_id": r.scenario_id,
            "metrics": r.metrics.to_dict(),
            "real_metrics": {f: system.get(f, 0.0) for f in REAL_METRIC_FIELDS},
            "execution_time_ms": round(r.execution_time_ms, 2),
            "metadata": {
                "degraded": r.metadata.get("degraded", False),
                "error": r.metadata.get("error", ""),
                "retries": r.metadata.get("retries", 0),
                "phase_timings_ms": r.metadata.get("phase_timings_ms", {}),
                "sandbox_validated": r.metadata.get("sandbox_validated", False),
                "sandbox_snippets": r.metadata.get("sandbox_snippets", 0),
                "consistency_passed": r.metadata.get("consistency_passed", True),
            },
        })

    with open(path, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    return path


def export_real_replay(results: list[BenchmarkResult], config: SwarmExecutionConfig, output_dir: str) -> str:
    """Export benchmark_real_replay.json with REAL pipeline session IDs + hashes."""
    path = _real_path(output_dir, "_replay.json")

    sessions = []
    for r in results:
        session_id = r.metadata.get("session_id", "")
        phase_timings = r.metadata.get("phase_timings_ms", {})
        phase_count = r.metadata.get("phase_count", 0)
        degraded = r.metadata.get("degraded", False)
        sessions.append({
            "condition": r.condition_name,
            "scenario_id": r.scenario_id,
            "seed": r.seed,
            "session_id": session_id,
            "phase_count": phase_count,
            "phase_timings_ms": phase_timings,
            "degraded": degraded,
            "pass_at_1": getattr(r.metrics, "pass_at_1", 0.0),
            "hallucination_ratio": getattr(r.metrics, "hallucination_ratio", 0.0),
            "adaptation_impact": getattr(r.metrics, "adaptation_impact", 0.0),
            "execution_time_ms": round(r.execution_time_ms, 2),
        })

    decisions_str = "|".join(
        f"{s['condition']}:{s['scenario_id']}:{s['pass_at_1']}:{s['session_id']}"
        for s in sessions
    )
    replay_hash = sha256(decisions_str.encode()).hexdigest()[:16]

    payload = {
        "replay_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "type": "real_swarm_execution",
        "config": {
            "seed": config.seed,
            "n_scenarios": config.n_scenarios,
            "n_runs_per_condition": config.n_runs_per_condition,
            "conditions": config.conditions,
            "timeout_per_experiment": config.timeout_per_experiment,
            "max_retries": config.max_retries,
        },
        "hash": replay_hash,
        "session_count": len(sessions),
        "sessions": sessions,
    }

    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    return path


def export_real_report(results: list[BenchmarkResult], output_dir: str) -> str:
    """Export benchmark_real_report.md with real execution context."""
    path = _real_path(output_dir, "_report.md")
    os.makedirs(output_dir, exist_ok=True)

    report_gen = ReportGenerator(results)
    base_report = report_gen.generate_full_report()

    summary = condition_summary(results)

    degraded_count = sum(1 for r in results if r.metadata.get("degraded", False))
    error_count = sum(1 for r in results if r.metadata.get("error", ""))
    total_timing = sum(r.execution_time_ms for r in results)
    sandbox_runs = sum(1 for r in results if r.metadata.get("sandbox_validated", False))
    avg_retries = sum(r.metadata.get("retries", 0) for r in results) / max(len(results), 1)

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    real_header = (
        f"# Reporte de Benchmark REAL\n"
        f"**UPAO-MAS-EDU v1.0.0** — {now_str}\n"
        f"**Tipo:** Ejecución REAL del swarm pedagógico (no proxy)\n\n"
        f"## Estadísticas de Ejecución\n\n"
        f"| Métrica | Valor |\n"
        f"|---------|-------|\n"
        f"| Total ejecuciones | {len(results)} |\n"
        f"| Ejecuciones degradadas | {degraded_count} |\n"
        f"| Ejecuciones con error | {error_count} |\n"
        f"| Tiempo total acumulado | {total_timing / 1000:.1f}s |\n"
        f"| Tiempo promedio por ejecución | {(total_timing / max(len(results), 1)):.1f}ms |\n"
        f"| Promedio de reintentos | {avg_retries:.2f} |\n"
        f"| Ejecuciones con sandbox | {sandbox_runs} |\n\n"
        f"## Métricas Reales Promedio por Condición\n\n"
        f"| Condición | pass@1 | Halluc. Ratio | Adapt. Impact | Latencia | Sandbox Pass | Misconception Coverage |\n"
        f"|-----------|--------|--------------|--------------|----------|-------------|----------------------|\n"
    )

    by_condition = {}
    for r in results:
        by_condition.setdefault(r.condition_name, []).append(r)

    for cname, cresults in by_condition.items():
        n = len(cresults)
        avg_pass = sum(getattr(r.metrics, "pass_at_1", 0.0) for r in cresults) / n
        avg_halluc = sum(getattr(r.metrics, "hallucination_ratio", 0.0) for r in cresults) / n
        avg_adapt = sum(getattr(r.metrics, "adaptation_impact", 0.0) for r in cresults) / n
        avg_latency = sum(r.execution_time_ms for r in cresults) / n
        avg_sandbox = sum(
            getattr(r, "system_output", {}).get("sandbox_pass_rate", 0.0)
            for r in cresults
        ) / n
        avg_coverage = sum(
            getattr(r, "system_output", {}).get("misconception_coverage", 0.0)
            for r in cresults
        ) / n
        real_header += f"| {cname} | {avg_pass:.3f} | {avg_halluc:.3f} | {avg_adapt:.3f} | {avg_latency:.1f}ms | {avg_sandbox:.1f}% | {avg_coverage:.1f}% |\n"

    real_header += "\n---\n\n"
    with open(path, "w") as f:
        f.write(real_header + base_report)
    return path


def export_real_tables(results: list[BenchmarkResult], output_dir: str) -> str:
    """Export benchmark_real_tables.tex with real execution data."""
    path = _real_path(output_dir, "_tables.tex")
    os.makedirs(output_dir, exist_ok=True)

    latex_gen = LaTeXTableGenerator(results)
    tables = latex_gen.generate_metrics_table()

    stats = latex_gen.generate_statistics_table() if len(results) > 50 else ""

    preamble = r"""% Auto-generated LaTeX table — UPAO-MAS-EDU REAL Benchmark
% Note: These results come from REAL swarm pipeline execution, not proxy/synthetic data.

"""
    with open(path, "w") as f:
        f.write(preamble + tables + "\n\n" + stats)
    return path


def export_real_all(
    results: list[BenchmarkResult],
    config: SwarmExecutionConfig,
) -> dict[str, str]:
    """Export all real benchmark files."""
    output_dir = config.output_dir
    os.makedirs(output_dir, exist_ok=True)

    paths = {
        "csv": export_real_csv(results, output_dir),
        "json": export_real_json(results, config, output_dir),
        "replay": export_real_replay(results, config, output_dir),
        "report": export_real_report(results, output_dir),
        "tables": export_real_tables(results, output_dir),
    }
    return paths
