"""add_concurrency_controls

Crea tabla idempotency_keys, agrega columnas version para optimistic
locking y unique constraints para upserts seguros.

Revision ID: 9a8b7c6d5e4f
Revises: 3a4b5c6d7e8f
Create Date: 2026-05-23 21:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, Sequence[str], None] = "3a4b5c6d7e8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- idempotency_keys --
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("response_status", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    # -- version columns for optimistic locking --
    op.add_column("student_memories", sa.Column("version", sa.Integer(),
                  nullable=False, server_default=sa.text("1")))
    op.add_column("learning_paths", sa.Column("version", sa.Integer(),
                  nullable=False, server_default=sa.text("1")))
    op.add_column("path_modules", sa.Column("version", sa.Integer(),
                  nullable=False, server_default=sa.text("1")))
    op.add_column("diagnostic_results", sa.Column("version", sa.Integer(),
                  nullable=False, server_default=sa.text("1")))

    # -- unique constraints for idempotent upserts --
    op.create_unique_constraint(
        "uq_student_memory_type_key",
        "student_memories",
        ["student_id", "memory_type", "key"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_student_memory_type_key", "student_memories", type_="unique")
    op.drop_column("diagnostic_results", "version")
    op.drop_column("path_modules", "version")
    op.drop_column("learning_paths", "version")
    op.drop_column("student_memories", "version")
    op.drop_table("idempotency_keys")
