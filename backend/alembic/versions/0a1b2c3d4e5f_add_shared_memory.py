"""add_shared_memory

Crea la tabla shared_memory_records para Shared Collective Memory.

Revision ID: 0a1b2c3d4e5f
Revises: 9a8b7c6d5e4f
Create Date: 2026-05-23 23:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0a1b2c3d4e5f"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shared_memory_records",
        sa.Column("id", sa.String(36), primary_key=True),

        sa.Column("voter_name", sa.String(100), nullable=False, index=True),

        sa.Column("student_id", sa.String(36), nullable=True, index=True),
        sa.Column("module_id", sa.String(36), nullable=True, index=True),

        sa.Column("memory_type", sa.String(50), nullable=False, index=True),
        sa.Column("key", sa.String(255), nullable=False),

        sa.Column("value", sa.JSON(), nullable=False),

        sa.Column("confidence", sa.Float(), nullable=False,
                  server_default=sa.text("1.0")),

        sa.Column("source_trace_id", sa.String(36), nullable=True),
        sa.Column("source_event_id", sa.String(36), nullable=True),
        sa.Column("parent_id", sa.String(36), nullable=True),

        sa.Column("version", sa.Integer(), nullable=False,
                  server_default=sa.text("1")),

        sa.Column("ttl_seconds", sa.Integer(), nullable=True),

        sa.Column("metadata_json", sa.JSON(), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )

    op.create_index(
        "ix_shared_memory_student_type",
        "shared_memory_records",
        ["student_id", "memory_type"],
    )
    op.create_index(
        "ix_shared_memory_module_type",
        "shared_memory_records",
        ["module_id", "memory_type"],
    )
    op.create_index(
        "ix_shared_memory_trace",
        "shared_memory_records",
        ["source_trace_id"],
    )
    op.create_unique_constraint(
        "uq_shared_memory_voter_scope_key",
        "shared_memory_records",
        ["voter_name", "student_id", "module_id", "memory_type", "key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_shared_memory_voter_scope_key",
        "shared_memory_records",
        type_="unique",
    )
    op.drop_index("ix_shared_memory_trace", table_name="shared_memory_records")
    op.drop_index("ix_shared_memory_module_type", table_name="shared_memory_records")
    op.drop_index("ix_shared_memory_student_type", table_name="shared_memory_records")
    op.drop_table("shared_memory_records")
