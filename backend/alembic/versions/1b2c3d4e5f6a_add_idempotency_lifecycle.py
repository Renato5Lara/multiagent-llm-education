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


TABLE_NAME = "idempotency_keys"


def _has_column(inspector: sa.Inspector, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def _add_column_if_missing(inspector: sa.Inspector, column: sa.Column) -> None:
    if not _has_column(inspector, column.name):
        op.add_column(TABLE_NAME, column)


def _has_index(inspector: sa.Inspector, *column_names: str) -> bool:
    wanted = set(column_names)
    return any(
        set(index.get("column_names") or []) == wanted
        for index in inspector.get_indexes(TABLE_NAME)
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        raise RuntimeError(
            f"{TABLE_NAME} must exist before applying revision {revision}."
        )

    # -- Add lifecycle status column (with index) --
    _add_column_if_missing(
        inspector,
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
    )
    inspector = sa.inspect(bind)
    if not _has_index(inspector, "status"):
        op.create_index("ix_idempotency_keys_status", TABLE_NAME, ["status"])

    # -- Add event metadata columns --
    _add_column_if_missing(
        inspector,
        sa.Column("event_type", sa.String(100), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        sa.Column("aggregate_id", sa.String(36), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        sa.Column("trace_id", sa.String(36), nullable=True),
    )
    _add_column_if_missing(
        inspector,
        sa.Column("causation_id", sa.String(36), nullable=True),
    )

    # -- Add completed_at timestamp --
    _add_column_if_missing(
        inspector,
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    if _has_index(inspector, "status"):
        op.drop_index("ix_idempotency_keys_status", table_name=TABLE_NAME)

    for column_name in (
        "completed_at",
        "causation_id",
        "trace_id",
        "aggregate_id",
        "event_type",
        "status",
    ):
        inspector = sa.inspect(bind)
        if _has_column(inspector, column_name):
            op.drop_column(TABLE_NAME, column_name)
