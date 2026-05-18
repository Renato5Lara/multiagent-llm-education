"""initial_models

Revision ID: 83058a18afd3
Revises:
Create Date: 2026-05-17 14:50:58.551637

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "83058a18afd3"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE userrole AS ENUM ('ADMIN', 'DOCENTE', 'ESTUDIANTE', 'INVESTIGADOR');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE coursestatus AS ENUM ('BORRADOR', 'PUBLICADO', 'ARCHIVADO');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE resourcetype AS ENUM ('PDF', 'VIDEO', 'IMAGE', 'TEXT', 'DOCUMENT', 'AUDIO', 'GAME', 'INTERACTIVE');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE enrollmentstatus AS ENUM ('ACTIVO', 'COMPLETADO', 'ABANDONADO');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE competencytype AS ENUM ('institutional', 'career', 'course');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("ADMIN", "DOCENTE", "ESTUDIANTE", "INVESTIGADOR", name="userrole", create_type=False),
            nullable=False,
        ),
        sa.Column("institutional_code", sa.String(50), nullable=True),
        sa.Column("area", sa.String(100), nullable=True),
        sa.Column("current_cycle", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
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
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cycle", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("BORRADOR", "PUBLICADO", "ARCHIVADO", name="coursestatus", create_type=False),
            nullable=False,
        ),
        sa.Column("teacher_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "learning_objectives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    op.create_table(
        "resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_path", sa.String(512), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "resource_type",
            postgresql.ENUM("PDF", "VIDEO", "IMAGE", "TEXT", "DOCUMENT", "AUDIO", "GAME", "INTERACTIVE", name="resourcetype", create_type=False),
            nullable=False,
        ),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "resource_objectives",
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("resources.id"), primary_key=True),
        sa.Column("objective_id", sa.String(36), sa.ForeignKey("learning_objectives.id"), primary_key=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default=sa.text("1.0")),
    )

    op.create_table(
        "enrollments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column(
            "status",
            postgresql.ENUM("ACTIVO", "COMPLETADO", "ABANDONADO", name="enrollmentstatus", create_type=False),
            nullable=False,
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, index=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
    )

    op.create_table(
        "diagnostic_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=True),
        sa.Column("modality_scores", sa.JSON(), nullable=True),
        sa.Column("dominant_modality", sa.String(50), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("total_modules", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("completed_modules", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=True, server_default="active"),
    )

    op.create_table(
        "path_modules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("path_id", sa.String(36), sa.ForeignKey("learning_paths.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("status", sa.String(20), nullable=True, server_default="locked"),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("resources.id"), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "evaluation_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("module_id", sa.String(36), sa.ForeignKey("path_modules.id"), nullable=True),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Integer(), nullable=True),
        sa.Column("attempted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "competencies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "competency_type",
            postgresql.ENUM("institutional", "career", "course", name="competencytype", create_type=False),
            nullable=False,
        ),
        sa.Column("cycle", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "course_competencies",
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), primary_key=True),
        sa.Column("competency_id", sa.String(36), sa.ForeignKey("competencies.id"), primary_key=True),
    )

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("preferred_modalities", sa.JSON(), nullable=False),
        sa.Column("dominant_style", sa.String(50), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "student_progress",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("resources.id"), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percentage", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("student_progress")
    op.drop_table("student_profiles")
    op.drop_table("course_competencies")
    op.drop_table("competencies")
    op.drop_table("evaluation_attempts")
    op.drop_table("path_modules")
    op.drop_table("learning_paths")
    op.drop_table("diagnostic_results")
    op.drop_table("login_attempts")
    op.drop_table("audit_logs")
    op.drop_table("enrollments")
    op.drop_table("resource_objectives")
    op.drop_table("resources")
    op.drop_table("learning_objectives")
    op.drop_table("courses")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole CASCADE")
    op.execute("DROP TYPE IF EXISTS coursestatus CASCADE")
    op.execute("DROP TYPE IF EXISTS resourcetype CASCADE")
    op.execute("DROP TYPE IF EXISTS enrollmentstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS competencytype CASCADE")
