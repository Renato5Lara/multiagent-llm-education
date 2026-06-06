"""
BugReportMarkdownWriter — Converts BugReport dataclass instances into
structured markdown files under docs/bug_reports/{category}/.

Template-driven with sections mirroring the forensic bug report format:
    metadata, symptoms, root cause, reproduction flow, architectural risk,
    swarm / adaptation / consensus / resilience / shared memory impact,
    fix, tests, observability, regression prevention, affected files, lessons.

Usage:
    writer = BugReportMarkdownWriter()
    path = writer.write(report, target_dir="/path/to/docs/bug_reports/auth")
"""

from __future__ import annotations

import os
from typing import Any

from app.bug_reports.models import BugReport


class BugReportMarkdownWriter:
    """Writes BugReport instances to structured markdown files."""

    def write(self, report: BugReport, target_dir: str) -> str:
        """Write a single bug report as markdown and return the file path."""
        filename = f"{report.filename_slug}.md"
        path = os.path.join(target_dir, filename)
        content = self._render(report)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    # ── Main template ─────────────────────────────────────────

    def _render(self, report: BugReport) -> str:
        sev = report.severity.value if hasattr(report.severity, "value") else report.severity
        cat = report.category.value if hasattr(report.category, "value") else report.category
        status = report.status.value if hasattr(report.status, "value") else report.status

        sections = [
            self._header(report, sev, cat, status),
            self._section("Síntomas", self._bullet_list(report.symptoms)),
            self._section("Root Cause", report.root_cause),
            self._section("Flujo de reproducción", self._ordered_list(report.reproduction_flow)),
            self._section("Riesgo arquitectónico", report.architectural_risk),
            self._section("Impacto en swarm", report.swarm_impact),
            self._section("Impacto en adaptación", report.adaptation_impact),
            self._section("Impacto en consenso", report.consensus_impact),
            self._section("Impacto en resiliencia", report.resilience_impact),
            self._section("Impacto en shared memory", report.shared_memory_impact),
            self._fix_section(report),
            self._tests_section(report),
            self._bullet_section("Observability recomendada", report.observability_recommendations),
            self._bullet_section("Regression prevention", report.regression_prevention),
            self._affected_files_section(report),
            self._trace_section(report),
            self._bullet_section("Lecciones aprendidas", report.lessons_learned),
        ]

        return "\n\n".join(sections) + "\n"

    # ── Section builders ──────────────────────────────────────

    def _header(self, report: BugReport, severity: str, category: str, status: str) -> str:
        lines = [
            "# Bug Report",
            "",
            "## Metadata",
            f"- **ID:** {report.bug_id}",
            f"- **Title:** {report.title}",
            f"- **Date:** {report.date}",
            f"- **Severity:** {severity.upper()}",
            f"- **Category:** {category}",
            f"- **Status:** {status.upper()}",
        ]
        if report.metadata.trace_id:
            lines.append(f"- **Trace ID:** `{report.metadata.trace_id}`")
        if report.metadata.correlation_id:
            lines.append(f"- **Correlation ID:** `{report.metadata.correlation_id}`")
        if report.metadata.anomaly_id:
            lines.append(f"- **Anomaly ID:** `{report.metadata.anomaly_id}`")
        if report.metadata.commit_hash:
            lines.append(f"- **Commit:** `{report.metadata.commit_hash}`")
        if report.metadata.environment:
            lines.append(f"- **Environment:** {report.metadata.environment}")
        return "\n".join(lines)

    def _section(self, title: str, body: str) -> str:
        if not body:
            return ""
        return f"## {title}\n\n{body}"

    def _bullet_list(self, items: list[str]) -> str:
        if not items:
            return ""
        return "\n".join(f"- {item}" for item in items)

    def _ordered_list(self, items: list[str]) -> str:
        if not items:
            return ""
        return "\n".join(f"{i+1}. {item}" for i, item in enumerate(items))

    def _bullet_section(self, title: str, items: list[str]) -> str:
        if not items:
            return ""
        return self._section(title, self._bullet_list(items))

    def _fix_section(self, report: BugReport) -> str:
        fix = report.fix
        parts = []
        if fix.strategy:
            parts.append(f"### Estrategia\n\n{fix.strategy}")
        if fix.description:
            parts.append(f"### Descripción\n\n{fix.description}")
        if fix.risks:
            parts.append(f"### Riesgos\n\n{fix.risks}")
        if fix.files_changed:
            rows = "\n".join(
                f"| {f.get('file', '')} | {f.get('lines', '')} | {f.get('change', '')} |"
                for f in fix.files_changed
            )
            header = "| Archivo | Líneas | Cambio |\n|--------|--------|--------|"
            parts.append(f"### Archivos modificados\n\n{header}\n{rows}")
        if not parts:
            return ""
        return "## Fix implementado\n\n" + "\n\n".join(parts)

    def _tests_section(self, report: BugReport) -> str:
        if not report.tests:
            return ""
        rows = "\n".join(
            f"| {t.name} | {t.type} | {t.status} | {t.description} |"
            for t in report.tests
        )
        header = "| Test | Tipo | Estado | Descripción |\n|------|------|--------|-------------|"
        return f"## Tests\n\n{header}\n{rows}"

    def _affected_files_section(self, report: BugReport) -> str:
        if not report.affected_files:
            return ""
        rows = "\n".join(
            f"| {f.get('file', '')} | {f.get('lines', '')} | {f.get('change', '')} |"
            for f in report.affected_files
        )
        header = "| Archivo | Líneas | Cambio |\n|--------|--------|--------|"
        return f"## Archivos afectados\n\n{header}\n{rows}"

    def _trace_section(self, report: BugReport) -> str:
        m = report.metadata
        has_trace = any([m.trace_id, m.correlation_id, m.span_id, m.causation_id, m.anomaly_id])
        if not has_trace:
            return ""
        lines = ["## Trace Correlation"]
        if m.trace_id:
            lines.append(f"- **Trace:** `{m.trace_id}`")
        if m.span_id:
            lines.append(f"- **Span:** `{m.span_id}`")
        if m.correlation_id:
            lines.append(f"- **Correlation:** `{m.correlation_id}`")
        if m.causation_id:
            lines.append(f"- **Causation:** `{m.causation_id}`")
        if m.anomaly_id:
            lines.append(f"- **Anomaly:** `{m.anomaly_id}`")
        return "\n".join(lines)

    # ── Bulk writer ───────────────────────────────────────────

    def write_all(self, reports: list[BugReport], base_dir: str) -> list[str]:
        """Write multiple reports, return list of file paths."""
        paths: list[str] = []
        for report in reports:
            cat_dir = report.category.value if hasattr(report.category, "value") else report.category
            target = os.path.join(base_dir, cat_dir)
            os.makedirs(target, exist_ok=True)
            paths.append(self.write(report, target))
        return paths
