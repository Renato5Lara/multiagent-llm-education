"""add_idempotency_lifecycle

Extiende la tabla idempotency_keys con lifecycle enterprise-grade:
  - status: pending | in_progress | completed | failed
  - event_type, aggregate_id, trace_id, causation_id
  - completed_at timestamp

Revision ID: 1b2c3d4e5f6a
Revises: 9a8b7c6d5e4f
Create Date: 2026-05-25 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1b2c3d4e5f6a"
down_revision: Union[str, Sequence[str], None] = "9a8b7c6d5e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -- Add lifecycle status column (with index) --
    op.add_column(
        "idempotency_keys",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
            index=True,
        ),
    )

    # -- Add event metadata columns --
    op.add_column(
        "idempotency_keys",
        sa.Column("event_type", sa.String(100), nullable=True),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column("aggregate_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column("trace_id", sa.String(36), nullable=True),
    )
    op.add_column(
        "idempotency_keys",
        sa.Column("causation_id", sa.String(36), nullable=True),
    )

    # -- Add completed_at timestamp --
    op.add_column(
        "idempotency_keys",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -- Backfill existing rows: response_status > 0 → completed, = 0 → in_progress --
    op.execute(
        "UPDATE idempotency_keys SET status = 'completed' "
        "WHERE response_status > 0"
    )
    op.execute(
        "UPDATE idempotency_keys SET status = 'in_progress' "
        "WHERE response_status = 0"
    )


def downgrade() -> None:
    op.drop_column("idempotency_keys", "completed_at")
    op.drop_column("idempotency_keys", "causation_id")
    op.drop_column("idempotency_keys", "trace_id")
    op.drop_column("idempotency_keys", "aggregate_id")
    op.drop_column("idempotency_keys", "event_type")
    op.drop_column("idempotency_keys", "status")
