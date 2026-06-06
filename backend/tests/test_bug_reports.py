"""
Tests for the Bug Report Automation System.

Covers:
    - Model creation and serialization
    - Enum values and conversions
    - Bug ID generation
    - Markdown writing
    - BugReportGenerator lifecycle
    - Regression tracking
    - Diagnostics bridge (with mocked diagnostics)
"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone

import pytest

from app.bug_reports.models import (
    BugCategory,
    BugFix,
    BugReport,
    BugReportMetadata,
    BugSeverity,
    BugStatus,
    BugTest,
)
from app.bug_reports.generator import BugReportGenerator
from app.bug_reports.markdown_writer import BugReportMarkdownWriter
from app.bug_reports.regression import RegressionEvent, RegressionTracker


# ═══════════════════════════════════════════════════════════════
# Model Tests
# ═══════════════════════════════════════════════════════════════


class TestEnums:
    def test_bug_severity_values(self):
        assert BugSeverity.CRITICAL.value == "critical"
        assert BugSeverity.HIGH.value == "high"
        assert BugSeverity.MEDIUM.value == "medium"
        assert BugSeverity.LOW.value == "low"

    def test_bug_category_values(self):
        assert BugCategory.AUTH.value == "auth"
        assert BugCategory.FRONTEND.value == "frontend"
        assert BugCategory.BACKEND.value == "backend"
        assert BugCategory.SWARM.value == "swarm"
        assert BugCategory.PROPAGATION.value == "propagation"
        assert BugCategory.RUNTIME.value == "runtime"
        assert BugCategory.DATABASE.value == "database"
        assert BugCategory.OBSERVABILITY.value == "observability"

    def test_bug_status_values(self):
        assert BugStatus.OPEN.value == "open"
        assert BugStatus.FIXED.value == "fixed"
        assert BugStatus.VERIFIED.value == "verified"
        assert BugStatus.REGRESSION.value == "regression"


class TestBugReport:
    def test_minimal_creation(self):
        report = BugReport(bug_id="BUG-001", title="Test bug")
        assert report.bug_id == "BUG-001"
        assert report.title == "Test bug"
        assert report.status == BugStatus.OPEN
        assert report.symptoms == []
        assert report.tests == []

    def test_to_dict(self):
        report = BugReport(
            bug_id="BUG-001",
            title="Test bug",
            severity=BugSeverity.CRITICAL,
            category=BugCategory.AUTH,
        )
        d = report.to_dict()
        assert d["bug_id"] == "BUG-001"
        assert d["severity"] == "critical"
        assert d["category"] == "auth"

    def test_filename_slug(self):
        report = BugReport(
            bug_id="BUG-001",
            title="Rate Limiter Bug",
            date="2026-05-27",
        )
        slug = report.filename_slug
        assert "BUG-001" in slug
        assert "rate_limiter_bug" in slug

    def test_mark_regression(self):
        report = BugReport(bug_id="BUG-001", title="Test")
        assert report.is_open is True
        report.mark_regression(commit_hash="abc123")
        assert report.is_regression is True
        assert report.metadata.commit_hash == "abc123"

    def test_mark_fixed(self):
        report = BugReport(bug_id="BUG-001", title="Test")
        report.mark_fixed()
        assert report.status == BugStatus.FIXED

    def test_mark_verified(self):
        report = BugReport(bug_id="BUG-001", title="Test")
        report.mark_verified()
        assert report.status == BugStatus.VERIFIED

    def test_add_test(self):
        report = BugReport(bug_id="BUG-001", title="Test")
        test = BugTest(name="test_login", type="integration")
        report.add_test(test)
        assert len(report.tests) == 1
        assert report.tests[0].name == "test_login"

    def test_add_lesson(self):
        report = BugReport(bug_id="BUG-001", title="Test")
        report.add_lesson("Always check rate limiters")
        assert "Always check rate limiters" in report.lessons_learned


class TestBugFix:
    def test_to_dict(self):
        fix = BugFix(
            description="Fixed the thing",
            strategy="Refactor X",
            risks="Minor perf impact",
            files_changed=[{"file": "app/main.py", "lines": "10-20", "change": "modified"}],
        )
        d = fix.to_dict()
        assert d["description"] == "Fixed the thing"
        assert len(d["files_changed"]) == 1


class TestBugTest:
    def test_to_dict(self):
        t = BugTest(name="test_login", type="integration", status="passing")
        d = t.to_dict()
        assert d["name"] == "test_login"
        assert d["status"] == "passing"


class TestBugReportMetadata:
    def test_to_dict(self):
        m = BugReportMetadata(
            bug_id="BUG-001",
            created_at="2026-05-27T00:00:00",
            trace_id="abc123",
        )
        d = m.to_dict()
        assert d["trace_id"] == "abc123"
        assert d["bug_id"] == "BUG-001"


# ═══════════════════════════════════════════════════════════════
# Generator Tests
# ═══════════════════════════════════════════════════════════════


class TestBugReportGenerator:
    def test_singleton(self):
        g1 = BugReportGenerator()
        g2 = BugReportGenerator()
        assert g1 is g2

    def test_generate_bug_id_increment(self):
        g = BugReportGenerator()
        # Force a clean sequence for the test
        g._next_id = 1
        id1 = g._generate_bug_id()
        id2 = g._generate_bug_id()
        assert id1 == "BUG-001"
        assert id2 == "BUG-002"

    def test_create_minimal(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        report = g.create(title="Test bug", category=BugCategory.AUTH, severity=BugSeverity.HIGH)
        assert report.bug_id == "BUG-001"
        assert report.title == "Test bug"
        assert report.status == BugStatus.OPEN
        assert report.date == datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def test_create_with_all_fields(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        report = g.create(
            title="Full test bug",
            category=BugCategory.SWARM,
            severity=BugSeverity.CRITICAL,
            symptoms=["System crashes", "High latency"],
            root_cause="Deadlock in consensus",
            reproduction_flow=["Start swarm", "Trigger consensus", "Observe deadlock"],
            architectural_risk="Single point of failure",
            swarm_impact="Swarm hangs",
            affected_files=[{"file": "app/swarm/consensus.py", "lines": "50-60", "change": "modified"}],
            environment="staging",
        )
        assert report.bug_id == "BUG-001"
        assert len(report.symptoms) == 2
        assert report.root_cause == "Deadlock in consensus"

    def test_get_report(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        report = g.create(title="Retrievable bug")
        fetched = g.get(report.bug_id)
        assert fetched is not None
        assert fetched.bug_id == report.bug_id

    def test_list_all(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        g.create(title="Bug 1")
        g.create(title="Bug 2")
        assert len(g.list_all()) == 2

    def test_list_by_category(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        g.create(title="Auth bug", category=BugCategory.AUTH)
        g.create(title="Swarm bug", category=BugCategory.SWARM)
        auth_bugs = g.list_by_category(BugCategory.AUTH)
        assert len(auth_bugs) == 1
        assert auth_bugs[0].title == "Auth bug"

    def test_update_status(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        report = g.create(title="Status test")
        g.update_status(report.bug_id, BugStatus.FIXED, commit_hash="def456")
        updated = g.get(report.bug_id)
        assert updated is not None
        assert updated.status == BugStatus.FIXED
        assert updated.metadata.commit_hash == "def456"
        # Cleanup
        if report.markdown_path and os.path.exists(report.markdown_path):
            os.remove(report.markdown_path)

    def test_update_status_nonexistent(self):
        g = BugReportGenerator()
        result = g.update_status("BUG-999", BugStatus.FIXED)
        assert result is None

    def test_stats(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        g.create(title="Bug 1", severity=BugSeverity.CRITICAL, category=BugCategory.AUTH)
        g.create(title="Bug 2", severity=BugSeverity.HIGH, category=BugCategory.SWARM)
        s = g.stats()
        assert s["total"] == 2

    def test_capture_trace_context_no_tracing(self):
        g = BugReportGenerator()
        ctx = g._capture_trace_context()
        # Should not crash when tracing is unavailable
        assert isinstance(ctx, dict)

    def test_markdown_output(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        report = g.create(title="Markdown test", category=BugCategory.BACKEND)
        with tempfile.TemporaryDirectory() as tmpdir:
            cat_dir = os.path.join(tmpdir, "backend")
            os.makedirs(cat_dir, exist_ok=True)
            writer = BugReportMarkdownWriter()
            path = writer.write(report, cat_dir)
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()
            assert "# Bug Report" in content
            assert report.bug_id in content
            assert "Markdown test" in content


# ═══════════════════════════════════════════════════════════════
# Markdown Writer Tests
# ═══════════════════════════════════════════════════════════════


class TestBugReportMarkdownWriter:
    def test_write_file(self):
        writer = BugReportMarkdownWriter()
        report = BugReport(
            bug_id="BUG-001",
            title="Write test",
            date="2026-05-27",
            severity=BugSeverity.CRITICAL,
            category=BugCategory.AUTH,
            symptoms=["Symptom 1", "Symptom 2"],
            root_cause="Root cause text",
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            assert os.path.exists(path)
            assert path.endswith(".md")
            with open(path) as f:
                content = f.read()
            assert "BUG-001" in content
            assert "Symptom 1" in content
            assert "Root cause text" in content

    def test_write_empty_sections(self):
        writer = BugReportMarkdownWriter()
        report = BugReport(bug_id="BUG-002", title="Minimal")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            assert os.path.exists(path)

    def test_write_with_fix(self):
        writer = BugReportMarkdownWriter()
        fix = BugFix(
            strategy="Refactor",
            description="Reimplemented the module",
            files_changed=[{"file": "app/core.py", "lines": "1-50", "change": "rewritten"}],
        )
        report = BugReport(bug_id="BUG-003", title="Fix test", fix=fix)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            with open(path) as f:
                content = f.read()
            assert "Refactor" in content
            assert "app/core.py" in content

    def test_write_with_tests(self):
        writer = BugReportMarkdownWriter()
        test = BugTest(name="test_fix", type="unit", status="passing", description="Validates fix")
        report = BugReport(bug_id="BUG-004", title="Test section")
        report.add_test(test)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            with open(path) as f:
                content = f.read()
            assert "test_fix" in content
            assert "passing" in content

    def test_write_with_trace(self):
        writer = BugReportMarkdownWriter()
        meta = BugReportMetadata(
            bug_id="BUG-005",
            trace_id="trace123",
            correlation_id="corr456",
            span_id="span789",
        )
        report = BugReport(bug_id="BUG-005", title="Trace test", metadata=meta)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            with open(path) as f:
                content = f.read()
            assert "Trace Correlation" in content
            assert "trace123" in content
            assert "corr456" in content

    def test_write_all(self):
        writer = BugReportMarkdownWriter()
        reports = [
            BugReport(bug_id="BUG-A1", title="Bug A", category=BugCategory.AUTH),
            BugReport(bug_id="BUG-B1", title="Bug B", category=BugCategory.SWARM),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            paths = writer.write_all(reports, tmpdir)
            assert len(paths) == 2
            for p in paths:
                assert os.path.exists(p)

    def test_lessons_section(self):
        writer = BugReportMarkdownWriter()
        report = BugReport(bug_id="BUG-006", title="Lessons test")
        report.add_lesson("Lesson 1: always test")
        report.add_lesson("Lesson 2: monitor everything")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = writer.write(report, tmpdir)
            with open(path) as f:
                content = f.read()
            assert "Lecciones aprendidas" in content
            assert "Lesson 1" in content


# ═══════════════════════════════════════════════════════════════
# Regression Tracker Tests
# ═══════════════════════════════════════════════════════════════


class TestRegressionTracker:
    def _setup(self):
        tracker = RegressionTracker()
        gen = tracker._generator
        gen._reports.clear()
        gen._next_id = 1
        return tracker, gen

    def test_register_regression(self):
        tracker, gen = self._setup()
        report = gen.create(title="Regression test bug")
        event = tracker.register_regression(
            report.bug_id,
            commit_hash="abc123",
            test_failures=["test_login"],
        )
        assert event.bug_id == report.bug_id
        assert event.commit_hash == "abc123"
        assert "test_login" in event.test_failures

        # Bug report status should be updated
        updated = gen.get(report.bug_id)
        assert updated is not None
        assert updated.is_regression

    def test_regression_history(self):
        tracker, gen = self._setup()
        report = gen.create(title="History test")
        tracker.register_regression(report.bug_id, commit_hash="abc")
        tracker.register_regression(report.bug_id, commit_hash="def")
        history = tracker.regression_history(report.bug_id)
        assert len(history) == 2
        assert history[0].commit_hash == "abc"
        assert history[1].commit_hash == "def"

    def test_regression_count(self):
        tracker, gen = self._setup()
        report = gen.create(title="Count test")
        assert tracker.regression_count(report.bug_id) == 0
        tracker.register_regression(report.bug_id)
        assert tracker.regression_count(report.bug_id) == 1

    def test_bugs_with_regressions(self):
        tracker, gen = self._setup()
        r1 = gen.create(title="Bug 1")
        r2 = gen.create(title="Bug 2")
        tracker.register_regression(r1.bug_id)
        tracker.register_regression(r2.bug_id)
        bugs = tracker.bugs_with_regressions()
        assert r1.bug_id in bugs
        assert r2.bug_id in bugs

    def test_recent_regressions(self):
        tracker, gen = self._setup()
        r1 = gen.create(title="Bug A")
        r2 = gen.create(title="Bug B")
        tracker.register_regression(r1.bug_id)
        tracker.register_regression(r2.bug_id)
        recent = tracker.recent_regressions(limit=1)
        assert len(recent) == 1

    def test_link_anomaly(self):
        tracker, gen = self._setup()
        report = gen.create(title="Anomaly link test")
        tracker.register_regression(report.bug_id)
        result = tracker.link_anomaly(report.bug_id, anomaly_id="anomaly-001")
        assert result is not None
        assert "anomaly-001" in result.anomaly_ids

    def test_link_anomaly_no_regression(self):
        tracker, gen = self._setup()
        report = gen.create(title="No prior regression")
        result = tracker.link_anomaly(report.bug_id, anomaly_id="anomaly-002")
        # Should auto-create a regression event
        assert result is not None
        assert tracker.regression_count(report.bug_id) >= 1

    def test_stats(self):
        tracker, gen = self._setup()
        r1 = gen.create(title="Bug X")
        r2 = gen.create(title="Bug Y")
        tracker.register_regression(r1.bug_id)
        tracker.register_regression(r2.bug_id)
        tracker.register_regression(r1.bug_id)  # second regression
        s = tracker.stats()
        assert s["total_regressions"] == 3
        assert s["unique_bugs_regressed"] == 2


# ═══════════════════════════════════════════════════════════════
# Diagnostics Bridge Tests (with mocks)
# ═══════════════════════════════════════════════════════════════


class MockAnomalySignal:
    """Simulates swarm_diagnostics AnomalySignal for testing."""

    def __init__(
        self,
        anomaly_id: str = "anomaly-001",
        title: str = "Propagation failure detected",
        description: str = "Event chain exceeded max depth",
        severity: str = "critical",
        anomaly_type: str = "propagation_failure",
        detector_name: str = "PropagationFailureDetector",
        scope: str = "student:test-001",
        metric_value: float = 15.0,
        threshold: float = 10.0,
        recommendation: str = "Check event chain depth",
        evidence: dict | None = None,
    ):
        self.anomaly_id = anomaly_id
        self.title = title
        self.description = description
        self.severity = MockEnum(severity)
        self.anomaly_type = MockEnum(anomaly_type)
        self.detector_name = detector_name
        self.scope = scope
        self.metric_value = metric_value
        self.threshold = threshold
        self.recommendation = recommendation
        self.evidence = evidence or {}


class MockEnum:
    def __init__(self, value: str):
        self.value = value


class TestBugDiagnosticsBridge:
    def _setup(self):
        from app.bug_reports.diagnostics_integration import BugDiagnosticsBridge

        bridge = BugDiagnosticsBridge()
        gen = bridge._generator
        gen._reports.clear()
        gen._next_id = 1
        return bridge, gen

    def test_auto_report_critical_anomaly(self):
        bridge, _gen = self._setup()
        anomaly = MockAnomalySignal(
            anomaly_id="anom-001",
            title="Critical failure",
            severity="critical",
            anomaly_type="propagation_failure",
        )
        report = bridge.auto_report_from_anomaly(anomaly)
        assert report is not None
        assert report.bug_id == "BUG-001"
        assert report.severity == BugSeverity.CRITICAL
        assert report.category == BugCategory.PROPAGATION
        assert "Critical failure" in report.title

    def test_auto_report_warning_anomaly(self):
        bridge, _gen = self._setup()
        anomaly = MockAnomalySignal(
            anomaly_id="anom-002",
            title="Warning signal",
            severity="warning",
            anomaly_type="consensus_conflict",
        )
        report = bridge.auto_report_from_anomaly(anomaly)
        assert report is not None
        assert report.severity == BugSeverity.HIGH
        assert report.category == BugCategory.SWARM

    def test_auto_report_info_anomaly_skipped(self):
        bridge, _gen = self._setup()
        anomaly = MockAnomalySignal(
            anomaly_id="anom-003",
            title="Info signal",
            severity="info",
        )
        report = bridge.auto_report_from_anomaly(anomaly)
        assert report is None  # Info anomalies should not auto-create

    def test_detect_regression_from_anomaly(self):
        bridge, gen = self._setup()

        # Create a FIXED bug that matches the anomaly
        report = gen.create(title="Propagation failure in event chain")
        gen.update_status(report.bug_id, BugStatus.FIXED)

        anomaly = MockAnomalySignal(
            anomaly_id="anom-004",
            title="Propagation failure detected",
            severity="critical",
        )
        detected = bridge.check_regression_from_anomaly(anomaly)
        assert detected is True

        # Regression should be registered
        regressions = bridge._regression_tracker.regression_history(report.bug_id)
        assert len(regressions) >= 1

    def test_no_false_positive_regression(self):
        bridge, gen = self._setup()

        # Create a FIXED bug with unrelated title
        r = gen.create(title="Database connection timeout")
        gen.update_status(r.bug_id, BugStatus.FIXED)

        anomaly = MockAnomalySignal(
            anomaly_id="anom-005",
            title="Swarm consensus conflict",
            severity="critical",
            anomaly_type="consensus_conflict",
        )
        detected = bridge.check_regression_from_anomaly(anomaly)
        assert detected is False

    def test_process_anomalies_batch(self):
        bridge, _gen = self._setup()

        # One critical anomaly that should auto-create
        anomalies = [
            MockAnomalySignal(anomaly_id="batch-001", title="Critical event storm", severity="critical", anomaly_type="event_storm"),
            MockAnomalySignal(anomaly_id="batch-002", title="Info signal", severity="info"),
        ]

        result = bridge.process_anomalies_batch(anomalies)
        assert len(result["created"]) == 1  # Only critical creates a report
        assert len(result["regressions"]) == 0  # No regressions expected

    def test_emit_diagnostic_event_no_engine(self):
        bridge, _gen = self._setup()
        report = BugReport(bug_id="BUG-001", title="Test emit")
        # Should not crash when swarm_diagnostics is not available
        event = bridge.emit_diagnostic_event(report, event_type="bug:created")
        # In test env it may or may not have diagnostics; just ensure no crash
        assert event is None or hasattr(event, "event_id")


# ═══════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════


class TestFullCycle:
    def _setup(self):
        g = BugReportGenerator()
        g._reports.clear()
        g._next_id = 1
        return g

    def test_generate_write_read_markdown(self):
        """Create a full bug and verify the markdown round-trip."""
        g = self._setup()

        report = g.create(
            title="Full cycle integration test",
            category=BugCategory.BACKEND,
            severity=BugSeverity.HIGH,
            symptoms=["Symptom 1", "Symptom 2"],
            root_cause="Root cause here",
            reproduction_flow=["Step 1", "Step 2", "Step 3"],
            architectural_risk="Arch risk here",
            swarm_impact="Swarm impact here",
            affected_files=[{"file": "app/core.py", "lines": "1-10", "change": "modified"}],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            cat_dir = os.path.join(tmpdir, "backend")
            os.makedirs(cat_dir, exist_ok=True)
            writer = BugReportMarkdownWriter()
            path = writer.write(report, cat_dir)

            # Verify file exists and has expected content
            assert os.path.exists(path)
            with open(path) as f:
                content = f.read()

            assert "# Bug Report" in content
            assert report.bug_id in content
            assert "HIGH" in content or "high" in content
            assert "Root cause here" in content
            assert "Step 1" in content
            assert "app/core.py" in content

    def test_regression_round_trip(self):
        """Bug → FIXED → REGRESSION → re-detection flow."""
        g = self._setup()
        tracker = RegressionTracker(generator=g)

        # Create and fix a bug
        report = g.create(title="Round trip regression test")
        g.update_status(report.bug_id, BugStatus.FIXED)

        # Register a regression
        tracker.register_regression(report.bug_id, commit_hash="bad-commit")
        assert g.get(report.bug_id).is_regression

        # Verify the regression history
        history = tracker.regression_history(report.bug_id)
        assert len(history) == 1
        assert history[0].commit_hash == "bad-commit"

    def test_multiple_bug_id_sequence(self):
        """Verify BUG-001, BUG-002, … sequence."""
        g = self._setup()
        ids = []
        for i in range(5):
            r = g.create(title=f"Bug {i}")
            ids.append(r.bug_id)
        assert ids == ["BUG-001", "BUG-002", "BUG-003", "BUG-004", "BUG-005"]


# ═══════════════════════════════════════════════════════════════
# Edge Case Tests
# ═══════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_report_with_empty_title(self):
        report = BugReport(bug_id="BUG-001", title="")
        assert report.filename_slug.endswith("_")

    def test_report_with_special_chars_in_title(self):
        report = BugReport(bug_id="BUG-001", title="Bug / Fix: #@! rate_limiter (v2)")
        slug = report.filename_slug
        assert "/" not in slug.split("_BUG-001_", 1)[1]

    def test_generator_list_nonexistent_status(self):
        g = BugReportGenerator()
        # Clear any cross-test leakage (singleton state)
        g._reports.clear()
        result = g.list_all(status=BugStatus.REGRESSION)
        assert result == []

    def test_regression_tracker_empty(self):
        tracker = RegressionTracker()
        assert tracker.regression_count("NONEXISTENT") == 0
        assert tracker.bugs_with_regressions() == []

    def test_tracker_stats_empty(self):
        tracker = RegressionTracker()
        s = tracker.stats()
        assert s["total_regressions"] == 0
        assert s["unique_bugs_regressed"] == 0
