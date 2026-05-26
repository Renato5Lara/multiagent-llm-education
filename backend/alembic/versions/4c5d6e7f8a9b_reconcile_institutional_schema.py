"""reconcile_institutional_schema

Formalizes tables and columns that were previously created by
Base.metadata.create_all() during application startup.

Revision ID: 4c5d6e7f8a9b
Revises: 3ba21248a301
Create Date: 2026-05-25 23:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4c5d6e7f8a9b"
down_revision: Union[str, Sequence[str], None] = "3ba21248a301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EXPECTED_TABLE_COLUMNS = {
    "institutional_courses": {
        "id",
        "code",
        "name",
        "credits",
        "cycle",
        "hours_theory",
        "hours_practice",
        "hours_lab",
        "competencies",
        "created_at",
    },
    "institutional_course_prerequisites": {
        "course_id",
        "prerequisite_id",
    },
    "teacher_assignments": {
        "id",
        "teacher_id",
        "institutional_course_id",
        "created_at",
    },
}


def _columns(inspector: sa.Inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return column_name in _columns(inspector, table_name)


def _validate_existing_table(inspector: sa.Inspector, table_name: str) -> None:
    missing = sorted(EXPECTED_TABLE_COLUMNS[table_name] - _columns(inspector, table_name))
    if missing:
        raise RuntimeError(
            f"Existing {table_name} table is not compatible with revision "
            f"{revision}; missing columns: {', '.join(missing)}."
        )


def _has_index(inspector: sa.Inspector, table_name: str, *column_names: str) -> bool:
    wanted = set(column_names)
    return any(
        set(index.get("column_names") or []) == wanted
        for index in inspector.get_indexes(table_name)
    )


def _ensure_index(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: list[str],
    unique: bool = False,
) -> None:
    if not _has_index(inspector, table_name, *columns):
        op.create_index(index_name, table_name, columns, unique=unique)


def _has_fk(
    inspector: sa.Inspector,
    table_name: str,
    constrained_column: str,
    referred_table: str,
) -> bool:
    for fk in inspector.get_foreign_keys(table_name):
        if (
            fk.get("referred_table") == referred_table
            and fk.get("constrained_columns") == [constrained_column]
            and fk.get("referred_columns") == ["id"]
        ):
            return True
    return False


def _ensure_fk(
    inspector: sa.Inspector,
    table_name: str,
    constraint_name: str,
    constrained_column: str,
    referred_table: str,
) -> None:
    if not _has_fk(inspector, table_name, constrained_column, referred_table):
        op.create_foreign_key(
            constraint_name,
            table_name,
            referred_table,
            [constrained_column],
            ["id"],
        )


def _ensure_institutional_courses(inspector: sa.Inspector) -> None:
    table_name = "institutional_courses"
    if inspector.has_table(table_name):
        _validate_existing_table(inspector, table_name)
    else:
        op.create_table(
            table_name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("credits", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("cycle", sa.Integer(), nullable=False),
            sa.Column("hours_theory", sa.Integer(), nullable=True),
            sa.Column("hours_practice", sa.Integer(), nullable=True),
            sa.Column("hours_lab", sa.Integer(), nullable=True),
            sa.Column("competencies", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
    inspector = sa.inspect(op.get_bind())
    _ensure_index(inspector, table_name, "ix_institutional_courses_code", ["code"], unique=True)
    _ensure_index(inspector, table_name, "ix_institutional_courses_cycle", ["cycle"])


def _ensure_institutional_course_prerequisites(inspector: sa.Inspector) -> None:
    table_name = "institutional_course_prerequisites"
    if inspector.has_table(table_name):
        _validate_existing_table(inspector, table_name)
    else:
        op.create_table(
            table_name,
            sa.Column("course_id", sa.String(36), nullable=False),
            sa.Column("prerequisite_id", sa.String(36), nullable=False),
            sa.PrimaryKeyConstraint("course_id", "prerequisite_id"),
            sa.ForeignKeyConstraint(
                ["course_id"],
                ["institutional_courses.id"],
                name="fk_institutional_course_prereq_course",
            ),
            sa.ForeignKeyConstraint(
                ["prerequisite_id"],
                ["institutional_courses.id"],
                name="fk_institutional_course_prereq_prerequisite",
            ),
        )
    inspector = sa.inspect(op.get_bind())
    _ensure_fk(
        inspector,
        table_name,
        "fk_institutional_course_prereq_course",
        "course_id",
        "institutional_courses",
    )
    _ensure_fk(
        inspector,
        table_name,
        "fk_institutional_course_prereq_prerequisite",
        "prerequisite_id",
        "institutional_courses",
    )


def _ensure_teacher_assignments(inspector: sa.Inspector) -> None:
    table_name = "teacher_assignments"
    if inspector.has_table(table_name):
        _validate_existing_table(inspector, table_name)
    else:
        op.create_table(
            table_name,
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("teacher_id", sa.String(36), nullable=False),
            sa.Column("institutional_course_id", sa.String(36), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(
                ["teacher_id"],
                ["users.id"],
                name="fk_teacher_assignments_teacher",
            ),
            sa.ForeignKeyConstraint(
                ["institutional_course_id"],
                ["institutional_courses.id"],
                name="fk_teacher_assignments_institutional_course",
            ),
        )
    inspector = sa.inspect(op.get_bind())
    _ensure_index(inspector, table_name, "ix_teacher_assignments_teacher_id", ["teacher_id"])
    _ensure_index(
        inspector,
        table_name,
        "ix_teacher_assignments_institutional_course_id",
        ["institutional_course_id"],
    )
    _ensure_fk(inspector, table_name, "fk_teacher_assignments_teacher", "teacher_id", "users")
    _ensure_fk(
        inspector,
        table_name,
        "fk_teacher_assignments_institutional_course",
        "institutional_course_id",
        "institutional_courses",
    )


def _ensure_courses_columns(inspector: sa.Inspector) -> None:
    table_name = "courses"
    if not _has_column(inspector, table_name, "institutional_course_id"):
        op.add_column(
            table_name,
            sa.Column("institutional_course_id", sa.String(36), nullable=True),
        )

    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, table_name, "is_institutional"):
        op.add_column(
            table_name,
            sa.Column(
                "is_institutional",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    inspector = sa.inspect(op.get_bind())
    course_columns = {column["name"]: column for column in inspector.get_columns(table_name)}
    if course_columns["teacher_id"].get("nullable") is False:
        op.alter_column(
            table_name,
            "teacher_id",
            existing_type=sa.String(36),
            nullable=True,
        )

    inspector = sa.inspect(op.get_bind())
    _ensure_index(
        inspector,
        table_name,
        "ix_courses_institutional_course_id",
        ["institutional_course_id"],
    )
    _ensure_fk(
        inspector,
        table_name,
        "fk_courses_institutional_course",
        "institutional_course_id",
        "institutional_courses",
    )


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    _ensure_institutional_courses(inspector)
    inspector = sa.inspect(op.get_bind())
    _ensure_institutional_course_prerequisites(inspector)
    inspector = sa.inspect(op.get_bind())
    _ensure_teacher_assignments(inspector)
    inspector = sa.inspect(op.get_bind())
    _ensure_courses_columns(inspector)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if inspector.has_table("courses"):
        if _has_fk(inspector, "courses", "institutional_course_id", "institutional_courses"):
            op.drop_constraint("fk_courses_institutional_course", "courses", type_="foreignkey")
        if _has_index(inspector, "courses", "institutional_course_id"):
            op.drop_index("ix_courses_institutional_course_id", table_name="courses")
        if _has_column(inspector, "courses", "is_institutional"):
            op.drop_column("courses", "is_institutional")
        if _has_column(inspector, "courses", "institutional_course_id"):
            op.drop_column("courses", "institutional_course_id")
        op.alter_column(
            "courses",
            "teacher_id",
            existing_type=sa.String(36),
            nullable=False,
        )

    inspector = sa.inspect(op.get_bind())
    for table_name in (
        "teacher_assignments",
        "institutional_course_prerequisites",
        "institutional_courses",
    ):
        if inspector.has_table(table_name):
            op.drop_table(table_name)
