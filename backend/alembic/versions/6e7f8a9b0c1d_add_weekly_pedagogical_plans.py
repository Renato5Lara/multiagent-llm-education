"""add_weekly_pedagogical_plans

Revision ID: 6e7f8a9b0c1d
Revises: 5d6e7f8a9b0c
Create Date: 2026-05-31 18:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6e7f8a9b0c1d"
down_revision: Union[str, Sequence[str], None] = "5d6e7f8a9b0c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector: sa.Inspector, table_name: str) -> bool:
    return inspector.has_table(table_name)


def _has_index(inspector: sa.Inspector, table_name: str, *column_names: str) -> bool:
    wanted = set(column_names)
    return any(
        set(index.get("column_names") or []) == wanted
        for index in inspector.get_indexes(table_name)
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_table(inspector, "weekly_pedagogical_plans"):
        op.create_table(
            "weekly_pedagogical_plans",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("course_id", sa.String(36), nullable=False),
            sa.Column("teacher_id", sa.String(36), nullable=False),
            sa.Column("week_number", sa.Integer(), nullable=False),
            sa.Column("topic", sa.String(255), nullable=False),
            sa.Column("objectives", sa.JSON(), nullable=False),
            sa.Column("bloom_target", sa.Integer(), nullable=False, server_default=sa.text("3")),
            sa.Column("pedagogical_style", sa.String(80), nullable=False),
            sa.Column("pedagogical_intention", sa.Text(), nullable=False),
            sa.Column("preferred_modality", sa.String(80), nullable=False),
            sa.Column("orchestration_status", sa.String(30), nullable=False, server_default="generated"),
            sa.Column("retrieval_summary", sa.JSON(), nullable=False),
            sa.Column("pedagogical_structure", sa.JSON(), nullable=False),
            sa.Column("adaptive_plan", sa.JSON(), nullable=False),
            sa.Column("multimodal_plan", sa.JSON(), nullable=False),
            sa.Column("prompt_plan", sa.JSON(), nullable=False),
            sa.Column("consistency_validation", sa.JSON(), nullable=False),
            sa.Column("consensus_result", sa.JSON(), nullable=False),
            sa.Column(
                "generated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["course_id"], ["courses.id"], name="fk_weekly_plan_course"),
            sa.ForeignKeyConstraint(["teacher_id"], ["users.id"], name="fk_weekly_plan_teacher"),
        )

    inspector = sa.inspect(op.get_bind())
    for name, columns in (
        ("ix_weekly_pedagogical_plans_course_id", ["course_id"]),
        ("ix_weekly_pedagogical_plans_teacher_id", ["teacher_id"]),
        ("ix_weekly_pedagogical_plans_week_number", ["week_number"]),
    ):
        if not _has_index(inspector, "weekly_pedagogical_plans", *columns):
            op.create_index(name, "weekly_pedagogical_plans", columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_table(inspector, "weekly_pedagogical_plans"):
        op.drop_table("weekly_pedagogical_plans")
