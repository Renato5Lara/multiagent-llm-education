"""add_event_outbox

Crea la tabla event_outbox para el Outbox Pattern.
Los eventos se persisten en la misma transaccion que los datos de negocio.

Revision ID: 3a4b5c6d7e8f
Revises: 8b9c0d1e2f3a
Create Date: 2026-05-23 20:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3a4b5c6d7e8f"
down_revision: Union[str, Sequence[str], None] = "8b9c0d1e2f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_outbox",
        sa.Column("id", sa.String(36), primary_key=True),

        sa.Column("event_type", sa.String(100), nullable=False, index=True),
        sa.Column("aggregate_id", sa.String(36), nullable=False, index=True),

        sa.Column("correlation_id", sa.String(36), nullable=False, index=True),
        sa.Column("causation_id", sa.String(36), nullable=True),

        sa.Column("payload", sa.JSON(), nullable=False),

        sa.Column("status", sa.String(20), nullable=False, index=True,
                  server_default=sa.text("'pending'")),
        sa.Column("retry_count", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("max_retries", sa.Integer(), nullable=False,
                  server_default=sa.text("3")),

        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
    )

    op.create_index(
        "ix_event_outbox_pending",
        "event_outbox",
        ["status", "retry_count"],
    )


def downgrade() -> None:
    op.drop_index("ix_event_outbox_pending", table_name="event_outbox")
    op.drop_table("event_outbox")
