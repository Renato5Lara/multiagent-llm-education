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


TABLE_NAME = "shared_memory_records"
EXPECTED_COLUMNS = {
    "id",
    "voter_name",
    "student_id",
    "module_id",
    "memory_type",
    "key",
    "value",
    "confidence",
    "source_trace_id",
    "source_event_id",
    "parent_id",
    "version",
    "ttl_seconds",
    "metadata_json",
    "created_at",
    "updated_at",
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


def _has_unique_constraint(
    inspector: sa.Inspector,
    name: str,
    columns: list[str],
) -> bool:
    wanted = set(columns)
    for constraint in inspector.get_unique_constraints(TABLE_NAME):
        if constraint.get("name") == name:
            return True
        if set(constraint.get("column_names") or []) == wanted:
            return True
    return False


def _ensure_unique_constraint(inspector: sa.Inspector) -> None:
    columns = ["voter_name", "student_id", "module_id", "memory_type", "key"]
    if not _has_unique_constraint(inspector, "uq_shared_memory_voter_scope_key", columns):
        op.create_unique_constraint(
            "uq_shared_memory_voter_scope_key",
            TABLE_NAME,
            columns,
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        _validate_existing_table(inspector)
        _ensure_index(inspector, "ix_shared_memory_student_type", ["student_id", "memory_type"])
        _ensure_index(inspector, "ix_shared_memory_module_type", ["module_id", "memory_type"])
        _ensure_index(inspector, "ix_shared_memory_trace", ["source_trace_id"])
        _ensure_unique_constraint(inspector)
        return

    op.create_table(
        TABLE_NAME,
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
        TABLE_NAME,
        ["student_id", "memory_type"],
    )
    op.create_index(
        "ix_shared_memory_module_type",
        TABLE_NAME,
        ["module_id", "memory_type"],
    )
    op.create_index(
        "ix_shared_memory_trace",
        TABLE_NAME,
        ["source_trace_id"],
    )
    op.create_unique_constraint(
        "uq_shared_memory_voter_scope_key",
        TABLE_NAME,
        ["voter_name", "student_id", "module_id", "memory_type", "key"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    if _has_unique_constraint(
        inspector,
        "uq_shared_memory_voter_scope_key",
        ["voter_name", "student_id", "module_id", "memory_type", "key"],
    ):
        op.drop_constraint(
            "uq_shared_memory_voter_scope_key",
            TABLE_NAME,
            type_="unique",
        )

    if _has_index(inspector, "source_trace_id"):
        op.drop_index("ix_shared_memory_trace", table_name=TABLE_NAME)
    if _has_index(inspector, "module_id", "memory_type"):
        op.drop_index("ix_shared_memory_module_type", table_name=TABLE_NAME)
    if _has_index(inspector, "student_id", "memory_type"):
        op.drop_index("ix_shared_memory_student_type", table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
