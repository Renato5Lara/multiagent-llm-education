"""add activation states to educational context

Revision ID: 7c8d9e0f1a2b
Revises: 6d7e8f9a0b1c
Create Date: 2026-05-27 02:30:00.000000

Adds FAILED, DEGRADED, PARTIAL, RECOVERING, INITIALIZING states
to the EducationalContextStatus enum, replacing the old ACTIVATING
value.

BUG-SWARM-003: ctx.status was set to ACTIVE even when swarm
initialization failed, causing false positive activation metrics,
invalid experiments, and corrupt diagnostics.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "7c8d9e0f1a2b"
down_revision: Union[str, Sequence[str], None] = "6d7e8f9a0b1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NEW_VALUES = [
    "initializing",
    "degraded",
    "failed",
    "partial",
    "recovering",
]

# Full value set of EducationalContextStatus in app/models/educational_context.py.
ALL_VALUES = [
    "pending",
    "initializing",
    "active",
    "degraded",
    "failed",
    "partial",
    "recovering",
    "suspended",
    "archived",
]


def upgrade() -> None:
    # The enum was historically created by Base.metadata.create_all() at app
    # startup (removed in 99e98b4), never by a migration. Fresh databases
    # built purely via Alembic therefore don't have it — create it here with
    # the full current value set before touching it.
    quoted = ", ".join(f"'{v}'" for v in ALL_VALUES)
    op.execute(
        sa.text(
            f"""
            DO $$ BEGIN
                CREATE TYPE educationalcontextstatus AS ENUM ({quoted});
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    # Databases where create_all already created the enum (old value set) only
    # need the new values appended. IF NOT EXISTS makes each statement a no-op
    # when the value is already present. Requires PostgreSQL >= 12 to run
    # inside Alembic's transaction.
    for val in NEW_VALUES:
        op.execute(
            sa.text(
                f"ALTER TYPE educationalcontextstatus ADD VALUE IF NOT EXISTS '{val}'"
            )
        )


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum.
    # The new values remain but are unused if we downgrade the application code.
    # This is a known limitation — downgrade is a no-op.
    pass
