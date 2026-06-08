"""add_weekly_learning_models (CourseWeeklyPlan, CourseWeek, WeekContent)

Revision ID: 0d1e2f3a4b5c
Revises: 6e7f8a9b0c1d
Create Date: 2026-05-31 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0d1e2f3a4b5c"
down_revision: Union[str, Sequence[str], None] = "6e7f8a9b0c1d"
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

    # --- weekly_plans ---
    if not _has_table(inspector, "weekly_plans"):
        op.create_table(
            "weekly_plans",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
            sa.Column("teacher_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("total_weeks", sa.Integer(), nullable=False, server_default=sa.text("5")),
            sa.Column("thematic_line", sa.String(500), nullable=False),
            sa.Column("pedagogical_intention", sa.Text(), nullable=False),
            sa.Column("bloom_progression", sa.JSON(), nullable=False),
            sa.Column("week_themes", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # --- course_weeks ---
    if not _has_table(inspector, "course_weeks"):
        op.create_table(
            "course_weeks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("plan_id", sa.String(36), sa.ForeignKey("weekly_plans.id"), nullable=False, index=True),
            sa.Column("week_number", sa.Integer(), nullable=False, index=True),
            sa.Column("theme", sa.String(255), nullable=False),
            sa.Column("bloom_target", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("objectives", sa.JSON(), nullable=False),
            sa.Column("misconceptions", sa.JSON(), nullable=False),
            sa.Column("real_applications", sa.JSON(), nullable=False),
            sa.Column("recommended_modality", sa.String(50), nullable=True),
            sa.Column("multimodal_prompts", sa.JSON(), nullable=False),
            sa.Column("evaluation_criteria", sa.JSON(), nullable=False),
            sa.Column("orchestration_status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        )

    # --- week_contents ---
    if not _has_table(inspector, "week_contents"):
        op.create_table(
            "week_contents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("week_id", sa.String(36), sa.ForeignKey("course_weeks.id"), nullable=False, unique=True, index=True),
            sa.Column("introduction", sa.Text(), nullable=False, server_default=""),
            sa.Column("pedagogical_explanation", sa.Text(), nullable=False, server_default=""),
            sa.Column("examples", sa.JSON(), nullable=False),
            sa.Column("guided_practice", sa.Text(), nullable=False, server_default=""),
            sa.Column("storyboard", sa.Text(), nullable=True),
            sa.Column("continuity_notes", sa.Text(), nullable=True),
            sa.Column("pedagogical_stages", sa.JSON(), nullable=False),
            sa.Column("retrieval_evidence", sa.JSON(), nullable=False),
            sa.Column("swarm_trace", sa.JSON(), nullable=False),
            sa.Column("memory_ids", sa.JSON(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # --- indexes for weekly_plans ---
    inspector = sa.inspect(op.get_bind())
    for name, columns in (
        ("ix_weekly_plans_course_id", ["course_id"]),
        ("ix_weekly_plans_teacher_id", ["teacher_id"]),
    ):
        if not _has_index(inspector, "weekly_plans", *columns):
            op.create_index(name, "weekly_plans", columns)

    # --- indexes for course_weeks ---
    inspector = sa.inspect(op.get_bind())
    for name, columns in (
        ("ix_course_weeks_plan_id", ["plan_id"]),
        ("ix_course_weeks_week_number", ["week_number"]),
    ):
        if not _has_index(inspector, "course_weeks", *columns):
            op.create_index(name, "course_weeks", columns)

    # --- index for week_contents ---
    inspector = sa.inspect(op.get_bind())
    if not _has_index(inspector, "week_contents", "week_id"):
        op.create_index("ix_week_contents_week_id", "week_contents", ["week_id"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table in ("week_contents", "course_weeks", "weekly_plans"):
        if _has_table(inspector, table):
            op.drop_table(table)
