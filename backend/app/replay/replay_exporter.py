"""Export replay sessions to JSON, Markdown, LaTeX, and CSV."""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any


class ReplayExporter:
    """Exports a complete replay session in multiple formats."""

    def to_json(self, replay: dict[str, Any]) -> str:
        return json.dumps(replay, ensure_ascii=False, indent=2, default=str)

    def to_markdown(self, replay: dict[str, Any]) -> str:
        lines: list[str] = []
        steps = replay.get("steps", [])
        student_id = replay.get("student_id", "unknown")
        course_id = replay.get("course_id", "unknown")

        lines.append(f"# Replay Session: {student_id}")
        lines.append(f"**Course:** {course_id}")
        lines.append(f"**Weeks:** {len(steps)}")
        lines.append(f"**Generated:** {replay.get('generated_at', '')}")
        lines.append("")

        for i, step in enumerate(steps):
            w = step.get("week_number", i + 1)
            lines.append(f"## Week {w}")
            lines.append("")

            ad = step.get("adaptation", {})
            bloom = ad.get("bloom", {})
            lines.append(f"- **Bloom:** {bloom.get('previous', '?')} → {bloom.get('current', '?')} ({bloom.get('direction', 'stable')})")
            lines.append(f"- **Consensus:** {ad.get('consensus', {}).get('decision', '?')} (confidence: {ad.get('consensus', {}).get('confidence', 0.0):.2f})")
            lines.append(f"- **Scaffolding steps:** {ad.get('scaffolding', {}).get('current_count', 0)}")
            lines.append("")

            reasoning = step.get("reasoning", {})
            for exp in reasoning.get("explanations", []):
                dim = exp.get("dimension", "?")
                reasons = exp.get("reasons", [])
                lines.append(f"### {dim.title()}")
                for r in reasons:
                    lines.append(f"- {r.get('factor', '?').replace('_', ' ')}: {r.get('evidence', '')[:120]}")
                lines.append("")

            mem = step.get("memory", {})
            lines.append(f"Memory: {mem.get('total_records', 0)} records ({', '.join(mem.get('memory_types', []))})")
            lines.append("---")
            lines.append("")

        timeline = replay.get("timeline", {})
        lines.append("## Longitudinal Metrics")
        lines.append("")
        lines.append(f"- Bloom levels: {timeline.get('bloom_levels', [])}")
        lines.append(f"- Confidence scores: {[f'{c:.2f}' for c in timeline.get('confidence_scores', [])]}")
        lines.append(f"- Scaffolding counts: {timeline.get('scaffolding_counts', [])}")
        lines.append(f"- Misconception counts: {timeline.get('misconception_counts', [])}")
        lines.append(f"- Memory records: {timeline.get('memory_records', [])}")
        lines.append("")

        return "\n".join(lines)

    def to_latex(self, replay: dict[str, Any]) -> str:
        lines: list[str] = []
        steps = replay.get("steps", [])
        student_id = replay.get("student_id", "unknown")

        lines.append(r"\section{Replay Session: " + student_id + "}")
        lines.append(r"\begin{itemize}")
        lines.append(r"\item Weeks: " + str(len(steps)))
        lines.append(r"\item Generated: " + replay.get("generated_at", ""))
        lines.append(r"\end{itemize}")
        lines.append("")

        for i, step in enumerate(steps):
            w = step.get("week_number", i + 1)
            lines.append(r"\subsection{Week " + str(w) + "}")
            lines.append("")

            ad = step.get("adaptation", {})
            bloom = ad.get("bloom", {})
            lines.append(r"\begin{itemize}")
            lines.append(r"\item Bloom: " + str(bloom.get("previous", "?")) + r" $\to$ " + str(bloom.get("current", "?")) + " (" + bloom.get("direction", "stable") + ")")
            lines.append(r"\item Confidence: " + f"{ad.get('consensus', {}).get('confidence', 0.0):.2f}")
            lines.append(r"\item Scaffolding steps: " + str(ad.get("scaffolding", {}).get("current_count", 0)))
            lines.append(r"\end{itemize}")
            lines.append("")

            reasoning = step.get("reasoning", {})
            for exp in reasoning.get("explanations", []):
                dim = exp.get("dimension", "?")
                lines.append(r"\subsubsection{" + dim.title() + "}")
                lines.append(r"\begin{itemize}")
                for r in exp.get("reasons", []):
                    evidence = r.get("evidence", "")[:100]
                    lines.append(r"\item " + r.get("factor", "?").replace("_", " ") + ": " + evidence)
                lines.append(r"\end{itemize}")

            lines.append(r"\subsubsection{Memory}")
            mem = step.get("memory", {})
            lines.append(f"Records: {mem.get('total_records', 0)}")
            lines.append("")

        timeline = replay.get("timeline", {})
        lines.append(r"\subsection{Longitudinal Metrics}")
        lines.append(r"\begin{itemize}")
        lines.append(r"\item Bloom levels: " + str(timeline.get("bloom_levels", [])))
        lines.append(r"\item Confidence: " + str([f"{c:.2f}" for c in timeline.get("confidence_scores", [])]))
        lines.append(r"\end{itemize}")

        return "\n".join(lines)

    def to_csv(self, replay: dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["week", "bloom_previous", "bloom_current", "bloom_direction", "confidence", "scaffolding_count", "memory_records", "consensus_decision"])

        for step in replay.get("steps", []):
            w = step.get("week_number", 0)
            ad = step.get("adaptation", {})
            bloom = ad.get("bloom", {})
            consensus = ad.get("consensus", {})
            sc = ad.get("scaffolding", {})
            mem = step.get("memory", {})
            writer.writerow([
                w,
                bloom.get("previous"),
                bloom.get("current"),
                bloom.get("direction"),
                f"{consensus.get('confidence', 0.0):.4f}",
                sc.get("current_count", 0),
                mem.get("total_records", 0),
                consensus.get("decision", ""),
            ])

        return output.getvalue()

    def export_all(self, replay: dict[str, Any]) -> dict[str, str]:
        return {
            "json": self.to_json(replay),
            "markdown": self.to_markdown(replay),
            "latex": self.to_latex(replay),
            "csv": self.to_csv(replay),
        }


replay_exporter = ReplayExporter()
