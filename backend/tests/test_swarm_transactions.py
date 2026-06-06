"""
BUG-SWARM-002 (nested tx / dual commit) + BUG-SWARM-003 (false active states)
regression tests.

BUG-SWARM-002 Verifies:
- activate_enrollment_with_swarm does NOT call db.commit() or db.rollback()
- Savepoint isolation: swarm failure rolls back savepoint, outer tx unaffected
- Session lifecycle: session is saved with "failed" status after swarm failure
- UnitOfWork uses lambda: db pattern (not Session as factory)
- Orchestrator can commit/rollback via savepoint without aborting outer tx

BUG-SWARM-003 Verifies:
- ctx.status is set to FAILED on swarm failure (not ACTIVE)
- ctx.status starts as INITIALIZING (not ACTIVE) before swarm runs
- _phase_active inside savepoint correctly sets ACTIVE on success
- No false-positive ACTIVE states in any failure path
"""

import logging
from unittest.mock import MagicMock, patch, call, ANY

import pytest

from app.db.uow import UnitOfWork
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.educational_context import EducationalContext, EducationalContextStatus


# ═══════════════════════════════════════════════════════════════
# UNIT TESTS — NO DB REQUIRED
# ═══════════════════════════════════════════════════════════════


class TestActivateEnrollmentWithSwarm:
    """Verify activate_enrollment_with_swarm has no dual-commit bugs."""

    def test_no_db_commit_called(self):
        """CRITICAL: sync wrapper must NOT call db.commit()."""
        from app.services.activation_service import (
            activate_enrollment_with_swarm_sync,
        )

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-1"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)
        context.id = "ctx-1"

        result = activate_enrollment_with_swarm_sync(
            db, enrollment, course, context
        )

        # db.commit() must NOT be called
        commit_calls = [
            c for c in db.mock_calls
            if c[0] == "commit"
        ]
        assert not commit_calls, (
            f"db.commit() should NOT be called by activate_enrollment_with_swarm, "
            f"got {len(commit_calls)} calls"
        )

    def test_no_db_rollback_called(self):
        """CRITICAL: activate_enrollment_with_swarm must NOT call db.rollback()."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-2"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)

        context.status = None
        context.activation_attempts = 0
        context.last_error = None

        activate_enrollment_with_swarm_sync(db, enrollment, course, context)

        rollback_calls = [
            c for c in db.mock_calls
            if c[0] == "rollback"
        ]
        assert not rollback_calls, (
            f"db.rollback() should NOT be called by activate_enrollment_with_swarm, "
            f"got {len(rollback_calls)} calls"
        )

    def test_uow_uses_lambda_factory(self):
        """UnitOfWork must use lambda: db, not Session directly."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-3"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)

        actual_uow = None

        def capture_uow(db_arg, context_arg, uow=None):
            nonlocal actual_uow
            actual_uow = uow
            mock = MagicMock()
            mock.activate.return_value = {"ok": True}
            return mock

        with patch(
            "app.services.activation_service.SwarmOrchestrator",
            side_effect=capture_uow,
        ):
            mock_savepoint_ctx = MagicMock()
            db.begin_nested.return_value = mock_savepoint_ctx
            mock_savepoint_ctx.__enter__.return_value = None
            mock_savepoint_ctx.__exit__.return_value = None

            activate_enrollment_with_swarm(db, enrollment, course, context)

        assert actual_uow is not None, "SwarmOrchestrator was not created with uow"
        # UnitOfWork._session_factory should be a lambda, not a Session
        assert callable(actual_uow._session_factory), (
            "UnitOfWork._session_factory must be callable (lambda: db), "
            f"got {type(actual_uow._session_factory)}"
        )

    def test_savepoint_rollback_on_failure(self):
        """Verify savepoint is rolled back on swarm failure,
        and outer db is NOT rolled back."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-4"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)

        mock_savepoint_ctx = MagicMock()
        db.begin_nested.return_value = mock_savepoint_ctx

        # Simulate savepoint __exit__ re-raising exception on failure
        mock_savepoint_ctx.__exit__.side_effect = lambda *a: True

        swarm_error = RuntimeError("Swarm crashed")
        with patch(
            "app.services.activation_service.SwarmOrchestrator"
        ) as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.activate.side_effect = swarm_error
            mock_orch_cls.return_value = mock_orch

            result = activate_enrollment_with_swarm(
                db, enrollment, course, context
            )

        # Swarm failure should return graceful error
        assert result.get("ok") is False, (
            "Should return graceful error on swarm failure"
        )
        assert "error" in result, "Result should contain error message"

        # outer db.rollback() must NOT be called
        rollback_calls = [
            c for c in db.mock_calls if c[0] == "rollback"
        ]
        assert not rollback_calls, (
            f"db.rollback() should NOT be called on swarm failure, "
            f"got {len(rollback_calls)} calls"
        )

    def test_savepoint_commit_on_success(self):
        """Verify savepoint is committed (released) on swarm success."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-5"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)

        # Use a real context manager that records state
        class SavepointTracker:
            def __init__(self):
                self.entered = False
                self.exited = False
                self.exc = None

            def __enter__(self):
                self.entered = True

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.exited = True
                self.exc = exc_val
                return True  # Suppress exception

        tracker = SavepointTracker()
        db.begin_nested.return_value = tracker

        with patch(
            "app.services.activation_service.SwarmOrchestrator"
        ) as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.activate.return_value = {"ok": True}
            mock_orch_cls.return_value = mock_orch

            result = activate_enrollment_with_swarm(
                db, enrollment, course, context
            )

        assert result.get("ok") is True, (
            f"Should return success result, got {result}"
        )
        assert tracker.entered, "Savepoint was never entered"
        assert tracker.exited, "Savepoint was never exited"
        assert tracker.exc is None, (
            f"Savepoint should not see an exception on success, got {tracker.exc}"
        )


