"""
RegressionTracker — Tracks bug regressions over time, linking them to
test results, commit history, and diagnostic anomaly signals.

A regression is a bug that was marked FIXED or VERIFIED but has
re-appeared (same symptoms, same root cause pattern).  The tracker
maintains a regression timeline and can cross-reference with the
swarm diagnostics engine for anomaly co-occurrence analysis.

Usage:
    tracker = RegressionTracker()
    tracker.register_regression("BUG-001", commit_hash="abc123",
                                test_failures=["test_login_rate_limit"])
    history = tracker.regression_history("BUG-001")
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.bug_reports.generator import BugReportGenerator
from app.bug_reports.models import BugStatus

logger = logging.getLogger(__name__)


@dataclass
class RegressionEvent:
    """A single regression occurrence for a given bug."""

    bug_id: str
    timestamp: str
    commit_hash: str | None = None
    test_failures: list[str] = field(default_factory=list)
    anomaly_ids: list[str] = field(default_factory=list)
    environment: str = ""
    details: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bug_id": self.bug_id,
            "timestamp": self.timestamp,
            "commit_hash": self.commit_hash,
            "test_failures": self.test_failures,
            "anomaly_ids": self.anomaly_ids,
            "environment": self.environment,
            "details": self.details,
            "evidence": self.evidence,
        }


class RegressionTracker:
    """Thread-safe tracker that records regression events and updates
    bug report status accordingly."""

    def __init__(self, generator: BugReportGenerator | None = None) -> None:
        self._lock = threading.Lock()
        self._regression_history: dict[str, list[RegressionEvent]] = defaultdict(list)
        self._generator = generator or BugReportGenerator()

    # ── Register regression ───────────────────────────────────

    def register_regression(
        self,
        bug_id: str,
        commit_hash: str | None = None,
        test_failures: list[str] | None = None,
        anomaly_ids: list[str] | None = None,
        environment: str = "",
        details: str = "",
        evidence: dict[str, Any] | None = None,
    ) -> RegressionEvent:
        """Record a regression event and update the bug report status."""
        event = RegressionEvent(
            bug_id=bug_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            commit_hash=commit_hash,
            test_failures=test_failures or [],
            anomaly_ids=anomaly_ids or [],
            environment=environment,
            details=details,
            evidence=evidence or {},
        )

        with self._lock:
            self._regression_history[bug_id].append(event)

        # Update the bug report status
        report = self._generator.get(bug_id)
        if report is not None:
            report.mark_regression(commit_hash)
            # Re-write markdown
            self._generator.write_markdown(report)
            logger.warning(
                "Regression registered: %s | commit=%s | %d test failures",
                bug_id,
                commit_hash,
                len(event.test_failures),
            )

        return event

    # ── Query ─────────────────────────────────────────────────

    def regression_history(self, bug_id: str) -> list[RegressionEvent]:
        """Return all regression events for a given bug, oldest first."""
        with self._lock:
            return list(self._regression_history.get(bug_id, []))

    def all_regressions(self) -> list[RegressionEvent]:
        """Return all recorded regression events across all bugs."""
        with self._lock:
            events: list[RegressionEvent] = []
            for ev_list in self._regression_history.values():
                events.extend(ev_list)
            return sorted(events, key=lambda e: e.timestamp)

    def regression_count(self, bug_id: str) -> int:
        """How many times has this bug regressed?"""
        return len(self._regression_history.get(bug_id, []))

    def bugs_with_regressions(self) -> list[str]:
        """Bug IDs that have regressed at least once."""
        with self._lock:
            return [bid for bid, evs in self._regression_history.items() if evs]

    def recent_regressions(self, limit: int = 10) -> list[RegressionEvent]:
        """Most recent regression events across all bugs."""
        all_events = self.all_regressions()
        return sorted(all_events, key=lambda e: e.timestamp, reverse=True)[:limit]

    # ── Link anomalies to regressions ─────────────────────────

    def link_anomaly(
        self,
        bug_id: str,
        anomaly_id: str,
        details: str = "",
    ) -> RegressionEvent | None:
        """Link a diagnostics anomaly signal to an existing bug regression.
        Creates a new regression event if none exists for this bug."""
        with self._lock:
            history = self._regression_history.get(bug_id, [])
            if history:
                latest = history[-1]
                latest.anomaly_ids.append(anomaly_id)
                if details:
                    latest.details = details
                return latest
        # No existing regression — register one
        return self.register_regression(
            bug_id=bug_id,
            anomaly_ids=[anomaly_id],
            details=details,
        )

    # ── Stats ─────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        all_events = self.all_regressions()
        return {
            "total_regressions": len(all_events),
            "unique_bugs_regressed": len(self.bugs_with_regressions()),
            "most_regressed": max(
                self.bugs_with_regressions(),
                key=lambda b: self.regression_count(b),
                default=None,
            ),
            "recent": [e.to_dict() for e in self.recent_regressions(5)],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "bugs_with_regressions": {
                bid: [e.to_dict() for e in evs]
                for bid, evs in self._regression_history.items()
            }
        }



