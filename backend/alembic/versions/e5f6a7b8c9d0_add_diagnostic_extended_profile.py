"""Add secondary_modality, prior_knowledge and confidence to diagnostic/profile

New columns:
  diagnostic_results: secondary_modality, prior_knowledge_level, known_topics, confidence
  student_profiles:   secondary_modality

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-29
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("diagnostic_results", sa.Column("secondary_modality", sa.String(50), nullable=True))
    op.add_column("diagnostic_results", sa.Column("prior_knowledge_level", sa.String(50), nullable=True))
    op.add_column("diagnostic_results", sa.Column("known_topics", sa.JSON(), nullable=True))
    op.add_column("diagnostic_results", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("student_profiles", sa.Column("secondary_modality", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("student_profiles", "secondary_modality")
    op.drop_column("diagnostic_results", "confidence")
    op.drop_column("diagnostic_results", "known_topics")
    op.drop_column("diagnostic_results", "prior_knowledge_level")
    op.drop_column("diagnostic_results", "secondary_modality")
