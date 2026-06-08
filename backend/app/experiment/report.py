"""Scientific report generation for swarm education experiments.

Generates thesis-ready reports in multiple formats:
    - LaTeX: full report with tables, figures (via stubs), and statistical analysis
    - Markdown: human-readable summary for quick review
    - Statistical appendix: detailed hypothesis testing results
"""

from __future__ import annotations

import os
import statistics
from typing import Any

from app.experiment.analysis import (
    compute_anova,
    cohens_d,
    generate_statistical_report,
    pairwise_bonferroni,
    significance_matrix,
)
from app.experiment.anomaly import detect_anomalies
from app.experiment.config import ExperimentConfig
from app.experiment.export import export_latex_table
from app.experiment.orchestrator import OrchestratorResult, orchestrator_summary_table


def generate_latex_report(
    result: OrchestratorResult,
    output_dir: str,
    *,
    title: str = "Swarm Cognition Experiment Report",
    author: str = "",
    include_appendix: bool = True,
) -> str:
    """Generate a complete LaTeX report for the experiment.

    Args:
        result: Orchestrator result with all run data.
        output_dir: Directory to write the report.
        title: Report title.
        author: Author name.
        include_appendix: Whether to include statistical appendix.

    Returns:
        Path to the generated .tex file.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, "experiment_report.tex")

    conditions = result.conditions
    summary = result.summary()

    # Build accuracy data per condition
    accuracies = {}
    for cond in conditions:
        runs = result.by_condition(cond)
        if not runs:
            continue
        correct = sum(1 for r in runs if r.correct)
        n = len(runs)
        acc = correct / n
        accuracies[cond] = {
            "accuracy": acc,
            "n": n,
            "correct": correct,
            "avg_confidence": statistics.mean([r.confidence for r in runs]),
            "avg_latency_ms": statistics.mean([r.elapsed_ms for r in runs]),
        }

    # ANOVA across treatment conditions
    treatments = [c for c in conditions if c != "single_agent"]
    anova_data = {}
    if len(treatments) >= 2:
        groups = {}
        for cond in treatments:
            runs = result.by_condition(cond)
            groups[cond] = [1.0 if r.correct else 0.0 for r in runs]
        try:
            anova_result = compute_anova(groups)
            anova_data = {
                "f_statistic": anova_result.f_statistic,
                "p_value": anova_result.p_value,
                "significant": anova_result.significant,
                "n_groups": anova_result.n_groups,
            }
        except Exception:
            anova_data = {}

    # Pairwise tests vs control
    control = "single_agent"
    pairwise_data = {}
    if control in conditions:
        control_runs = result.by_condition(control)
        control_accs = [1.0 if r.correct else 0.0 for r in control_runs]
        for cond in conditions:
            if cond == control:
                continue
            runs = result.by_condition(cond)
            cond_accs = [1.0 if r.correct else 0.0 for r in runs]
            d = cohens_d(cond_accs, control_accs)
            pairwise_data[cond] = {
                "cohens_d": d,
                "n_treatment": len(cond_accs),
                "n_control": len(control_accs),
            }

    # Anomalies
    anomalies = detect_anomalies(result)

    # Build LaTeX document
    lines = [
        "\\documentclass[11pt,a4paper]{article}",
        "\\usepackage[utf8]{inputenc}",
        "\\usepackage{booktabs}",
        "\\usepackage{amsmath}",
        "\\usepackage{geometry}",
        "\\usepackage{tabularx}",
        "\\usepackage{caption}",
        "\\geometry{margin=2.5cm}",
        "",
        f"\\title{{{title}}}",
        f"\\author{{{author}}}",
        f"\\date{{{result.completed_at.strftime('%B %d, %Y') if result.completed_at else ''}}}",
        "",
        "\\begin{document}",
        "\\maketitle",
        "",
        "\\section{Experiment Summary}",
        f"Total runs: {summary['n_runs']}",
        f"Conditions compared: {len(conditions)}",
        f"Config hash: \\texttt{{{summary['config_hash']}}}",
        "",
        "\\subsection{Accuracy by Condition}",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "Condition & N & Accuracy & Confidence & Latency (ms) \\\\",
        "\\midrule",
    ]

    for cond in conditions:
        if cond in accuracies:
            a = accuracies[cond]
            lines.append(
                f"{cond.replace('_', ' ').title()} & {a['n']} & "
                f"{a['accuracy']:.3f} & {a['avg_confidence']:.3f} & "
                f"{a['avg_latency_ms']:.0f} \\\\"
            )

    lines.extend([
        "\\bottomrule",
        "\\end{tabular}",
    ])

    # ANOVA results
    if anova_data:
        lines.extend([
            "",
            "\\subsection{ANOVA Results}",
            f"F-statistic: {anova_data.get('f_statistic', 'N/A'):.4f}",
            f"p-value: {anova_data.get('p_value', 'N/A'):.4f}",
            f"Significant at $\\alpha = 0.05$: {'Yes' if anova_data.get('significant') else 'No'}",
            f"Groups compared: {anova_data.get('n_groups', 0)}",
        ])

    # Effect sizes
    if pairwise_data:
        lines.extend([
            "",
            "\\subsection{Effect Sizes vs. Single Agent}",
            "\\begin{tabular}{lccc}",
            "\\toprule",
            "Condition & Cohen's d & N (treatment) & N (control) \\\\",
            "\\midrule",
        ])
        for cond, pd in pairwise_data.items():
            lines.append(
                f"{cond.replace('_', ' ').title()} & {pd['cohens_d']:.3f} & "
                f"{pd['n_treatment']} & {pd['n_control']} \\\\"
            )
        lines.extend([
            "\\bottomrule",
            "\\end{tabular}",
        ])

    # Anomalies
    if anomalies.anomalies:
        lines.extend([
            "",
            "\\subsection{Anomalies Detected}",
            f"Critical: {anomalies.n_critical}, Warnings: {anomalies.n_warnings}",
        ])
        for a in anomalies.anomalies:
            lines.append(
                f"\\textbf{{{a.severity}}}: {a.description} \\\\"
            )

    # LaTeX table from export module
    tex_table_path = os.path.join(output_dir, "results_table.tex")
    export_latex_table(result, tex_table_path)
    lines.extend([
        "",
        "\\subsection{Detailed Results}",
        f"\\input{{{tex_table_path.replace(os.path.commonpath([output_dir, tex_table_path]), '').lstrip('/')}}}",
    ])

    # Appendix
    if include_appendix:
        lines.extend([
            "",
            "\\appendix",
            "\\section{Statistical Appendix}",
        ])
        try:
            report = generate_statistical_report(result.runs, conditions)
            lines.append(report.replace("\n", "\n\n"))
        except Exception:
            lines.append("Statistical report generation failed.")

    lines.append("\\end{document}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return path


def generate_markdown_report(
    result: OrchestratorResult,
    output_path: str,
) -> str:
    """Generate a Markdown report summarizing experiment results."""
    summary = result.summary()
    table = orchestrator_summary_table(result)
    anomalies = detect_anomalies(result)

    lines = [
        "# Experiment Report",
        "",
        f"**Config hash:** `{summary['config_hash']}`",
        f"**Total runs:** {summary['n_runs']}",
        f"**Conditions:** {', '.join(summary['conditions'])}",
        f"**Started:** {result.started_at.isoformat()}",
        f"**Completed:** {result.completed_at.isoformat() if result.completed_at else 'N/A'}",
        "",
        "## Accuracy by Condition",
        "",
        "| Condition | Accuracy | Avg Confidence | N | Correct |",
        "|-----------|----------|---------------|----|---------|",
    ]

    for row in table[1:]:
        lines.append(f"| {' | '.join(row)} |")

    if anomalies.anomalies:
        lines.extend([
            "",
            "## Anomalies",
            "",
            f"**Critical:** {anomalies.n_critical}, **Warnings:** {anomalies.n_warnings}",
            "",
        ])
        for a in anomalies.anomalies:
            lines.append(f"- **[{a.severity}]** {a.description}")

    lines.append("")
    lines.append("## Raw Results")
    lines.append("")
    lines.append("See the exported CSV/JSON files for full per-run data.")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return output_path
