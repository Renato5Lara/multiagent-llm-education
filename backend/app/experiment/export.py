"""Metrics export for experiment results.

Supports:
    - CSV export (flat table, one row per run, ideal for pandas/R)
    - JSON export (full structured data for programmatic analysis)
    - LaTeX table export (thesis-ready tables)
    - Summary statistics export
"""

from __future__ import annotations

import csv
import json
import os
from typing import Any

from app.experiment.orchestrator import OrchestratorResult


# ── CSV Export ──────────────────────────────────────────

def export_to_csv(
    result: OrchestratorResult,
    path: str,
) -> None:
    """Export experiment runs to a flat CSV file.

    One row per run. Columns include all PerRunMetrics fields
    plus condition, seed, correctness, and swarm metrics.
    """
    fieldnames = [
        "condition", "run_index", "seed", "decision", "confidence",
        "correct", "elapsed_ms", "tokens_used", "llm_calls",
        # PerRunMetrics
        "unanimous", "total_latency_ms",
        # SwarmMetrics
        "cognitive_diversity", "deliberation_impact",
        "polarization_index", "cross_pollination_rate", "calibration_delta",
    ]

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for run in result.runs:
            row = {
                "condition": run.condition_name,
                "run_index": run.run_index,
                "seed": run.seed,
                "decision": run.decision.value,
                "confidence": round(run.confidence, 4),
                "correct": int(run.correct),
                "elapsed_ms": round(run.elapsed_ms, 2),
                "tokens_used": run.tokens_used,
                "llm_calls": run.llm_calls,
                "unanimous": int(run.metrics.unanimous) if run.metrics else 0,
                "total_latency_ms": round(run.metrics.total_latency_ms, 2) if run.metrics else 0.0,
            }
            if run.swarm_metrics:
                row.update({
                    "cognitive_diversity": round(run.swarm_metrics.cognitive_diversity, 4),
                    "deliberation_impact": round(run.swarm_metrics.deliberation_impact, 4),
                    "polarization_index": round(run.swarm_metrics.polarization_index, 4),
                    "cross_pollination_rate": round(run.swarm_metrics.cross_pollination_rate, 4),
                    "calibration_delta": round(run.swarm_metrics.calibration_delta, 4),
                })
            writer.writerow(row)


# ── JSON Export ─────────────────────────────────────────

def export_to_json(
    result: OrchestratorResult,
    path: str,
) -> None:
    """Export full experiment result to JSON."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    result.save(path)


# ── Summary Export ──────────────────────────────────────

def export_summary(
    result: OrchestratorResult,
    path: str,
) -> None:
    """Export a human-readable summary (TXT format)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    from app.experiment.orchestrator import orchestrator_summary_table

    summary = result.summary()
    table = orchestrator_summary_table(result)

    lines = [
        "=" * 60,
        "EXPERIMENT SUMMARY",
        "=" * 60,
        f"Config hash: {summary['config_hash']}",
        f"Total runs:  {summary['n_runs']}",
        f"Conditions:  {', '.join(summary['conditions'])}",
        "",
        "=" * 60,
        "ACCURACY BY CONDITION",
        "=" * 60,
    ]

    for row in table:
        lines.append(f"  {row[0]:<25s} {row[1]:>8s} (conf: {row[2]:>8s}, n={row[3]:>4s}, correct: {row[4]:>10s})")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ── LaTeX Table Export ──────────────────────────────────

