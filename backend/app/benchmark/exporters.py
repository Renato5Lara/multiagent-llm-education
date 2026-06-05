from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from app.benchmark.schemas import BenchmarkRunRecord, StatisticalComparison


class BenchmarkExporter:
    def export(
        self,
        output_dir: str,
        experiment_id: str,
        records: list[BenchmarkRunRecord],
        aggregates: list[dict],
        comparisons: list[StatisticalComparison],
    ) -> dict[str, str]:
        out = Path(output_dir) / experiment_id
        out.mkdir(parents=True, exist_ok=True)
        paths = {
            "csv": str(out / "results.csv"),
            "json": str(out / "summary.json"),
            "jsonl": str(out / "records.jsonl"),
            "markdown": str(out / "report.md"),
            "latex": str(out / "tables.tex"),
            "replay": str(out / "experiment_replay.json"),
        }
        self._csv(paths["csv"], records)
        self._jsonl(paths["jsonl"], records)
        self._json(paths["json"], experiment_id, aggregates, comparisons)
        self._markdown(paths["markdown"], experiment_id, aggregates, comparisons)
        self._latex(paths["latex"], aggregates, comparisons)
        self._replay(paths["replay"], records)
        return paths

    def _csv(self, path: str, records: list[BenchmarkRunRecord]) -> None:
        metric_names = sorted({key for record in records for key in record.metrics})
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["experiment_id", "task_id", "dataset", "variant", "success", *metric_names])
            writer.writeheader()
            for record in records:
                writer.writerow({
                    "experiment_id": record.experiment_id,
                    "task_id": record.task_id,
                    "dataset": record.dataset,
                    "variant": record.variant,
                    "success": record.success,
                    **record.metrics,
                })

    def _jsonl(self, path: str, records: list[BenchmarkRunRecord]) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")

    def _json(self, path: str, experiment_id: str, aggregates: list[dict], comparisons: list[StatisticalComparison]) -> None:
        payload = {
            "experiment_id": experiment_id,
            "aggregate_metrics": aggregates,
            "statistical_comparisons": [asdict(item) for item in comparisons],
        }
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _markdown(self, path: str, experiment_id: str, aggregates: list[dict], comparisons: list[StatisticalComparison]) -> None:
        lines = [f"# Benchmark Report: {experiment_id}", "", "## Aggregate Metrics", ""]
        lines.append("| variant | metric | mean |")
        lines.append("|---|---:|---:|")
        for row in aggregates:
            lines.append(f"| {row['variant']} | {row['metric']} | {float(row['mean']):.4f} |")
        lines.extend(["", "## Statistical Comparisons", "", "| metric | treatment | delta | p | Cohen d | CI 95% |", "|---|---|---:|---:|---:|---|"])
        for item in comparisons:
            lines.append(
                f"| {item.metric} | {item.treatment} | {item.delta:.4f} | {item.mann_whitney_p:.4f} | "
                f"{item.cohens_d:.4f} | [{item.ci_low:.4f}, {item.ci_high:.4f}] |"
            )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _latex(self, path: str, aggregates: list[dict], comparisons: list[StatisticalComparison]) -> None:
        lines = [
            "\\begin{tabular}{llr}",
            "\\toprule",
            "Variant & Metric & Mean \\\\",
            "\\midrule",
        ]
        for row in aggregates[:40]:
            lines.append(f"{row['variant']} & {row['metric'].replace('_', '\\_')} & {float(row['mean']):.4f} \\\\")
        lines.extend(["\\bottomrule", "\\end{tabular}", "", "\\begin{tabular}{lrrr}", "\\toprule", "Metric & Delta & p & Cohen's d \\\\", "\\midrule"])
        for item in comparisons[:40]:
            lines.append(f"{item.metric.replace('_', '\\_')} & {item.delta:.4f} & {item.mann_whitney_p:.4f} & {item.cohens_d:.4f} \\\\")
        lines.extend(["\\bottomrule", "\\end{tabular}", ""])
        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def _replay(self, path: str, records: list[BenchmarkRunRecord]) -> None:
        replay = {
            "event_count": len(records),
            "events": [
                {
                    "event_type": "benchmark.task_evaluated",
                    "task_id": record.task_id,
                    "variant": record.variant,
                    "payload": record.replay,
                }
                for record in records
            ],
        }
        Path(path).write_text(json.dumps(replay, ensure_ascii=False, indent=2), encoding="utf-8")
