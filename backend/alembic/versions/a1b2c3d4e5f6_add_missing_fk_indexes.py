"""add missing FK indexes for performance

Revision ID: a1b2c3d4e5f6
Revises: 7c8d9e0f1a2b, 0d1e2f3a4b5c
Create Date: 2026-06-08
"""

from typing import Sequence, Union
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = ("7c8d9e0f1a2b", "0d1e2f3a4b5c")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # enrollments — FK lookups by student, course, teacher
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_teacher_id", "enrollments", ["teacher_id"])

    # audit_logs — lookups by user
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])

    # diagnostic_results — lookups by student and course
    op.create_index("ix_diagnostic_results_student_id", "diagnostic_results", ["student_id"])
    op.create_index("ix_diagnostic_results_course_id", "diagnostic_results", ["course_id"])

    # learning_paths — lookups by student and course
    op.create_index("ix_learning_paths_student_id", "learning_paths", ["student_id"])
    op.create_index("ix_learning_paths_course_id", "learning_paths", ["course_id"])

    # student_progress — lookups by student, course, resource
    op.create_index("ix_student_progress_student_id", "student_progress", ["student_id"])
    op.create_index("ix_student_progress_course_id", "student_progress", ["course_id"])
    op.create_index("ix_student_progress_resource_id", "student_progress", ["resource_id"])

    # evaluation_attempts — lookups by student, course, module
    op.create_index("ix_evaluation_attempts_student_id", "evaluation_attempts", ["student_id"])
    op.create_index("ix_evaluation_attempts_course_id", "evaluation_attempts", ["course_id"])
    op.create_index("ix_evaluation_attempts_module_id", "evaluation_attempts", ["module_id"])

    # path_modules — lookups by path
    op.create_index("ix_path_modules_path_id", "path_modules", ["path_id"])


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