def export_latex_table(
    result: OrchestratorResult,
    path: str,
    *,
    caption: str = "Experiment Results by Condition",
    label: str = "tab:experiment_results",
) -> None:
    """Export a LaTeX table of results suitable for thesis inclusion.

    Generates a booktabs-style table with accuracy, confidence,
    and swarm metrics per condition.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    from app.experiment.analysis import cohens_d
    import statistics

    conditions = result.conditions
    control = "single_agent"

    rows = []
    for cond in conditions:
        runs = result.by_condition(cond)
        if not runs:
            continue
        correct = sum(1 for r in runs if r.correct)
        n = len(runs)
        acc = correct / n
        avg_conf = statistics.mean([r.confidence for r in runs])
        avg_lat = statistics.mean([r.elapsed_ms for r in runs])

        # Effect size vs control
        if cond != control and control in conditions:
            control_runs = result.by_condition(control)
            control_accs = [1.0 if r.correct else 0.0 for r in control_runs]
            cond_accs = [1.0 if r.correct else 0.0 for r in runs]
            d = cohens_d(cond_accs, control_accs)
            d_str = f"{d:.3f}"
        else:
            d_str = "---"

        # Swarm metrics (average across runs)
        swarm_cols = {}
        sm_runs = [r for r in runs if r.swarm_metrics is not None]
        if sm_runs:
            swarm_cols = {
                "diversity": statistics.mean(
                    r.swarm_metrics.cognitive_diversity for r in sm_runs
                ),
                "impact": statistics.mean(
                    r.swarm_metrics.deliberation_impact for r in sm_runs
                ),
                "polarization": statistics.mean(
                    r.swarm_metrics.polarization_index for r in sm_runs
                ),
                "cross_pollination": statistics.mean(
                    r.swarm_metrics.cross_pollination_rate for r in sm_runs
                ),
            }
        else:
            swarm_cols = {
                "diversity": 0.0, "impact": 0.0,
                "polarization": 0.0, "cross_pollination": 0.0,
            }

        rows.append({
            "condition": cond.replace("_", " ").title(),
            "n": n,
            "accuracy": acc,
            "confidence": avg_conf,
            "latency_ms": avg_lat,
            "cohens_d": d_str,
            **swarm_cols,
        })

    if not rows:
        return

    # Build LaTeX
    has_swarm = any(r["diversity"] > 0.0 for r in rows)
    metrics_cols = "c c c" + (" c c c c" if has_swarm else "")
    header_cols = "l c " + metrics_cols + " c"

    lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        "\\small",
        "\\begin{{tabular}}{{{}}}".format(header_cols),
        "\\toprule",
    ]

    # Header row
    if has_swarm:
        lines.append(
            "Condition & N & Accuracy & Confidence & Latency (ms) & "
            "Cog. Div. & Delib. Impact & Polarization & Cross-Poll. & Cohen's d \\\\"
        )
    else:
        lines.append(
            "Condition & N & Accuracy & Confidence & Latency (ms) & Cohen's d \\\\"
        )
    lines.append("\\midrule")

    # Data rows
    for r in rows:
        if has_swarm:
            lines.append(
                f"{r['condition']} & {r['n']} & "
                f"{r['accuracy']:.3f} & {r['confidence']:.3f} & {r['latency_ms']:.0f} & "
                f"{r['diversity']:.3f} & {r['impact']:.3f} & {r['polarization']:.3f} & "
                f"{r['cross_pollination']:.3f} & {r['cohens_d']} \\\\"
            )
        else:
            lines.append(
                f"{r['condition']} & {r['n']} & "
                f"{r['accuracy']:.3f} & {r['confidence']:.3f} & {r['latency_ms']:.0f} & "
                f"{r['cohens_d']} \\\\"
            )

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
        f"\\caption*{{Effect sizes (Cohen's d) are relative to {control.replace('_', ' ')} control condition.}}",
        "\\end{table}",
    ])

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ── All exports at once ─────────────────────────────────

def export_all(
    result: OrchestratorResult,
    output_dir: str,
    *,
    base_name: str = "experiment",
) -> dict[str, str]:
    """Export experiment results in all formats.

    Args:
        result: The experiment result to export.
        output_dir: Directory to write exports to.
        base_name: Base filename (without extension).

    Returns:
        Dict mapping format -> file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = {}

    csv_path = os.path.join(output_dir, f"{base_name}.csv")
    export_to_csv(result, csv_path)
    paths["csv"] = csv_path

    json_path = os.path.join(output_dir, f"{base_name}.json")
    export_to_json(result, json_path)
    paths["json"] = json_path

    summary_path = os.path.join(output_dir, f"{base_name}_summary.txt")
    export_summary(result, summary_path)
    paths["summary"] = summary_path

    tex_path = os.path.join(output_dir, f"{base_name}_table.tex")
    export_latex_table(result, tex_path)
    paths["latex"] = tex_path

    return paths
