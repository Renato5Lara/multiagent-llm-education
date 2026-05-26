"""add_memory_and_knowledge_graph

Revision ID: 8b9c0d1e2f3a
Revises: 6a7b8c9d0e1f
Create Date: 2026-05-23 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "8b9c0d1e2f3a"
down_revision: Union[str, Sequence[str], None] = "6a7b8c9d0e1f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "student_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("memory_type", sa.String(50), nullable=False, index=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "conversation_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("course_id", sa.String(36), sa.ForeignKey("courses.id"), nullable=True, index=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "weakness_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("detection_count", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "strength_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("node_type", sa.String(50), nullable=False, index=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("external_id", sa.String(36), nullable=True, index=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "knowledge_edges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_id", sa.String(36), sa.ForeignKey("knowledge_nodes.id"), nullable=False, index=True),
        sa.Column("target_id", sa.String(36), sa.ForeignKey("knowledge_nodes.id"), nullable=False, index=True),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default=sa.text("1.0")),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("knowledge_edges")
    op.drop_table("knowledge_nodes")
    op.drop_table("strength_records")
    op.drop_table("weakness_records")
    op.drop_table("conversation_messages")
    op.drop_table("student_memories")
