"""add missing educational_context, programming_metrics, concept_prerequisite, resource_programming_tag

Formalizes tables that were defined in models but never tracked by Alembic.
See DB-003 in forensic audit for root cause.

Revision ID: 6d7e8f9a0b1c
Revises: 5c924adef43d
Create Date: 2026-05-27 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6d7e8f9a0b1c"
down_revision: Union[str, Sequence[str], None] = "5c924adef43d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_DEFINITIONS = {
    "educational_context": {
        "columns": [
            ("id", sa.String(36), True),
            ("enrollment_id", sa.String(36), False),
            ("student_id", sa.String(36), False),
            ("course_id", sa.String(36), False),
            ("teacher_id", sa.String(36), True),
            ("status", sa.String(20), False),
            ("swarm_config", sa.JSON(), True),
            ("adaptive_params", sa.JSON(), True),
            ("shared_memory_key", sa.String(255), True),
            ("activation_attempts", sa.Integer(), False),
            ("last_error", sa.String(500), True),
            ("activated_at", sa.DateTime(timezone=True), True),
            ("created_at", sa.DateTime(timezone=True), False),
            ("updated_at", sa.DateTime(timezone=True), False),
        ],
        "fks": [
            ("enrollment_id", "enrollments.id", "fk_educational_context_enrollment"),
            ("student_id", "users.id", "fk_educational_context_student"),
            ("course_id", "courses.id", "fk_educational_context_course"),
            ("teacher_id", "users.id", "fk_educational_context_teacher"),
        ],
        "indexes": [
            "ix_educational_context_status",
            "ix_educational_context_student_id",
            "ix_educational_context_course_id",
            "ix_educational_context_enrollment_id",
        ],
        "unique_constraints": [
            ("uq_educational_context_enrollment", ["enrollment_id"]),
            ("uq_educational_context_shared_memory_key", ["shared_memory_key"]),
        ],
    },
    "concept_prerequisite": {
        "columns": [
            ("id", sa.String(36), True),
            ("concept", sa.String(50), False),
            ("required_concept", sa.String(50), False),
            ("strength", sa.Float(), False),
            ("created_at", sa.DateTime(timezone=True), False),
        ],
        "indexes": [
            "ix_concept_prerequisite_concept",
            "ix_concept_prerequisite_required_concept",
        ],
        "unique_constraints": [
            ("uq_concept_prerequisite", ["concept", "required_concept"]),
        ],
    },
    "programming_metrics": {
        "columns": [
            ("id", sa.String(36), True),
            ("student_id", sa.String(36), False),
            ("course_id", sa.String(36), False),
            ("pseudocode_quality", sa.Float(), False),
            ("debugging_efficiency", sa.Float(), False),
            ("code_reading_speed", sa.Float(), False),
            ("ct_decomposition", sa.Float(), False),
            ("ct_pattern_recognition", sa.Float(), False),
            ("ct_abstraction", sa.Float(), False),
            ("ct_algorithm_design", sa.Float(), False),
            ("syntax_error_rate", sa.Float(), False),
            ("logic_error_rate", sa.Float(), False),
            ("semantic_error_rate", sa.Float(), False),
            ("stage_progression", sa.Float(), False),
            ("concept_mastery_rate", sa.Float(), False),
            ("concept_scores", sa.JSON(), True),
            ("error_history", sa.JSON(), True),
            ("calculated_at", sa.DateTime(timezone=True), False),
        ],
        "fks": [
            ("student_id", "users.id", "fk_programming_metrics_student"),
            ("course_id", "courses.id", "fk_programming_metrics_course"),
        ],
        "indexes": [
            "ix_programming_metrics_student_id",
            "ix_programming_metrics_course_id",
        ],
    },
    "resource_programming_tag": {
        "columns": [
            ("id", sa.String(36), True),
            ("resource_id", sa.String(36), False),
            ("concept", sa.String(50), False),
            ("bloom_level", sa.Integer(), False),
            ("difficulty", sa.Float(), False),
            ("language", sa.String(50), True),
            ("is_exercise", sa.Integer(), False),
            ("created_at", sa.DateTime(timezone=True), False),
        ],
        "fks": [
            ("resource_id", "resources.id", "fk_resource_programming_tag_resource"),
        ],
        "indexes": [
            "ix_resource_programming_tag_resource_id",
        ],
    },
}


def _has_table(name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return inspector.has_table(name)


def _create_table_if_missing(name: str, definition: dict) -> None:
    if _has_table(name):
        return

    columns = []
    for col_name, col_type, nullable in definition["columns"]:
        kwargs = {"nullable": nullable}
        if col_name == "id":
            kwargs["primary_key"] = True
        if not nullable and col_name not in ("id", "updated_at", "created_at", "activated_at",
                                              "calculated_at", "last_error", "error_history",
                                              "concept_scores", "shared_memory_key", "teacher_id",
                                              "language", "swarm_config", "adaptive_params"):
            kwargs["server_default"] = sa.text("0")
        columns.append(sa.Column(col_name, col_type, **kwargs))

    op.create_table(name, *columns)

    for fk_col, ref, fk_name in definition.get("fks", []):
        if not _has_fk(name, fk_col, ref):
            op.create_foreign_key(fk_name, name, ref.split(".")[0], [fk_col], [ref.split(".")[1]])

    for idx_name in definition.get("indexes", []):
        idx_cols = idx_name.replace(f"ix_{name}_", "")
        if not _has_index(name, idx_cols):
            op.create_index(idx_name, name, [idx_cols])

    for uq_name, uq_cols in definition.get("unique_constraints", []):
        if not _has_unique(name, uq_name):
            op.create_unique_constraint(uq_name, name, uq_cols)


def _has_fk(table: str, column: str, ref: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    ref_table = ref.split(".")[0]
    for fk in inspector.get_foreign_keys(table):
        if fk.get("constrained_columns") == [column] and fk.get("referred_table") == ref_table:
            return True
    return False


def _has_index(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    wanted = {column}
    for idx in inspector.get_indexes(table):
        if set(idx.get("column_names") or []) == wanted:
            return True
    return False


def _has_unique(table: str, name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    for constraint in inspector.get_unique_constraints(table):
        if constraint.get("name") == name:
            return True
    return False


def upgrade() -> None:
    for table_name, definition in TABLE_DEFINITIONS.items():
        _create_table_if_missing(table_name, definition)


def downgrade() -> None:
    for table_name in reversed(list(TABLE_DEFINITIONS.keys())):
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        if inspector.has_table(table_name):
            op.drop_table(table_name)
