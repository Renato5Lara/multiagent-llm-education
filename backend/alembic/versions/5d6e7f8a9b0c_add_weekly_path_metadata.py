"""add_weekly_path_metadata

Revision ID: 5d6e7f8a9b0c
Revises: 4c5d6e7f8a9b
Create Date: 2026-05-31 17:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5d6e7f8a9b0c"
down_revision: Union[str, Sequence[str], None] = "4c5d6e7f8a9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _has_index(inspector: sa.Inspector, table_name: str, *column_names: str) -> bool:
    wanted = set(column_names)
    return any(
        set(index.get("column_names") or []) == wanted
        for index in inspector.get_indexes(table_name)
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, "path_modules", "week_number"):
        op.add_column("path_modules", sa.Column("week_number", sa.Integer(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    if not _has_index(inspector, "path_modules", "week_number"):
        op.create_index("ix_path_modules_week_number", "path_modules", ["week_number"])


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_index(inspector, "path_modules", "week_number"):
        op.drop_index("ix_path_modules_week_number", table_name="path_modules")
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, "path_modules", "week_number"):
        op.drop_column("path_modules", "week_number")
