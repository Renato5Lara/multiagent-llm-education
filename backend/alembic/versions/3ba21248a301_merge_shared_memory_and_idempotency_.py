"""merge shared memory and idempotency lifecycle heads

Revision ID: 3ba21248a301
Revises: 0a1b2c3d4e5f, 1b2c3d4e5f6a
Create Date: 2026-05-25 23:15:27.628778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3ba21248a301'
down_revision: Union[str, Sequence[str], None] = ('0a1b2c3d4e5f', '1b2c3d4e5f6a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
