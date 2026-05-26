"""add_course_prerequisite

Revision ID: 6a7b8c9d0e1f
Revises: 83058a18afd3
Create Date: 2026-05-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "6a7b8c9d0e1f"
down_revision: Union[str, Sequence[str], None] = "83058a18afd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "course_prerequisites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("prerequisite_course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("course_prerequisites")