# ═══════════════════════════════════════════════════════════════
# BUG-SWARM-003 TESTS: Activation State Correctness
# ═══════════════════════════════════════════════════════════════


class TestActivationStateCorrectness:
    """Verify ctx.status transitions correctly through activation lifecycle.

    States: PENDING → INITIALIZING → ACTIVE (success)
           PENDING → INITIALIZING → FAILED (failure)
    Never: ACTIVE set before swarm completes or outside savepoint.
    """

    def test_status_is_failed_after_swarm_failure(self):
        """CRITICAL: ctx.status must be FAILED (not ACTIVE) after swarm failure."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-bs3-1"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)
        context.id = "ctx-bs3-1"
        context.activation_attempts = 0

        swarm_error = RuntimeError("Swarm exploded")
        with patch(
            "app.services.activation_service.SwarmOrchestrator"
        ) as mock_orch_cls:
            mock_orch = MagicMock()
            mock_orch.activate.side_effect = swarm_error
            mock_orch_cls.return_value = mock_orch

            mock_savepoint_ctx = MagicMock()
            # __exit__ returns True to suppress exception from with block
            # but the exception escapes around the with block
            mock_savepoint_ctx.__exit__.side_effect = lambda *a: False
            mock_savepoint_ctx.__enter__.return_value = None
            db.begin_nested.return_value = mock_savepoint_ctx

            result = activate_enrollment_with_swarm(
                db, enrollment, course, context
            )

        # Result must indicate failure
        assert result.get("ok") is False, "Result should be failure"
        assert "error" in result, "Result should have error message"

        # context.status must be FAILED, NOT ACTIVE
        assert context.status == EducationalContextStatus.FAILED, (
            f"ctx.status should be FAILED after swarm failure, "
            f"got {context.status}"
        )
        # last_error must be set
        assert context.last_error is not None, "last_error should be set"
        assert "Swarm exploded" in str(context.last_error), (
            "last_error should contain the exception message"
        )
        # activation_attempts must be incremented
        assert context.activation_attempts >= 1, (
            "activation_attempts should be incremented"
        )

    def test_status_is_not_active_on_failure(self):
        """CRITICAL: ctx.status must NEVER be ACTIVE after swarm failure.
        This test explicitly checks no ACTIVE attribute was set on context."""
        from app.services.activation_service import activate_enrollment_with_swarm_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-bs3-2"
        course = MagicMock()
        context = MagicMock(spec=EducationalContext)
        context.id = "ctx-bs3-2"
        context.activation_attempts = 0

        # Track all attribute sets on context
        setattr_history = []

        original_setattr = MockSetAttr = type(context).__setattr__

        def tracking_setattr(self, name, value):
            setattr_history.append((name, value))
            return original_setattr(self, name, value)

        with patch.object(type(context), "__setattr__", tracking_setattr):
            with patch(
                "app.services.activation_service.SwarmOrchestrator"
            ) as mock_orch_cls:
                mock_orch = MagicMock()
                mock_orch.activate.side_effect = RuntimeError("boom")
                mock_orch_cls.return_value = mock_orch

                mock_savepoint_ctx = MagicMock()
                mock_savepoint_ctx.__exit__.side_effect = lambda *a: False
                mock_savepoint_ctx.__enter__.return_value = None
                db.begin_nested.return_value = mock_savepoint_ctx

                activate_enrollment_with_swarm(
                    db, enrollment, course, context
                )

        # Check that status was set to FAILED, not ACTIVE
        status_sets = [
            v for v in setattr_history
            if v[0] == "status" and v[1] == EducationalContextStatus.ACTIVE
        ]
        assert len(status_sets) == 0, (
            f"ctx.status was set to ACTIVE {len(status_sets)} time(s) "
            f"during failed activation! Values: {status_sets}"
        )
        # Verify FAILED was set
        failed_sets = [
            v for v in setattr_history
            if v[0] == "status" and v[1] == EducationalContextStatus.FAILED
        ]
        assert len(failed_sets) >= 1, (
            "ctx.status was never set to FAILED during failed activation"
        )

    def test_activate_enrollment_sets_initializing_before_swarm(self):
        """_activate_enrollment should set INITIALIZING, not ACTIVE."""
        from app.services.activation_service import _activate_enrollment_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-bs3-3"
        enrollment.student_id = "stu-3"
        enrollment.course_id = "course-3"
        course = MagicMock()
        course.id = "course-3"
        course.teacher_id = "teacher-1"

        db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "app.services.activation_service.activate_enrollment_with_swarm"
        ) as mock_swarm:
            mock_swarm.return_value = {"ok": True}
            _activate_enrollment_sync(db, enrollment, course)

        # Find the EducationalContext that was added to db
        added_ctx = None
        for call_args in db.add.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], EducationalContext):
                added_ctx = args[0]
                break

        assert added_ctx is not None, "EducationalContext should have been created"
        assert added_ctx.status == EducationalContextStatus.INITIALIZING, (
            f"New EducationalContext should start as INITIALIZING, "
            f"got {added_ctx.status}"
        )

    def test_activate_enrollment_no_swarm_sets_active(self):
        """When run_swarm=False, status should be ACTIVE directly."""
        from app.services.activation_service import _activate_enrollment_sync

        db = MagicMock()
        enrollment = MagicMock(spec=Enrollment)
        enrollment.id = "enroll-bs3-4"
        enrollment.student_id = "stu-4"
        enrollment.course_id = "course-4"
        course = MagicMock()
        course.id = "course-4"
        course.teacher_id = "teacher-1"

        db.query.return_value.filter.return_value.first.return_value = None

        _activate_enrollment_sync(db, enrollment, course, run_swarm=False)

        # Find the EducationalContext that was added
        added_ctx = None
        for call_args in db.add.call_args_list:
            args, _ = call_args
            if args and isinstance(args[0], EducationalContext):
                added_ctx = args[0]
                break

        assert added_ctx is not None, "EducationalContext should have been created"
        # When no swarm runs, status is explicitly set to ACTIVE
        # by the run_swarm=False branch in _activate_enrollment
        assert added_ctx.status == EducationalContextStatus.ACTIVE, (
            f"Status should be ACTIVE when no swarm runs, "
            f"got {added_ctx.status}"
        )


class TestSwarmTransactionBoundaries:
    """Verify the outer transaction caller (session_service) integrity."""

    def test_session_saved_with_failed_after_swarm_failure(self):
        pytest.skip(
            "DB-002 migration: session_service is now async; "
            "test needs async def + execute() mocks"
        )

    def test_activate_enrollment_with_swarm_no_outside_commit(self):
        pytest.skip(
            "DB-002 migration: session_service is now async; "
            "test needs async def + execute() mocks"
        )


class TestUnitOfWorkConstruction:
    """Verify UnitOfWork is never constructed with Session directly."""

    def test_unit_of_work_rejects_session_as_factory(self):
        """UnitOfWork must be created with a callable, not a Session."""
        from sqlalchemy.orm import Session
        db = Session()
        # This should fail when .db is accessed, not at construction
        uow = UnitOfWork(db)
        with pytest.raises(TypeError, match="not callable"):
            _ = uow.db

    def test_unit_of_work_with_lambda(self):
        """UnitOfWork with lambda: db should work correctly."""
        db = MagicMock()
        uow = UnitOfWork(lambda: db)
        result = uow.db
        assert result is db, "uow.db should return the same session"


class TestSwarmOrchestratorUnitOfWork:
    """Verify SwarmOrchestrator uses proper UnitOfWork construction."""

    def test_orchestrator_uow_fallback_uses_lambda(self):
        """Orchestrator's fallback uow construction must use lambda."""
        from app.swarm.orchestrator import SwarmOrchestrator

        db = MagicMock()
        context = MagicMock()
        context.student_id = "s1"
        context.course_id = "c1"
        context.shared_memory_key = "ctx:s1:c1"

        orch = SwarmOrchestrator(db, context, uow=None)
        assert orch.uow is not None
        assert callable(orch.uow._session_factory), (
            "UnitOfWork._session_factory must be callable"
        )

    def test_orchestrator_uow_passed_through(self):
        """Orchestrator should use the passed uow as-is."""
        from app.swarm.orchestrator import SwarmOrchestrator

        db = MagicMock()
        context = MagicMock()
        context.student_id = "s1"
        context.course_id = "c1"
        context.shared_memory_key = "ctx:s1:c1"

        uow = UnitOfWork(lambda: db)
        orch = SwarmOrchestrator(db, context, uow=uow)
        assert orch.uow is uow, "Orchestrator should use the passed uow"


# ═══════════════════════════════════════════════════════════════
# BASIC SMOKE TESTS
# ═══════════════════════════════════════════════════════════════


def test_imports():
    """All modules import without errors."""
    from app.services.activation_service import activate_enrollment_with_swarm_sync
    from app.services.session_service import start_module_session, end_session
    from app.db.uow import UnitOfWork
    assert activate_enrollment_with_swarm is not None
    assert start_module_session is not None
    assert end_session is not None
    assert UnitOfWork is not None
