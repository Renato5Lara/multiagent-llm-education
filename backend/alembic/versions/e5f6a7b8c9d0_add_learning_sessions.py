"""add_learning_sessions (Misión Activa — primera migración real de la tabla)

La tabla existía solo en el modelo (era create_all, schema drift documentado).
La Misión Activa la refunda como dueña del estado {snapshot, cursor, evidencia},
por lo que necesita existir en toda base gestionada por Alembic. Guarded: si un
entorno ya la tiene (create_all histórico), no se toca.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-06 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("learning_sessions"):
        op.create_table(
            "learning_sessions",
            sa.Column("id", sa.String(), primary_key=True),
            sa.Column("student_id", sa.String(), sa.ForeignKey("users.id"), nullable=False, index=True),
            sa.Column("course_id", sa.String(), sa.ForeignKey("courses.id"), nullable=False, index=True),
            sa.Column("module_id", sa.String(), sa.ForeignKey("path_modules.id"), nullable=True),
            sa.Column("enrollment_id", sa.String(), sa.ForeignKey("enrollments.id"), nullable=True),
            sa.Column("status", sa.String(), nullable=True, index=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("duration_minutes", sa.Float(), nullable=True),
            sa.Column("swarm_activated", sa.String(), nullable=True),
            sa.Column("context_key", sa.String(), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("learning_sessions"):
        op.drop_table("learning_sessions")
