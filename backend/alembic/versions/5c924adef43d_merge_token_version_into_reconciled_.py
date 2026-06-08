"""merge token_version into reconciled schema

Revision ID: 5c924adef43d
Revises: 4c5d6e7f8a9b, 0b1c2d3e4f5a
Create Date: 2026-05-27 02:09:13.436049

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c924adef43d'
down_revision: Union[str, Sequence[str], None] = ('4c5d6e7f8a9b', '0b1c2d3e4f5a')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
