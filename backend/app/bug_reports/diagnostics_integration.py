"""
BugDiagnosticsBridge — Bi-directional integration between the bug report
automation system and the existing swarm diagnostics / tracing infrastructure.

Capabilities:
    1. Listen for AnomalySignals from SwarmDiagnosticsEngine and auto-create
       bug reports when severity is CRITICAL or WARNING.
    2. Emit DiagnosticEvents when a bug report is created / updated so that
       the diagnostics pipeline is aware of known bugs.
    3. Cross-reference anomaly signals with existing bug reports to detect
       regressions automatically.
    4. Propagate trace context (trace_id, correlation_id, causation_id)
       into every bug report for full distributed tracing correlation.

Usage:
    bridge = BugDiagnosticsBridge()
    bridge.auto_report_from_anomaly(anomaly_signal)
    bridge.emit_diagnostic_event(report, event_type="bug:created")
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.bug_reports.generator import BugReportGenerator
from app.bug_reports.models import BugCategory, BugReport, BugSeverity, BugStatus
from app.bug_reports.regression import RegressionTracker

logger = logging.getLogger(__name__)

# Severity mapping: swarm_diagnostics Severity → bug_reports BugSeverity
_SEVERITY_MAP: dict[str, BugSeverity] = {
    "critical": BugSeverity.CRITICAL,
    "warning": BugSeverity.HIGH,
    "info": BugSeverity.LOW,
}

# AnomalyType → BugCategory mapping (heuristic)
_CATEGORY_MAP: dict[str, BugCategory] = {
    "propagation_failure": BugCategory.PROPAGATION,
    "propagation_storm": BugCategory.PROPAGATION,
    "consensus_conflict": BugCategory.SWARM,
    "hung_consensus": BugCategory.SWARM,
    "cascading_delay": BugCategory.SWARM,
    "quorum_instability": BugCategory.SWARM,
    "delegation_loop": BugCategory.SWARM,
    "retry_storm": BugCategory.RUNTIME,
    "deadlock": BugCategory.RUNTIME,
    "stale_memory": BugCategory.OBSERVABILITY,
    "agent_divergence": BugCategory.SWARM,
    "event_storm": BugCategory.OBSERVABILITY,
    "sync_delay": BugCategory.RUNTIME,
    "trust_decay": BugCategory.SWARM,
    "memory_fragmentation": BugCategory.OBSERVABILITY,
    "circuit_breaker_open": BugCategory.RUNTIME,
    "cascading_failure": BugCategory.RUNTIME,
    "recovery_instability": BugCategory.RUNTIME,
    "degraded_agent": BugCategory.SWARM,
    "hallucination": BugCategory.SWARM,
    "slow_agent": BugCategory.SWARM,
    "cognitive_drift": BugCategory.SWARM,
    "decision_flipping": BugCategory.SWARM,
}


class BugDiagnosticsBridge:
    """Bi-directional bridge between diagnostics and bug reports.

    Thread-safe (delegates to BugReportGenerator's internal lock).
    """

    def __init__(
        self,
        generator: BugReportGenerator | None = None,
        regression_tracker: RegressionTracker | None = None,
    ) -> None:
        self._generator = generator or BugReportGenerator()
        self._regression_tracker = regression_tracker or RegressionTracker(generator=self._generator)

    # ── Anomaly → BugReport ───────────────────────────────────

    def auto_report_from_anomaly(
        self,
        anomaly: Any,
        environment: str = "",
    ) -> BugReport | None:
        """Create a bug report from a swarm_diagnostics AnomalySignal.

        Only auto-creates for CRITICAL and WARNING severity.
        Returns None if severity is too low for auto-reporting.
        """
        sev_name = anomaly.severity.value if hasattr(anomaly.severity, "value") else str(anomaly.severity)
        bug_severity = _SEVERITY_MAP.get(sev_name, BugSeverity.LOW)

        if bug_severity == BugSeverity.LOW:
            return None  # Don't auto-create for INFO / LOW

        anomaly_type = anomaly.anomaly_type.value if hasattr(anomaly.anomaly_type, "value") else str(anomaly.anomaly_type)
        category = _CATEGORY_MAP.get(anomaly_type, BugCategory.OBSERVABILITY)

        # Check if this anomaly matches an existing open report to avoid duplicates
        existing = self._find_matching_anomaly(anomaly)
        if existing is not None:
            logger.debug("Anomaly %s matches existing bug %s, skipping auto-report", anomaly.anomaly_id, existing.bug_id)
            return existing

        scope = getattr(anomaly, "scope", "global")
        title = f"[Auto] {anomaly.title} ({scope})"
        description = getattr(anomaly, "description", "")
        metric_value = getattr(anomaly, "metric_value", None)
        threshold = getattr(anomaly, "threshold", None)
        evidence = getattr(anomaly, "evidence", {})
        recommendation = getattr(anomaly, "recommendation", "")

        symptoms = [description] if description else [f"Anomaly detected: {anomaly_type}"]
        if metric_value is not None and threshold is not None:
            symptoms.append(f"Metric {metric_value:.2f} exceeds threshold {threshold:.2f}")

        report = self._generator.create(
            title=title,
            category=category,
            severity=bug_severity,
            symptoms=symptoms,
            root_cause=f"Auto-detected by diagnostics detector: {getattr(anomaly, 'detector_name', 'unknown')}",
            architectural_risk=recommendation,
            swarm_impact=f"Anomaly type: {anomaly_type}" if anomaly_type else "",
            affected_files=[],
            environment=environment,
            anomaly_id=getattr(anomaly, "anomaly_id", None),
        )

        # Emit a diagnostic event for this new bug report
        self.emit_diagnostic_event(report, event_type="bug:auto_created")

        # Write to markdown
        self._generator.write_markdown(report)

        logger.info(
            "Auto-created bug report %s from anomaly %s (%s)",
            report.bug_id,
            getattr(anomaly, "anomaly_id", "?"),
            anomaly_type,
        )
        return report

    def _find_matching_anomaly(self, anomaly: Any) -> BugReport | None:
        """Check if an existing OPEN bug report already covers this anomaly."""
        anomaly_id = getattr(anomaly, "anomaly_id", None)
        title = getattr(anomaly, "title", "")
        for report in self._generator.list_all(status=BugStatus.OPEN):
            if report.metadata.anomaly_id == anomaly_id:
                return report
            if title and title in report.title:
                return report
        return None

    # ── BugReport → DiagnosticEvent ───────────────────────────

    def emit_diagnostic_event(
        self,
        report: BugReport,
        event_type: str = "bug:created",
    ) -> Any | None:
        """Emit a DiagnosticEvent to the swarm diagnostics engine.

        This makes bug lifecycle visible to the diagnostics pipeline
        (detectors, health snapshots, dashboards).

        Returns the DiagnosticEvent if emitted, None if engine unavailable.
        """
        try:
            from app.swarm_diagnostics import diagnostics_engine
            from app.swarm_diagnostics.models import DiagnosticEvent

            sev = report.severity.value if hasattr(report.severity, "value") else report.severity
            event = DiagnosticEvent(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                correlation_id=report.metadata.correlation_id,
                causation_id=report.metadata.causation_id,
                trace_id=report.metadata.trace_id,
                scope="bug_reports",
                source="BugDiagnosticsBridge",
                payload={
                    "bug_id": report.bug_id,
                    "title": report.title,
                    "severity": sev,
                    "category": report.category.value if hasattr(report.category, "value") else report.category,
                    "status": report.status.value if hasattr(report.status, "value") else report.status,
                },
            )
            diagnostics_engine.record_event(event)
            logger.debug("Emitted %s for %s", event_type, report.bug_id)
            return event
        except ImportError:
            logger.debug("swarm_diagnostics not available, skipping event emission")
            return None
        except Exception as exc:
            logger.warning("Failed to emit diagnostic event for %s: %s", report.bug_id, exc)
            return None

    # ── Regression detection from anomalies ───────────────────

    def check_regression_from_anomaly(
        self,
        anomaly: Any,
        environment: str = "",
    ) -> bool:
        """Check if an anomaly signals a regression of a known bug.

        Returns True if a regression was registered.
        """
        anomaly_id = getattr(anomaly, "anomaly_id", None)
        title = getattr(anomaly, "title", "")
        desc = getattr(anomaly, "description", "")

        # Look for FIXED/VERIFIED bugs that match this anomaly
        for status in (BugStatus.FIXED, BugStatus.VERIFIED):
            for report in self._generator.list_all(status=status):
                # Match by title similarity or symptom overlap
                if self._matches_regression_pattern(report, title, desc):
                    self._regression_tracker.register_regression(
                        bug_id=report.bug_id,
                        anomaly_ids=[anomaly_id] if anomaly_id else [],
                        details=f"Auto-detected regression via anomaly: {title}",
                        environment=environment,
                    )
                    logger.warning(
                        "Auto-detected regression: %s matches anomaly %s",
                        report.bug_id,
                        anomaly_id or title,
                    )
                    return True
        return False

    def _matches_regression_pattern(self, report: BugReport, anomaly_title: str, anomaly_desc: str) -> bool:
        """Heuristic match between a bug report and an anomaly signal.

        Checks title overlap in BOTH directions so that:
            report.title = "Propagation failure in event chain"
            anomaly.title = "Propagation failure detected"
        still matches because "Propagation failure" is common to both.
        """
        words_report = set(report.title.lower().split())
        words_anomaly = set(anomaly_title.lower().split()) if anomaly_title else set()
        shared = words_report & words_anomaly
        if len(shared) >= 2:
            return True

        if anomaly_title and anomaly_title in report.title:
            return True
        if report.title and report.title in anomaly_title:
            return True
        if anomaly_title and any(anomaly_title in s for s in report.symptoms):
            return True
        if anomaly_desc:
            for symptom in report.symptoms:
                if any(word in anomaly_desc.lower() for word in symptom.lower().split()[:3]):
                    return True
        return False

    # ── Process batch from diagnostics engine ─────────────────

    def process_anomalies_batch(
        self,
        anomalies: list[Any],
        environment: str = "",
    ) -> dict[str, list[str]]:
        """Process a batch of anomalies: auto-create reports and check
        for regressions.

        Returns:
            {"created": [bug_id, ...], "regressions": [bug_id, ...]}
        """
        result: dict[str, list[str]] = {"created": [], "regressions": []}

        for anomaly in anomalies:
            # Check regression first (more important)
            if self.check_regression_from_anomaly(anomaly, environment=environment):
                result["regressions"].append(
                    getattr(anomaly, "anomaly_id", "?")
                )
            # Auto-create report
            report = self.auto_report_from_anomaly(anomaly, environment=environment)
            if report is not None:
                result["created"].append(report.bug_id)

        return result
