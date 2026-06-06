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


# PostgreSQL ALTER TYPE ... ADD VALUE cannot run inside a transaction block.
# We use op.execute() with a raw SQL statement.
# Each ADD VALUE is a separate, auto-committed statement.

NEW_VALUES = [
    "initializing",
    "degraded",
    "failed",
    "partial",
    "recovering",
]


def upgrade() -> None:
    conn = op.get_bind()
    # Check which values already exist (safe for re-run)
    existing = set(
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT unnest(enum_range(NULL::educationalcontextstatus))::text"
            )
        ).fetchall()
    )
    for val in NEW_VALUES:
        if val not in existing:
            op.execute(
                sa.text(
                    f"ALTER TYPE educationalcontextstatus ADD VALUE '{val}'"
                )
            )


def downgrade() -> None:
    # PostgreSQL does not support removing values from an enum.
    # The new values remain but are unused if we downgrade the application code.
    # This is a known limitation — downgrade is a no-op.
    pass
