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


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in _columns(inspector, table_name)


def _validate_table_columns(
    inspector: sa.Inspector,
    table_name: str,
    expected_columns: set[str],
) -> None:
    columns = _columns(inspector, table_name)
    missing = sorted(expected_columns - columns)
    if missing:
        raise RuntimeError(
            f"Existing {table_name} table is not compatible with revision "
            f"{revision}; missing columns: {', '.join(missing)}."
        )


def _has_unique_constraint(
    inspector: sa.Inspector,
    table_name: str,
    name: str,
    columns: list[str],
) -> bool:
    wanted = set(columns)
    for constraint in inspector.get_unique_constraints(table_name):
        if constraint.get("name") == name:
            return True
        if set(constraint.get("column_names") or []) == wanted:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # -- idempotency_keys --
    if inspector.has_table("idempotency_keys"):
        _validate_table_columns(
            inspector,
            "idempotency_keys",
            {"id", "key", "response_status", "response_body", "created_at", "expires_at"},
        )
    else:
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
    for table_name in (
        "student_memories",
        "learning_paths",
        "path_modules",
        "diagnostic_results",
    ):
        if not _has_column(inspector, table_name, "version"):
            op.add_column(
                table_name,
                sa.Column(
                    "version",
                    sa.Integer(),
                    nullable=False,
                    server_default=sa.text("1"),
                ),
            )

    # -- unique constraints for idempotent upserts --
    inspector = sa.inspect(bind)
    if not _has_unique_constraint(
        inspector,
        "student_memories",
        "uq_student_memory_type_key",
        ["student_id", "memory_type", "key"],
    ):
        op.create_unique_constraint(
            "uq_student_memory_type_key",
            "student_memories",
            ["student_id", "memory_type", "key"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("student_memories") and _has_unique_constraint(
        inspector,
        "student_memories",
        "uq_student_memory_type_key",
        ["student_id", "memory_type", "key"],
    ):
        op.drop_constraint("uq_student_memory_type_key", "student_memories", type_="unique")

    for table_name in (
        "diagnostic_results",
        "path_modules",
        "learning_paths",
        "student_memories",
    ):
        if inspector.has_table(table_name) and _has_column(inspector, table_name, "version"):
            op.drop_column(table_name, "version")

    if inspector.has_table("idempotency_keys"):
        op.drop_table("idempotency_keys")
