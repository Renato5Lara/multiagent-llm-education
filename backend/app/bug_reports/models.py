"""
Core data models for the Bug Report Automation System.

Defines:
    - BugSeverity (CRITICAL / HIGH / MEDIUM / LOW)
    - BugCategory (auth / frontend / backend / swarm / …)
    - BugStatus  (OPEN / FIXED / VERIFIED / REGRESSION)
    - BugReport  (full dataclass composing all fields)
    - BugFix     (fix implementation details)
    - BugTest    (linked test metadata)
    - BugReportMetadata (auto-generated fields: ID, timestamp, trace)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ═══════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════


class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugCategory(str, Enum):
    AUTH = "auth"
    FRONTEND = "frontend"
    BACKEND = "backend"
    SWARM = "swarm"
    PROPAGATION = "propagation"
    RUNTIME = "runtime"
    DATABASE = "database"
    OBSERVABILITY = "observability"


class BugStatus(str, Enum):
    OPEN = "open"
    FIXED = "fixed"
    VERIFIED = "verified"
    REGRESSION = "regression"


# ═══════════════════════════════════════════════════════════════
# Supporting dataclasses
# ═══════════════════════════════════════════════════════════════


@dataclass
class BugFix:
    description: str = ""
    files_changed: list[dict[str, Any]] = field(default_factory=list)
    strategy: str = ""
    risks: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "files_changed": self.files_changed,
            "strategy": self.strategy,
            "risks": self.risks,
        }


@dataclass
class BugTest:
    name: str = ""
    type: str = "unit"  # unit | integration | e2e | property
    file_path: str = ""
    status: str = "pending"  # pending | passing | failing
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.type,
            "file_path": self.file_path,
            "status": self.status,
            "description": self.description,
        }


@dataclass
class BugReportMetadata:
    bug_id: str = ""
    created_at: str = ""
    updated_at: str = ""
    trace_id: str | None = None
    correlation_id: str | None = None
    span_id: str | None = None
    causation_id: str | None = None
    anomaly_id: str | None = None
    commit_hash: str | None = None
    environment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "span_id": self.span_id,
            "causation_id": self.causation_id,
            "anomaly_id": self.anomaly_id,
            "commit_hash": self.commit_hash,
            "environment": self.environment,
        }


# ═══════════════════════════════════════════════════════════════
# Main BugReport dataclass
# ═══════════════════════════════════════════════════════════════


@dataclass
class BugReport:
    # ── Identifiers ────────────────────────────────────────────
    bug_id: str = ""
    title: str = ""
    date: str = ""
    category: BugCategory | str = BugCategory.BACKEND
    severity: BugSeverity | str = BugSeverity.MEDIUM
    status: BugStatus | str = BugStatus.OPEN

    # ── Symptoms & cause ──────────────────────────────────────
    symptoms: list[str] = field(default_factory=list)
    root_cause: str = ""
    reproduction_flow: list[str] = field(default_factory=list)

    # ── Architectural impact ──────────────────────────────────
    architectural_risk: str = ""
    swarm_impact: str = ""
    adaptation_impact: str = ""
    consensus_impact: str = ""
    resilience_impact: str = ""
    shared_memory_impact: str = ""

    # ── Fix details ───────────────────────────────────────────
    fix: BugFix = field(default_factory=BugFix)

    # ── Tests ─────────────────────────────────────────────────
    tests: list[BugTest] = field(default_factory=list)

    # ── Observability ─────────────────────────────────────────
    observability_recommendations: list[str] = field(default_factory=list)
    regression_prevention: list[str] = field(default_factory=list)

    # ── Trace correlation ─────────────────────────────────────
    metadata: BugReportMetadata = field(default_factory=BugReportMetadata)

    # ── File tracking ─────────────────────────────────────────
    affected_files: list[dict[str, str]] = field(default_factory=list)
    markdown_path: str = ""

    # ── Lessons ───────────────────────────────────────────────
    lessons_learned: list[str] = field(default_factory=list)

    # ────────────────────────────────────────────────────────────

    @property
    def is_regression(self) -> bool:
        return self.status == BugStatus.REGRESSION

    @property
    def is_open(self) -> bool:
        return self.status == BugStatus.OPEN

    @property
    def filename_slug(self) -> str:
        date_part = self.date.replace(" ", "T") if self.date else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        safe_title = self.title.lower().replace(" ", "_").replace("/", "_")[:60]
        return f"{date_part}_{self.bug_id}_{safe_title}"

    def mark_regression(self, commit_hash: str | None = None) -> None:
        self.status = BugStatus.REGRESSION
        self.metadata.updated_at = datetime.now(timezone.utc).isoformat()
        if commit_hash:
            self.metadata.commit_hash = commit_hash

    def mark_fixed(self, commit_hash: str | None = None) -> None:
        self.status = BugStatus.FIXED
        self.metadata.updated_at = datetime.now(timezone.utc).isoformat()
        if commit_hash:
            self.metadata.commit_hash = commit_hash

    def mark_verified(self, commit_hash: str | None = None) -> None:
        self.status = BugStatus.VERIFIED
        self.metadata.updated_at = datetime.now(timezone.utc).isoformat()
        if commit_hash:
            self.metadata.commit_hash = commit_hash

    def add_test(self, test: BugTest) -> None:
        self.tests.append(test)

    def add_lesson(self, lesson: str) -> None:
        self.lessons_learned.append(lesson)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "title": self.title,
            "date": self.date,
            "category": self.category.value if isinstance(self.category, BugCategory) else self.category,
            "severity": self.severity.value if isinstance(self.severity, BugSeverity) else self.severity,
            "status": self.status.value if isinstance(self.status, BugStatus) else self.status,
            "symptoms": self.symptoms,
            "root_cause": self.root_cause,
            "reproduction_flow": self.reproduction_flow,
            "architectural_risk": self.architectural_risk,
            "swarm_impact": self.swarm_impact,
            "adaptation_impact": self.adaptation_impact,
            "consensus_impact": self.consensus_impact,
            "resilience_impact": self.resilience_impact,
            "shared_memory_impact": self.shared_memory_impact,
            "fix": self.fix.to_dict(),
            "tests": [t.to_dict() for t in self.tests],
            "observability_recommendations": self.observability_recommendations,
            "regression_prevention": self.regression_prevention,
            "metadata": self.metadata.to_dict(),
            "affected_files": self.affected_files,
            "markdown_path": self.markdown_path,
            "lessons_learned": self.lessons_learned,
        }
