"""
Bug Report Automation System for multiagent-llm-education.

Provides structured bug report generation, markdown output,
regression tracking, and integration with the existing tracing
and swarm diagnostics infrastructure.
"""

from app.bug_reports.models import (
    BugSeverity,
    BugCategory,
    BugStatus,
    BugReport,
    BugFix,
    BugTest,
    BugReportMetadata,
)
from app.bug_reports.generator import BugReportGenerator
from app.bug_reports.markdown_writer import BugReportMarkdownWriter
from app.bug_reports.regression import RegressionTracker
from app.bug_reports.diagnostics_integration import BugDiagnosticsBridge

__all__ = [
    "BugSeverity",
    "BugCategory",
    "BugStatus",
    "BugReport",
    "BugFix",
    "BugTest",
    "BugReportMetadata",
    "BugReportGenerator",
    "BugReportMarkdownWriter",
    "RegressionTracker",
    "BugDiagnosticsBridge",
]
