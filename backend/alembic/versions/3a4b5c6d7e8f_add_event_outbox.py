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


TABLE_NAME = "event_outbox"
EXPECTED_COLUMNS = {
    "id",
    "event_type",
    "aggregate_id",
    "correlation_id",
    "causation_id",
    "payload",
    "status",
    "retry_count",
    "max_retries",
    "created_at",
    "updated_at",
    "published_at",
    "last_error",
}


def _validate_existing_table(inspector: sa.Inspector) -> None:
    columns = {column["name"] for column in inspector.get_columns(TABLE_NAME)}
    missing = sorted(EXPECTED_COLUMNS - columns)
    if missing:
        raise RuntimeError(
            f"Existing {TABLE_NAME} table is not compatible with revision "
            f"{revision}; missing columns: {', '.join(missing)}."
        )


def _has_index(inspector: sa.Inspector, *column_names: str) -> bool:
    wanted = set(column_names)
    return any(
        set(index.get("column_names") or []) == wanted
        for index in inspector.get_indexes(TABLE_NAME)
    )


def _ensure_index(inspector: sa.Inspector, name: str, columns: list[str]) -> None:
    if not _has_index(inspector, *columns):
        op.create_index(name, TABLE_NAME, columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        _validate_existing_table(inspector)
        _ensure_index(inspector, "ix_event_outbox_event_type", ["event_type"])
        _ensure_index(inspector, "ix_event_outbox_aggregate_id", ["aggregate_id"])
        _ensure_index(inspector, "ix_event_outbox_correlation_id", ["correlation_id"])
        _ensure_index(inspector, "ix_event_outbox_status", ["status"])
        _ensure_index(inspector, "ix_event_outbox_pending", ["status", "retry_count"])
        return

    op.create_table(
        TABLE_NAME,
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
        TABLE_NAME,
        ["status", "retry_count"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    if _has_index(inspector, "status", "retry_count"):
        op.drop_index("ix_event_outbox_pending", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
