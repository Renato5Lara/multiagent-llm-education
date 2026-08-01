"""
BUG-SWARM-002 (nested tx / dual commit) + BUG-SWARM-003 (false active states)
regression tests, for the sync activation path
(activate_enrollment_with_swarm_sync / _activate_enrollment_sync).

The async path (activate_enrollment_with_swarm, SwarmOrchestrator) was
retired in ADR-0011 — it had no real caller in production. Its tests
were removed along with it, not migrated.

BUG-SWARM-002 Verifies:
- activate_enrollment_with_swarm_sync does NOT call db.commit() or db.rollback()

BUG-SWARM-003 Verifies:
- ctx.status starts as INITIALIZING (not ACTIVE) before swarm runs
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
        from app.services.activation_service import activate_enrollment_with_swarm_sync

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


# ═══════════════════════════════════════════════════════════════
# BUG-SWARM-003 TESTS: Activation State Correctness
# ═══════════════════════════════════════════════════════════════


class TestActivationStateCorrectness:
    """Verify ctx.status transitions correctly through activation lifecycle.

    States: PENDING → INITIALIZING → ACTIVE (success)
           PENDING → INITIALIZING → FAILED (failure)
    Never: ACTIVE set before swarm completes or outside savepoint.
    """

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
            "app.services.activation_service.activate_enrollment_with_swarm_sync"
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


# ═══════════════════════════════════════════════════════════════
# BASIC SMOKE TESTS
# ═══════════════════════════════════════════════════════════════


def test_imports():
    """All modules import without errors."""
    from app.services.activation_service import activate_enrollment_with_swarm_sync
    from app.db.uow import UnitOfWork
    assert activate_enrollment_with_swarm_sync is not None
    assert UnitOfWork is not None
