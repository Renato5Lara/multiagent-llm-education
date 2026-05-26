"""add_course_prerequisite

Revision ID: 6a7b8c9d0e1f
Revises: 83058a18afd3
Create Date: 2026-05-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6a7b8c9d0e1f"
down_revision: Union[str, Sequence[str], None] = "83058a18afd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "course_prerequisites"

EXPECTED_COLUMNS = {
    "id": {"nullable": False},
    "course_id": {"nullable": False},
    "prerequisite_course_id": {"nullable": False},
    "created_at": {"nullable": False},
}


def _column_map(inspector: sa.Inspector) -> dict[str, dict]:
    return {col["name"]: col for col in inspector.get_columns(TABLE_NAME)}


def _validate_existing_table(inspector: sa.Inspector) -> None:
    columns = _column_map(inspector)
    missing = sorted(set(EXPECTED_COLUMNS) - set(columns))
    if missing:
        raise RuntimeError(
            f"Existing {TABLE_NAME} table is not compatible with revision "
            f"{revision}; missing columns: {', '.join(missing)}. "
            "Fix the schema manually or run a dedicated reconciliation migration."
        )

    nullable_mismatches = [
        name
        for name, expected in EXPECTED_COLUMNS.items()
        if columns[name].get("nullable") != expected["nullable"]
    ]
    if nullable_mismatches:
        raise RuntimeError(
            f"Existing {TABLE_NAME} table has incompatible nullable settings "
            f"for columns: {', '.join(sorted(nullable_mismatches))}."
        )


def _has_index(inspector: sa.Inspector, *column_names: str) -> bool:
    wanted = set(column_names)
    for index in inspector.get_indexes(TABLE_NAME):
        if set(index.get("column_names") or []) == wanted:
            return True
    return False


def _has_fk(inspector: sa.Inspector, constrained_column: str) -> bool:
    for fk in inspector.get_foreign_keys(TABLE_NAME):
        if (
            fk.get("referred_table") == "courses"
            and fk.get("constrained_columns") == [constrained_column]
            and fk.get("referred_columns") == ["id"]
        ):
            return True
    return False


def _ensure_indexes_and_fks(inspector: sa.Inspector) -> None:
    if not _has_index(inspector, "course_id"):
        op.create_index(
            "ix_course_prerequisites_course_id",
            TABLE_NAME,
            ["course_id"],
        )

    if not _has_index(inspector, "prerequisite_course_id"):
        op.create_index(
            "ix_course_prerequisites_prerequisite_course_id",
            TABLE_NAME,
            ["prerequisite_course_id"],
        )

    if not _has_fk(inspector, "course_id"):
        op.create_foreign_key(
            "fk_course_prerequisites_course_id_courses",
            TABLE_NAME,
            "courses",
            ["course_id"],
            ["id"],
        )

    if not _has_fk(inspector, "prerequisite_course_id"):
        op.create_foreign_key(
            "fk_course_prerequisites_prerequisite_course_id_courses",
            TABLE_NAME,
            "courses",
            ["prerequisite_course_id"],
            ["id"],
        )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        _validate_existing_table(inspector)
        _ensure_indexes_and_fks(inspector)
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("course_id", sa.String(36), nullable=False),
        sa.Column("prerequisite_course_id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name="fk_course_prerequisites_course_id_courses",
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_course_id"],
            ["courses.id"],
            name="fk_course_prerequisites_prerequisite_course_id_courses",
        ),
    )
    op.create_index(
        "ix_course_prerequisites_course_id",
        TABLE_NAME,
        ["course_id"],
    )
    op.create_index(
        "ix_course_prerequisites_prerequisite_course_id",
        TABLE_NAME,
        ["prerequisite_course_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    op.drop_table(TABLE_NAME)
