"""add missing FK indexes for performance

Revision ID: a1b2c3d4e5f6
Revises: 7c8d9e0f1a2b, 0d1e2f3a4b5c
Create Date: 2026-06-08
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = ("7c8d9e0f1a2b", "0d1e2f3a4b5c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return column in {col["name"] for col in inspector.get_columns(table)}


def _ensure_enrollments_columns() -> None:
    # enrollments.teacher_id and context_key exist in the ORM model but were
    # only ever created by Base.metadata.create_all() at startup (removed in
    # 99e98b4), never by a migration. Fresh databases need them before the
    # teacher_id index below can be created.
    if not _has_column("enrollments", "teacher_id"):
        op.add_column(
            "enrollments", sa.Column("teacher_id", sa.String(36), nullable=True)
        )
        op.create_foreign_key(
            "fk_enrollments_teacher", "enrollments", "users", ["teacher_id"], ["id"]
        )
    if not _has_column("enrollments", "context_key"):
        op.add_column(
            "enrollments", sa.Column("context_key", sa.String(255), nullable=True)
        )


def upgrade() -> None:
    _ensure_enrollments_columns()

    # if_not_exists keeps this idempotent on databases where create_all or a
    # previous partial run already created some of these indexes.

    # enrollments — FK lookups by student, course, teacher
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"], if_not_exists=True)
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"], if_not_exists=True)
    op.create_index("ix_enrollments_teacher_id", "enrollments", ["teacher_id"], if_not_exists=True)

    # audit_logs — lookups by user
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], if_not_exists=True)

    # diagnostic_results — lookups by student and course
    op.create_index("ix_diagnostic_results_student_id", "diagnostic_results", ["student_id"], if_not_exists=True)
    op.create_index("ix_diagnostic_results_course_id", "diagnostic_results", ["course_id"], if_not_exists=True)

    # learning_paths — lookups by student and course
    op.create_index("ix_learning_paths_student_id", "learning_paths", ["student_id"], if_not_exists=True)
    op.create_index("ix_learning_paths_course_id", "learning_paths", ["course_id"], if_not_exists=True)

    # student_progress — lookups by student, course, resource
    op.create_index("ix_student_progress_student_id", "student_progress", ["student_id"], if_not_exists=True)
    op.create_index("ix_student_progress_course_id", "student_progress", ["course_id"], if_not_exists=True)
    op.create_index("ix_student_progress_resource_id", "student_progress", ["resource_id"], if_not_exists=True)

    # evaluation_attempts — lookups by student, course, module
    op.create_index("ix_evaluation_attempts_student_id", "evaluation_attempts", ["student_id"], if_not_exists=True)
    op.create_index("ix_evaluation_attempts_course_id", "evaluation_attempts", ["course_id"], if_not_exists=True)
    op.create_index("ix_evaluation_attempts_module_id", "evaluation_attempts", ["module_id"], if_not_exists=True)

    # path_modules — lookups by path
    op.create_index("ix_path_modules_path_id", "path_modules", ["path_id"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("ix_path_modules_path_id", "path_modules")

    op.drop_index("ix_evaluation_attempts_module_id", "evaluation_attempts")
    op.drop_index("ix_evaluation_attempts_course_id", "evaluation_attempts")
    op.drop_index("ix_evaluation_attempts_student_id", "evaluation_attempts")

    op.drop_index("ix_student_progress_resource_id", "student_progress")
    op.drop_index("ix_student_progress_course_id", "student_progress")
    op.drop_index("ix_student_progress_student_id", "student_progress")

    op.drop_index("ix_learning_paths_course_id", "learning_paths")
    op.drop_index("ix_learning_paths_student_id", "learning_paths")

    op.drop_index("ix_diagnostic_results_course_id", "diagnostic_results")
    op.drop_index("ix_diagnostic_results_student_id", "diagnostic_results")

    op.drop_index("ix_audit_logs_user_id", "audit_logs")

    op.drop_index("ix_enrollments_teacher_id", "enrollments")
    op.drop_index("ix_enrollments_student_id", "enrollments")
    op.drop_index("ix_enrollments_course_id", "enrollments")
