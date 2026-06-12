"""reconcile ORM tables and enums with the actual model definitions

Revision 6d7e8f9a0b1c attempted to formalize tables that had only ever been
created by Base.metadata.create_all() at startup (removed in 99e98b4), but it
created them under the wrong names and types:

    migration created            ORM actually maps
    -------------------------    ---------------------------------
    educational_context          educational_contexts
    concept_prerequisite         concept_prerequisites
    resource_programming_tag     resource_programming_tags
    status VARCHAR(20)           educationalcontextstatus enum

This migration idempotently creates the enums and the correctly-named tables
so that any database — fresh or existing production — converges on the schema
the ORM expects. The misnamed orphan tables are dropped only when empty.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Mirrors EducationalContextStatus in app/models/educational_context.py.
EDUCATIONAL_CONTEXT_STATUS_VALUES = [
    "pending",
    "initializing",
    "active",
    "degraded",
    "failed",
    "partial",
    "recovering",
    "suspended",
    "archived",
]

# Mirrors ProgrammingConcept in app/models/programming_domain.py.
PROGRAMMING_CONCEPT_VALUES = [
    "variables",
    "data_types",
    "expressions",
    "input_output",
    "conditionals",
    "boolean_logic",
    "nested_conditionals",
    "loops",
    "nested_loops",
    "loop_patterns",
    "arrays",
    "strings",
    "dictionaries",
    "matrices",
    "functions",
    "parameters",
    "return_values",
    "scope",
    "recursion",
    "algorithm_design",
    "searching",
    "sorting",
    "complexity",
    "debugging",
    "error_handling",
    "computational_thinking",
]

# Orphan tables created under the wrong name by 6d7e8f9a0b1c. The ORM never
# mapped them, so they should be empty everywhere; dropped only if they are.
ORPHAN_TABLES = [
    "educational_context",
    "concept_prerequisite",
    "resource_programming_tag",
]


def _ensure_enum(name: str, values: list[str]) -> None:
    quoted = ", ".join(f"'{v}'" for v in values)
    op.execute(
        sa.text(
            f"""
            DO $$ BEGIN
                CREATE TYPE {name} AS ENUM ({quoted});
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    # Pre-existing enums (from create_all with an older value set) may be
    # missing values. Requires PostgreSQL >= 12 inside a transaction.
    for val in values:
        op.execute(sa.text(f"ALTER TYPE {name} ADD VALUE IF NOT EXISTS '{val}'"))


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _status_enum() -> postgresql.ENUM:
    return postgresql.ENUM(
        *EDUCATIONAL_CONTEXT_STATUS_VALUES,
        name="educationalcontextstatus",
        create_type=False,
    )


def _concept_enum() -> postgresql.ENUM:
    return postgresql.ENUM(
        *PROGRAMMING_CONCEPT_VALUES,
        name="programmingconcept",
        create_type=False,
    )


def _create_educational_contexts() -> None:
    if _has_table("educational_contexts"):
        return
    op.create_table(
        "educational_contexts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("enrollment_id", sa.String(36), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("course_id", sa.String(36), nullable=False),
        sa.Column("teacher_id", sa.String(36), nullable=True),
        # No server_default: the ORM supplies status (Python-side default
        # PENDING), and a default referencing an enum value added by ALTER
        # TYPE earlier in this same transaction would raise "unsafe use of
        # new value" on PostgreSQL >= 12.
        sa.Column("status", _status_enum(), nullable=False),
        sa.Column("swarm_config", sa.JSON(), nullable=True),
        sa.Column("adaptive_params", sa.JSON(), nullable=True),
        sa.Column("shared_memory_key", sa.String(255), nullable=True),
        sa.Column(
            "activation_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"], ["enrollments.id"],
            name="fk_educational_contexts_enrollment",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"], ["users.id"],
            name="fk_educational_contexts_student",
        ),
        sa.ForeignKeyConstraint(
            ["course_id"], ["courses.id"],
            name="fk_educational_contexts_course",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"], ["users.id"],
            name="fk_educational_contexts_teacher",
        ),
        sa.UniqueConstraint("enrollment_id", name="uq_educational_contexts_enrollment"),
        sa.UniqueConstraint(
            "shared_memory_key", name="uq_educational_contexts_shared_memory_key"
        ),
    )
    op.create_index(
        "ix_educational_contexts_student_id", "educational_contexts", ["student_id"]
    )
    op.create_index(
        "ix_educational_contexts_course_id", "educational_contexts", ["course_id"]
    )
    op.create_index(
        "ix_educational_contexts_status", "educational_contexts", ["status"]
    )


def _create_concept_prerequisites() -> None:
    if _has_table("concept_prerequisites"):
        return
    op.create_table(
        "concept_prerequisites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("concept", _concept_enum(), nullable=False),
        sa.Column("required_concept", _concept_enum(), nullable=False),
        sa.Column(
            "strength", sa.Float(), nullable=False, server_default=sa.text("1.0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("concept", "required_concept", name="uq_concept_prereq"),
    )
    op.create_index("ix_concept_prerequisites_concept", "concept_prerequisites", ["concept"])
    op.create_index(
        "ix_concept_prerequisites_required_concept",
        "concept_prerequisites",
        ["required_concept"],
    )


def _create_resource_programming_tags() -> None:
    if _has_table("resource_programming_tags"):
        return
    op.create_table(
        "resource_programming_tags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_id", sa.String(36), nullable=False),
        sa.Column("concept", _concept_enum(), nullable=False),
        sa.Column(
            "bloom_level", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "difficulty", sa.Float(), nullable=False, server_default=sa.text("0.5")
        ),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column(
            "is_exercise", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"], ["resources.id"],
            name="fk_resource_programming_tags_resource",
        ),
    )
    op.create_index(
        "ix_resource_programming_tags_resource_id",
        "resource_programming_tags",
        ["resource_id"],
    )


def _drop_orphan_if_empty(name: str) -> None:
    if not _has_table(name):
        return
    conn = op.get_bind()
    count = conn.execute(sa.text(f'SELECT COUNT(*) FROM "{name}"')).scalar()
    if count == 0:
        op.drop_table(name)


def upgrade() -> None:
    _ensure_enum("educationalcontextstatus", EDUCATIONAL_CONTEXT_STATUS_VALUES)
    _ensure_enum("programmingconcept", PROGRAMMING_CONCEPT_VALUES)

    _create_educational_contexts()
    _create_concept_prerequisites()
    _create_resource_programming_tags()

    for orphan in ORPHAN_TABLES:
        _drop_orphan_if_empty(orphan)


def downgrade() -> None:
    # Intentional no-op. Upgrade is conditional (create-if-missing), so a
    # downgrade cannot tell whether it created these tables or whether they
    # pre-existed with production data (create_all-era databases). Every
    # deployed application version maps these tables, so dropping them would
    # break the rolled-back code too. To roll back a bad deploy, redeploy the
    # previous application image and leave the schema in place.
    pass
