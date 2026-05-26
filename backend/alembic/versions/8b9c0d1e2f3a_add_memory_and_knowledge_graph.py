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


EXPECTED_COLUMNS = {
    "student_memories": {
        "id", "student_id", "memory_type", "key", "value", "score",
        "metadata_json", "created_at", "updated_at",
    },
    "conversation_messages": {
        "id", "student_id", "course_id", "role", "content",
        "metadata_json", "created_at",
    },
    "weakness_records": {
        "id", "student_id", "topic", "description", "bloom_level",
        "detection_count", "last_detected_at", "resolved", "created_at",
    },
    "strength_records": {
        "id", "student_id", "topic", "description", "bloom_level", "created_at",
    },
    "knowledge_nodes": {
        "id", "node_type", "label", "description", "external_id",
        "metadata_json", "created_at",
    },
    "knowledge_edges": {
        "id", "source_id", "target_id", "relationship_type", "weight",
        "metadata_json", "created_at",
    },
}


def _existing_table_is_compatible(inspector: sa.Inspector, table_name: str) -> bool:
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    missing = sorted(EXPECTED_COLUMNS[table_name] - columns)
    if missing:
        raise RuntimeError(
            f"Existing {table_name} table is not compatible with revision "
            f"{revision}; missing columns: {', '.join(missing)}."
        )
    return True


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    if inspector.has_table(table_name):
        _existing_table_is_compatible(inspector, table_name)
        return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _table_exists(inspector, "student_memories"):
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
    if not _table_exists(inspector, "conversation_messages"):
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
    if not _table_exists(inspector, "weakness_records"):
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
    if not _table_exists(inspector, "strength_records"):
        op.create_table(
        "strength_records",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("topic", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("bloom_level", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _table_exists(inspector, "knowledge_nodes"):
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
    if not _table_exists(inspector, "knowledge_edges"):
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name in (
        "knowledge_edges",
        "knowledge_nodes",
        "strength_records",
        "weakness_records",
        "conversation_messages",
        "student_memories",
    ):
        if inspector.has_table(table_name):
            op.drop_table(table_name)
