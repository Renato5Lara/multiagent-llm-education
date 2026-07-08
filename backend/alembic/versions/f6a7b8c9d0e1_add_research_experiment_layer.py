"""add_research_experiment_layer (instrumento pre/post-test + evidencia)

Research & Experiment Layer: banco fijo de preguntas MCQ, intentos pre/post
de conocimiento con respuestas normalizadas, comparación pre→post
materializada (experiment_results) y event-log de métricas de investigación
(research_metrics). Añade además dos columnas nullable a learning_paths para
registrar el nivel de conocimiento usado y la duración de generación.

Guarded: si un entorno ya tiene alguna tabla/columna, no se toca.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-08 09:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("knowledge_test_questions"):
        op.create_table(
            "knowledge_test_questions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("course_code", sa.String(20), nullable=False, index=True),
            sa.Column("module_number", sa.Integer(), nullable=False),
            sa.Column("topic", sa.String(100), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("options", sa.JSON(), nullable=False),
            sa.Column("correct_index", sa.Integer(), nullable=False),
            sa.Column("difficulty", sa.String(20), nullable=False),
            sa.Column("bloom_level", sa.Integer(), nullable=True),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "module_number >= 1 AND module_number <= 9", name="ck_ktq_module_range"
            ),
        )
        op.create_index(
            "ix_ktq_course_module_order",
            "knowledge_test_questions",
            ["course_code", "module_number", "order"],
        )

    if not inspector.has_table("knowledge_test_attempts"):
        op.create_table(
            "knowledge_test_attempts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True
            ),
            sa.Column(
                "course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False, index=True
            ),
            sa.Column("kind", sa.String(4), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_seconds", sa.Integer(), nullable=True),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("total_questions", sa.Integer(), nullable=True),
            sa.Column("percentage", sa.Float(), nullable=True),
            sa.Column("level", sa.String(20), nullable=True),
            sa.Column("question_order", sa.JSON(), nullable=True),
            sa.Column("module_breakdown", sa.JSON(), nullable=True),
            sa.Column("bank_version", sa.Integer(), nullable=True),
            sa.CheckConstraint("kind IN ('pre', 'post')", name="ck_kta_kind"),
            sa.UniqueConstraint(
                "student_id", "course_id", "kind", name="uq_kt_attempt_student_course_kind"
            ),
        )
        op.create_index(
            "ix_kta_course_kind_status",
            "knowledge_test_attempts",
            ["course_id", "kind", "status"],
        )

    if not inspector.has_table("knowledge_test_answers"):
        op.create_table(
            "knowledge_test_answers",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "attempt_id",
                sa.String(36),
                sa.ForeignKey("knowledge_test_attempts.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "question_id",
                sa.String(36),
                sa.ForeignKey("knowledge_test_questions.id"),
                nullable=False,
            ),
            sa.Column("selected_index", sa.Integer(), nullable=True),
            sa.Column("correct_index", sa.Integer(), nullable=False),
            sa.Column("is_correct", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("time_spent_seconds", sa.Integer(), nullable=True),
            sa.UniqueConstraint("attempt_id", "question_id", name="uq_kt_answer_attempt_question"),
        )

    if not inspector.has_table("experiment_results"):
        op.create_table(
            "experiment_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
            sa.Column(
                "pre_attempt_id",
                sa.String(36),
                sa.ForeignKey("knowledge_test_attempts.id"),
                nullable=False,
            ),
            sa.Column(
                "post_attempt_id",
                sa.String(36),
                sa.ForeignKey("knowledge_test_attempts.id"),
                nullable=False,
            ),
            sa.Column("pre_percentage", sa.Float(), nullable=False),
            sa.Column("post_percentage", sa.Float(), nullable=False),
            sa.Column("absolute_gain", sa.Float(), nullable=False),
            sa.Column("percent_gain", sa.Float(), nullable=True),
            sa.Column("normalized_gain", sa.Float(), nullable=True),
            sa.Column("pre_level", sa.String(20), nullable=False),
            sa.Column("post_level", sa.String(20), nullable=False),
            sa.Column("pre_duration_seconds", sa.Integer(), nullable=True),
            sa.Column("post_duration_seconds", sa.Integer(), nullable=True),
            sa.Column(
                "group_label", sa.String(30), nullable=False, server_default="Experimental"
            ),
            sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "student_id", "course_id", name="uq_experiment_result_student_course"
            ),
        )

    if not inspector.has_table("research_metrics"):
        op.create_table(
            "research_metrics",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True, index=True
            ),
            sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("metric_type", sa.String(60), nullable=False, index=True),
            sa.Column("value", sa.Float(), nullable=True),
            sa.Column("unit", sa.String(20), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, index=True),
        )
        op.create_index("ix_rm_student_type", "research_metrics", ["student_id", "metric_type"])
        op.create_index(
            "ix_rm_course_type_time",
            "research_metrics",
            ["course_id", "metric_type", "recorded_at"],
        )

    lp_columns = {col["name"] for col in inspector.get_columns("learning_paths")}
    if "knowledge_level" not in lp_columns:
        op.add_column("learning_paths", sa.Column("knowledge_level", sa.String(20), nullable=True))
    if "generation_duration_ms" not in lp_columns:
        op.add_column(
            "learning_paths", sa.Column("generation_duration_ms", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    lp_columns = {col["name"] for col in inspector.get_columns("learning_paths")}
    if "generation_duration_ms" in lp_columns:
        op.drop_column("learning_paths", "generation_duration_ms")
    if "knowledge_level" in lp_columns:
        op.drop_column("learning_paths", "knowledge_level")

    for table in (
        "research_metrics",
        "experiment_results",
        "knowledge_test_answers",
        "knowledge_test_attempts",
        "knowledge_test_questions",
    ):
        if inspector.has_table(table):
            op.drop_table(table)
