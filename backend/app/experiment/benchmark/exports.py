"""
Benchmark Exports — Generación de reportes académicos formateados.

Produce:
  - report.md (reporte completo)
  - executive_summary.md (resumen ejecutivo)
  - results.csv (datos planos)
  - tables.tex (tablas LaTeX)
  - benchmark.json (datos completos estructurados)
  - benchmark_replay.json (reproducibilidad)
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime, timezone
from typing import Any

from app.experiment.benchmark.metrics import (
    BenchmarkResult,
    BenchmarkMetrics,
    condition_summary,
    aggregate_metrics,
)
from app.experiment.benchmark.statistics import (
    StatisticalReport,
    StatisticalTestSuite,
)


class ReportGenerator:
    """Generador de reportes Markdown estructurados."""

    METRIC_LABELS = {
        "pass_at_1": "Pass@1",
        "correction_rate": "Tasa de Corrección",
        "grounding_score": "Puntaje de Grounding",
        "misconception_coverage": "Cobertura de Misconceptions",
        "bloom_alignment": "Alineación Bloom",
        "adaptation_impact": "Impacto de Adaptación",
        "hallucination_reduction": "Reducción de Alucinación",
        "sandbox_validation_success": "Éxito en Sandbox",
        "execution_success": "Éxito de Ejecución",
        "consensus_confidence": "Confianza del Consenso",
        "retrieval_confidence": "Confianza de Recuperación",
        "prompt_grounding_score": "Grounding de Prompts",
        "personalization_impact": "Impacto de Personalización",
    }

    METRIC_DESCRIPTIONS = {
        "pass_at_1": "Proporción de escenarios donde el sistema genera un plan correcto al primer intento.",
        "correction_rate": "Proporción de errores detectados que son corregidos exitosamente.",
        "grounding_score": "Grado de alineación con teoría educativa y taxonomía de Bloom.",
        "misconception_coverage": "Proporción de misconceptions conocidas del estudiante que son abordadas.",
        "bloom_alignment": "Precisión en la asignación del nivel Bloom respecto al ground truth.",
        "adaptation_impact": "Mejora relativa del contenido adaptado versus el contenido baseline.",
        "hallucination_reduction": "Proporción de contenido generado que es factualmente correcto.",
        "sandbox_validation_success": "Proporción de código generado que compila y ejecuta correctamente.",
        "execution_success": "Proporción de pasos de la pipeline que completan exitosamente.",
        "consensus_confidence": "Confianza promedio de los voters en las decisiones de consenso.",
        "retrieval_confidence": "Calidad promedio del contenido recuperado (Tavily).",
        "prompt_grounding_score": "Grado de contextualización de los prompts generados.",
        "personalization_impact": "Grado de adaptación al perfil individual del estudiante.",
    }

    def __init__(self, results: list[BenchmarkResult]):
        self.results = results
        self.summary = condition_summary(results)
        self.conditions_order = [
            "single-agent_static",
            "swarm_full",
            "swarm_no_retrieval",
            "swarm_no_memory",
            "swarm_no_reviewer",
            "swarm_static_pedagogy",
        ]

    def _condition_label(self, name: str) -> str:
        labels = {
            "single-agent_static": "Agente Único Estático",
            "swarm_full": "Enjambre Completo",
            "swarm_no_retrieval": "Enjambre sin Recuperación",
            "swarm_no_memory": "Enjambre sin Memoria",
            "swarm_no_reviewer": "Enjambre sin Revisor",
            "swarm_static_pedagogy": "Enjambre con Pedagogía Estática",
        }
        return labels.get(name, name)

    def _metric_row(
        self, metric_key: str, best: str | None = None,
    ) -> list[str]:
        row = [self.METRIC_LABELS.get(metric_key, metric_key)]
        for cond in self.conditions_order:
            if cond in self.summary:
                val = self.summary[cond].get(metric_key, 0.0)
                formatted = f"{val:.4f}"
                if best and cond == best:
                    formatted = f"**{formatted}**"
                row.append(formatted)
            else:
                row.append("—")
        return row

    def _find_best_condition(self, metric_key: str) -> str | None:
        best_val = -1.0
        best_cond = None
        for cond in self.conditions_order:
            if cond in self.summary:
                val = self.summary[cond].get(metric_key, 0.0)
                if val > best_val:
                    best_val = val
                    best_cond = cond
        return best_cond

    def generate_full_report(self) -> str:
        lines = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        lines.append(f"# Reporte de Benchmark Académico")
        lines.append(f"**UPAO-MAS-EDU v1.0.0** — {now}")
        lines.append(f"**Total de ejecuciones:** {len(self.results)}")
        lines.append("")

        # ── Condiciones ──
        lines.append("## Condiciones Evaluadas")
        lines.append("")
        lines.append("| Condición | Tipo | Descripción |")
        lines.append("|-----------|------|-------------|")
        for cond in self.conditions_order:
            if cond in self.summary:
                n = self.summary[cond].get("_count", 0)
                types = {
                    "single-agent_static": "Control",
                    "swarm_full": "Tratamiento",
                }
                t = types.get(cond, "Ablación")
                labels = {
                    "single-agent_static": "Agente pedagógico único sin adaptación ni memoria.",
                    "swarm_full": "Sistema completo con todos los agentes y capacidades.",
                    "swarm_no_retrieval": "Enjambre sin ResearchAgent (Tavily desactivado).",
                    "swarm_no_memory": "Enjambre sin memoria compartida.",
                    "swarm_no_reviewer": "Enjambre sin ConsistencyAgent (revisor).",
                    "swarm_static_pedagogy": "Enjambre con pedagogía no adaptativa.",
                }
                lines.append(
                    f"| {self._condition_label(cond)} | {t} | {labels.get(cond, '')} |"
                )
        lines.append("")

        # ── Tabla de métricas agregadas ──
        lines.append("## Métricas Agregadas por Condición")
        lines.append("")
        header = ["Métrica"] + [self._condition_label(c) for c in self.conditions_order if c in self.summary]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join("---" for _ in header) + "|")

        metric_keys = [k for k in BenchmarkMetrics.__dataclass_fields__.keys()]
        for key in metric_keys:
            best = self._find_best_condition(key)
            row = self._metric_row(key, best)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines.append("*Nota: Los valores en **negrita** indican el mejor rendimiento para cada métrica.*")
        lines.append("")

        # ── Descripción de métricas ──
        lines.append("## Descripción de Métricas")
        lines.append("")
        for key, label in self.METRIC_LABELS.items():
            desc = self.METRIC_DESCRIPTIONS.get(key, "")
            lines.append(f"- **{label}**: {desc}")
        lines.append("")

        # ── Análisis estadístico ──
        lines.append("## Análisis Estadístico")
        lines.append("")
        lines.append("### Comparación: Enjambre Completo vs Agente Único Estático")
        lines.append("")

        suite = StatisticalTestSuite(alpha=0.05)
        swarm_results = [
            r for r in self.results if r.condition_name == "swarm_full"
        ]
        single_results = [
            r for r in self.results if r.condition_name == "single-agent_static"
        ]

        if swarm_results and single_results:
            report = suite.compare_conditions(
                swarm_results, single_results,
                "Enjambre Completo", "Agente Único Estático",
            )
            lines.append("| Métrica | Media (Enjambre) | Media (Agente Único) | Mann-Whitney U | p-valor | Sig. | Cohen's d | Efecto |")
            lines.append("|---------|------------------|---------------------|----------------|---------|------|-----------|--------|")
            for metric, summary in report.metric_summaries.items():
                label = self.METRIC_LABELS.get(metric, metric)
                ma = summary.get("mean_a", 0)
                mb = summary.get("mean_b", 0)
                mw = summary.get("mw_statistic", 0)
                pv = summary.get("mw_p", 1)
                sig = "✅" if summary.get("mw_sig") else "❌"
                d_val = summary.get("cohens_d", 0)
                d_label = summary.get("cohens_d_label", "")
                lines.append(
                    f"| {label} | {ma:.4f} | {mb:.4f} | {mw:.4f} | {pv:.4f} | {sig} | {d_val:.3f} | {d_label} |"
                )
            lines.append("")

        # ── Conclusiones ──
        lines.append("## Conclusiones")
        lines.append("")
        if swarm_results and single_results:
            swarm_agg = aggregate_metrics(swarm_results)
            single_agg = aggregate_metrics(single_results)
            imp = {}
            for k in swarm_agg:
                if single_agg.get(k, 0) > 0:
                    imp[k] = (swarm_agg[k] - single_agg[k]) / single_agg[k] * 100

            lines.append("### Mejora Relativa del Enjambre Completo sobre Agente Único")
            lines.append("")
            lines.append("| Métrica | Mejora (%) |")
            lines.append("|---------|-----------|")
            for k, v in sorted(imp.items(), key=lambda x: -abs(x[1])):
                label = self.METRIC_LABELS.get(k, k)
                arrow = "↑" if v > 0 else "↓"
                lines.append(f"| {label} | {arrow} {abs(v):.1f}% |")
            lines.append("")

        lines.append("---")
        lines.append(f"*Reporte generado automáticamente el {now}*")
        lines.append("")

        return "\n".join(lines)

    def generate_executive_summary(self) -> str:
        lines = []
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        lines.append("# Resumen Ejecutivo — Benchmark Académico")
        lines.append("")
        lines.append(f"**Sistema:** UPAO-MAS-EDU v1.0.0")
        lines.append(f"**Fecha:** {now}")
        lines.append(f"**Escenarios:** {len(self.results)} ejecuciones en 6 condiciones")
        lines.append("")

        lines.append("## Hallazgos Principales")
        lines.append("")

        swarm_results = [
            r for r in self.results if r.condition_name == "swarm_full"
        ]
        single_results = [
            r for r in self.results if r.condition_name == "single-agent_static"
        ]

        if swarm_results and single_results:
            sa = aggregate_metrics(swarm_results)
            si = aggregate_metrics(single_results)

            for k in ["pass_at_1", "grounding_score", "hallucination_reduction",
                       "adaptation_impact", "personalization_impact"]:
                label = ReportGenerator.METRIC_LABELS.get(k, k)
                v_swarm = sa.get(k, 0)
                v_single = si.get(k, 0)
                diff = (v_swarm - v_single) * 100
                arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="
                lines.append(f"- **{label}**: {arrow} {abs(diff):.1f}% ({v_swarm:.3f} vs {v_single:.3f})")

        lines.append("")
        lines.append("## Ranking de Condiciones")
        lines.append("")

        scores = {}
        for cond in self.conditions_order:
            if cond in self.summary:
                s = self.summary[cond]
                avg = sum(s.get(k, 0) for k in BenchmarkMetrics.__dataclass_fields__.keys()) / 13
                scores[cond] = avg

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        lines.append("| Posición | Condición | Puntaje Compuesto |")
        lines.append("|----------|-----------|-------------------|")
        for i, (cond, score) in enumerate(ranked, 1):
            lines.append(f"| {i} | {self._condition_label(cond)} | {score:.4f} |")

        lines.append("")
        lines.append("## Conclusión")
        lines.append("")
        if ranked:
            best_cond = ranked[0][0]
            best_label = self._condition_label(best_cond)
            lines.append(
                f"El sistema **{best_label}** demuestra el mejor rendimiento "
                f"general con un puntaje compuesto de **{ranked[0][1]:.4f}**."
            )

        lines.append("")
        lines.append("---")
        lines.append(f"*Resumen ejecutivo generado el {now}*")
        lines.append("")

        return "\n".join(lines)

    def save_report(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_full_report())

    def save_executive_summary(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_executive_summary())


class LaTeXTableGenerator:
    """Generador de tablas LaTeX para publicación académica."""

    METRIC_SHORT = {
        "pass_at_1": "Pass@1",
        "correction_rate": "Corr. Rate",
        "grounding_score": "Grounding",
        "misconception_coverage": "Mis. Coverage",
        "bloom_alignment": "Bloom Align.",
        "adaptation_impact": "Adapt. Impact",
        "hallucination_reduction": "Halluc. Red.",
        "sandbox_validation_success": "Sandbox",
        "execution_success": "Exec. Success",
        "consensus_confidence": "Cons. Conf.",
        "retrieval_confidence": "Retr. Conf.",
        "prompt_grounding_score": "Prompt Ground.",
        "personalization_impact": "Personalization",
    }

    def __init__(self, results: list[BenchmarkResult]):
        self.results = results
        self.summary = condition_summary(results)
        self.conditions_order = [
            "single-agent_static", "swarm_full",
            "swarm_no_retrieval", "swarm_no_memory",
            "swarm_no_reviewer", "swarm_static_pedagogy",
        ]

    def _cond_label_latex(self, name: str) -> str:
        labels = {
            "single-agent_static": "\\textsc{SingleAgent}",
            "swarm_full": "\\textsc{SwarmFull}",
            "swarm_no_retrieval": "\\textsc{NoRetrieval}",
            "swarm_no_memory": "\\textsc{NoMemory}",
            "swarm_no_reviewer": "\\textsc{NoReviewer}",
            "swarm_static_pedagogy": "\\textsc{StaticPed}",
        }
        return labels.get(name, name)

    def generate_metrics_table(self) -> str:
        lines = []
        conds = [c for c in self.conditions_order if c in self.summary]
        n_conds = len(conds)

        lines.append("% Auto-generated LaTeX table — UPAO-MAS-EDU Benchmark")
        lines.append(r"\begin{table}[htbp]")
        lines.append(r"\centering")
        lines.append(r"\caption{Metrics Comparison Across Conditions}")
        lines.append(r"\label{tab:benchmark_metrics}")
        lines.append(r"\begin{tabular}{l" + "c" * n_conds + "}")
        lines.append(r"\toprule")

        header = ["Metric"] + [self._cond_label_latex(c) for c in conds]
        lines.append(" & ".join(header) + r" \\")
        lines.append(r"\midrule")

        for key in BenchmarkMetrics.__dataclass_fields__.keys():
            short = self.METRIC_SHORT.get(key, key)
            row = [short]
            for cond in conds:
                val = self.summary[cond].get(key, 0.0)
                row.append(f"{val:.4f}")
            lines.append(" & ".join(row) + r" \\")

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("")

        return "\n".join(lines)

    def generate_statistics_table(self) -> str:
        lines = []
        swarm_results = [
            r for r in self.results if r.condition_name == "swarm_full"
        ]
        single_results = [
            r for r in self.results if r.condition_name == "single-agent_static"
        ]

        if not swarm_results or not single_results:
            return "% No data for statistics table"

        suite = StatisticalTestSuite(alpha=0.05)
        report = suite.compare_conditions(
            swarm_results, single_results,
            "SwarmFull", "SingleAgent",
        )

        lines.append(r"\begin{table}[htbp]")
        lines.append(r"\centering")
        lines.append(r"\caption{Statistical Comparison: SwarmFull vs SingleAgent}")
        lines.append(r"\label{tab:benchmark_statistics}")
        lines.append(r"\begin{tabular}{lcccc}")
        lines.append(r"\toprule")
        lines.append(
            r"Metric & \textsc{SingleAgent} & \textsc{SwarmFull} "
            r"& $p$-value & Cohen's $d$ \\"
        )
        lines.append(r"\midrule")

        for metric, summ in report.metric_summaries.items():
            short = self.METRIC_SHORT.get(metric, metric)
            ma = summ.get("mean_b", 0)
            mb = summ.get("mean_a", 0)
            pv = summ.get("mw_p", 1)
            d_val = summ.get("cohens_d", 0)
            sig = "^{***}" if pv < 0.001 else "^{**}" if pv < 0.01 else "^{*}" if pv < 0.05 else ""
            lines.append(
                f"{short} & {ma:.3f} & {mb:.3f} & {pv:.4f}{sig} & {d_val:.3f} \\\\"
            )

        lines.append(r"\bottomrule")
        lines.append(r"\end{tabular}")
        lines.append(r"\end{table}")
        lines.append("")

        return "\n".join(lines)

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        content = []
        content.append(self.generate_metrics_table())
        content.append(self.generate_statistics_table())
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(content))


class ExportManager:
    """Maneja todas las exportaciones del benchmark."""

    def __init__(self, results: list[BenchmarkResult]):
        self.results = results
        self.report_gen = ReportGenerator(results)
        self.latex_gen = LaTeXTableGenerator(results)

    def export_csv(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        keys = list(BenchmarkMetrics.__dataclass_fields__.keys())
        fieldnames = [
            "condition", "seed", "scenario_id",
        ] + keys + ["execution_time_ms"]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in self.results:
                row = {
                    "condition": r.condition_name,
                    "seed": r.seed,
                    "scenario_id": r.scenario_id,
                    "execution_time_ms": round(r.execution_time_ms, 2),
                }
                for k in keys:
                    row[k] = round(getattr(r.metrics, k, 0.0), 6)
                writer.writerow(row)
        return path

    def export_json(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        data = {
            "benchmark_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_runs": len(self.results),
            "conditions": list(
                sorted(set(r.condition_name for r in self.results))
            ),
            "results": [
                {
                    "condition": r.condition_name,
                    "seed": r.seed,
                    "scenario_id": r.scenario_id,
                    "metrics": r.metrics.to_dict(),
                    "execution_time_ms": round(r.execution_time_ms, 2),
                }
                for r in self.results
            ],
            "summary": condition_summary(self.results),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def export_replay(self, path: str) -> str:
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        config = {
            "replay_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "seed_base": 42,
            "n_scenarios": len(set(r.scenario_id for r in self.results)),
            "conditions": list(
                sorted(set(r.condition_name for r in self.results))
            ),
            "hash": hash(tuple(
                (r.condition_name, r.seed, r.scenario_id,
                 tuple(r.metrics.to_dict().items()))
                for r in self.results
            )),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return path

    def export_all(self, output_dir: str) -> dict[str, str]:
        os.makedirs(output_dir, exist_ok=True)

        report_path = os.path.join(output_dir, "report.md")
        self.report_gen.save_report(report_path)

        summary_path = os.path.join(output_dir, "executive_summary.md")
        self.report_gen.save_executive_summary(summary_path)

        csv_path = os.path.join(output_dir, "results.csv")
        self.export_csv(csv_path)

        tex_path = os.path.join(output_dir, "tables.tex")
        self.latex_gen.save(tex_path)

        json_path = os.path.join(output_dir, "benchmark.json")
        self.export_json(json_path)

        replay_path = os.path.join(output_dir, "benchmark_replay.json")
        self.export_replay(replay_path)

        return {
            "report": report_path,
            "executive_summary": summary_path,
            "csv": csv_path,
            "latex": tex_path,
            "json": json_path,
            "replay": replay_path,
        }
