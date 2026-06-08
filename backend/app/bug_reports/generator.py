"""
BugReportGenerator — Central service for creating, tracking, and
persisting bug reports across the distributed architecture.

Integrates with:
    - tracing.CorrelationEngine for trace/correlation IDs
    - swarm_diagnostics for anomaly-to-bug bridging
    - markdown_writer.BugReportMarkdownWriter for file output

Usage:
    generator = BugReportGenerator()
    report = generator.create(
        title="My bug",
        category=BugCategory.AUTH,
        severity=BugSeverity.CRITICAL,
        symptoms=["...", "..."],
        root_cause="...",
    )
    generator.write_markdown(report)
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from app.bug_reports.models import (
    BugCategory,
    BugReport,
    BugReportMetadata,
    BugSeverity,
    BugStatus,
)
from app.bug_reports.markdown_writer import BugReportMarkdownWriter

logger = logging.getLogger(__name__)

BUG_REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs",
    "bug_reports",
)


class BugReportGenerator:
    """Thread-safe singleton that manages the lifecycle of bug reports.

    Responsibility areas:
        - Generate sequential bug IDs (BUG-001, BUG-002, …)
        - Create BugReport instances with trace correlation
        - Persist to markdown files via BugReportMarkdownWriter
        - Load existing reports for status updates
        - Maintain an in-memory registry of known bugs
    """

    _instance: BugReportGenerator | None = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> BugReportGenerator:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self._bug_lock = threading.Lock()
        self._reports: dict[str, BugReport] = {}
        self._next_id: int = 1
        self._markdown_writer = BugReportMarkdownWriter()
        self._reports_dir = BUG_REPORTS_DIR
        self._ensure_dirs()
        self._load_existing()

    # ── Directory management ──────────────────────────────────

    def _ensure_dirs(self) -> None:
        os.makedirs(self._reports_dir, exist_ok=True)
        for cat in BugCategory:
            cat_dir = os.path.join(self._reports_dir, cat.value)
            os.makedirs(cat_dir, exist_ok=True)

    def _load_existing(self) -> None:
        """Scan docs/bug_reports/ for existing markdown files and
        register their IDs so we don't reuse them."""
        import re

        max_id = 0
        pattern = re.compile(r"BUG-(\d+)")
        for root, _dirs, files in os.walk(self._reports_dir):
            for fname in files:
                if not fname.endswith(".md"):
                    continue
                m = pattern.search(fname)
                if m:
                    num = int(m.group(1))
                    if num > max_id:
                        max_id = num
        if max_id > 0:
            self._next_id = max_id + 1
            logger.info("BugReportGenerator: next ID will be BUG-%03d", self._next_id)

    # ── ID generation ─────────────────────────────────────────

    def _generate_bug_id(self) -> str:
        with self._bug_lock:
            bid = f"BUG-{self._next_id:03d}"
            self._next_id += 1
            return bid

    # ── Trace correlation ─────────────────────────────────────

    def _capture_trace_context(self) -> dict[str, str | None]:
        """Attempt to pull the active PropagationContext from the
        tracing subsystem.  Returns whatever fields are available."""
        ctx: dict[str, str | None] = {
            "trace_id": None,
            "correlation_id": None,
            "span_id": None,
            "causation_id": None,
        }
        try:
            from app.tracing import correlation_engine

            prop = correlation_engine.get_current()
            if prop is not None:
                ctx["trace_id"] = prop.trace_id
                ctx["correlation_id"] = prop.correlation_id
                ctx["span_id"] = prop.span_id
                ctx["causation_id"] = prop.causation_id
        except ImportError:
            pass
        except Exception as exc:
            logger.debug("Failed to capture trace context: %s", exc)
        return ctx

    # ── Create report ─────────────────────────────────────────

    def create(
        self,
        *,
        title: str,
        category: BugCategory | str = BugCategory.BACKEND,
        severity: BugSeverity | str = BugSeverity.MEDIUM,
        symptoms: list[str] | None = None,
        root_cause: str = "",
        reproduction_flow: list[str] | None = None,
        architectural_risk: str = "",
        swarm_impact: str = "",
        adaptation_impact: str = "",
        consensus_impact: str = "",
        resilience_impact: str = "",
        shared_memory_impact: str = "",
        affected_files: list[dict[str, str]] | None = None,
        environment: str = "",
        anomaly_id: str | None = None,
    ) -> BugReport:
        """Create a new BugReport, auto-populating IDs and trace context."""

        bug_id = self._generate_bug_id()
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        trace = self._capture_trace_context()

        metadata = BugReportMetadata(
            bug_id=bug_id,
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            trace_id=trace["trace_id"],
            correlation_id=trace["correlation_id"],
            span_id=trace["span_id"],
            causation_id=trace["causation_id"],
            anomaly_id=anomaly_id,
            environment=environment,
        )

        report = BugReport(
            bug_id=bug_id,
            title=title,
            date=date_str,
            category=category,
            severity=severity,
            status=BugStatus.OPEN,
            symptoms=symptoms or [],
            root_cause=root_cause,
            reproduction_flow=reproduction_flow or [],
            architectural_risk=architectural_risk,
            swarm_impact=swarm_impact,
            adaptation_impact=adaptation_impact,
            consensus_impact=consensus_impact,
            resilience_impact=resilience_impact,
            shared_memory_impact=shared_memory_impact,
            affected_files=affected_files or [],
            metadata=metadata,
        )

        with self._bug_lock:
            self._reports[bug_id] = report

        logger.info(
            "Bug report created: %s | %s | %s",
            bug_id,
            title,
            severity.value if isinstance(severity, BugSeverity) else severity,
        )
        return report

    # ── Persist to markdown ───────────────────────────────────

    def write_markdown(self, report: BugReport) -> str:
        """Write the report as a markdown file under docs/bug_reports/
        and return the file path."""
        cat_dir = report.category.value if isinstance(report.category, BugCategory) else report.category
        target_dir = os.path.join(self._reports_dir, cat_dir)
        os.makedirs(target_dir, exist_ok=True)

        path = self._markdown_writer.write(report, target_dir)
        report.markdown_path = path
        logger.info("Bug report written: %s", path)
        return path

    # ── Read / Update ─────────────────────────────────────────

    def get(self, bug_id: str) -> BugReport | None:
        return self._reports.get(bug_id)

    def list_all(self, status: BugStatus | None = None) -> list[BugReport]:
        if status is None:
            return list(self._reports.values())
        return [r for r in self._reports.values() if r.status == status]

    def list_by_category(self, category: BugCategory | str) -> list[BugReport]:
        return [
            r
            for r in self._reports.values()
            if (r.category.value if isinstance(r.category, BugCategory) else r.category)
            == (category.value if isinstance(category, BugCategory) else category)
        ]

    def update_status(
        self,
        bug_id: str,
        new_status: BugStatus,
        commit_hash: str | None = None,
    ) -> BugReport | None:
        report = self.get(bug_id)
        if report is None:
            logger.warning("Bug report %s not found for status update", bug_id)
            return None

        if new_status == BugStatus.FIXED:
            report.mark_fixed(commit_hash)
        elif new_status == BugStatus.VERIFIED:
            report.mark_verified(commit_hash)
        elif new_status == BugStatus.REGRESSION:
            report.mark_regression(commit_hash)
        else:
            report.status = new_status
            report.metadata.updated_at = datetime.now(timezone.utc).isoformat()

        # Re-write markdown with updated status
        self.write_markdown(report)
        logger.info("Bug report %s → %s", bug_id, new_status.value if isinstance(new_status, BugStatus) else new_status)
        return report

    # ── Stats ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        counts: dict[str, int] = defaultdict(int)
        by_category: dict[str, int] = defaultdict(int)
        by_severity: dict[str, int] = defaultdict(int)

        for report in self._reports.values():
            cat = report.category.value if isinstance(report.category, BugCategory) else report.category
            sev = report.severity.value if isinstance(report.severity, BugSeverity) else report.severity
            status = report.status.value if isinstance(report.status, BugStatus) else report.status

            counts[status] += 1
            by_category[cat] += 1
            by_severity[sev] += 1

        return {
            "total": len(self._reports),
            "next_id": f"BUG-{self._next_id:03d}",
            "by_status": dict(counts),
            "by_category": dict(by_category),
            "by_severity": dict(by_severity),
        }
