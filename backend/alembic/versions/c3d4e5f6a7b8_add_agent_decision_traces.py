"""add agent_decision_traces table for P0.3 Decision Trace system

Each agent invocation produces a structured AgentDecisionTrace stored here.
Chains of traces are linked by correlation_id (shared per swarm run) and
causation_id (previous agent's trace_id), enabling full reasoning auditability.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_decision_traces",

        # Primary key
        sa.Column("id", sa.String(36), primary_key=True),

        # Identity
        sa.Column("trace_id", sa.String(36), nullable=False),
        sa.Column("agent_id", sa.String(36), nullable=False),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("agent_type", sa.String(100), nullable=False),

        # Invocation context
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("context_key", sa.String(255), nullable=False),
        sa.Column("student_id", sa.String(36), nullable=False),
        sa.Column("course_id", sa.String(36), nullable=False),

        # Causal chain
        sa.Column("correlation_id", sa.String(36), nullable=True),
        sa.Column("causation_id", sa.String(36), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),

        # Inputs summary
        sa.Column("state_inputs", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "memory_records_queried",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        # Reasoning payload
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("reasoning_steps", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("dimensions", sa.JSON(), nullable=False, server_default="[]"),

        # Decision
        sa.Column("decision_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("output_keys", sa.JSON(), nullable=False, server_default="[]"),

        # Performance
        sa.Column("elapsed_ms", sa.Float(), nullable=False, server_default="0.0"),

        # Outcome
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error", sa.Text(), nullable=True),

        # Timestamps
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Unique constraint on trace_id
    op.create_unique_constraint(
        "uq_adt_trace_id",
        "agent_decision_traces",
        ["trace_id"],
    )

    # Indexes for efficient retrieval
    op.create_index("ix_adt_trace_id", "agent_decision_traces", ["trace_id"])
    op.create_index("ix_adt_correlation", "agent_decision_traces", ["correlation_id"])
    op.create_index("ix_adt_session", "agent_decision_traces", ["session_id"])
    op.create_index("ix_adt_context_key", "agent_decision_traces", ["context_key"])
    op.create_index(
        "ix_adt_student_agent",
        "agent_decision_traces",
        ["student_id", "agent_name"],
    )
    op.create_index(
        "ix_adt_causal_chain",
        "agent_decision_traces",
        ["correlation_id", "sequence"],
    )
    op.create_index("ix_adt_created_at", "agent_decision_traces", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_adt_created_at", table_name="agent_decision_traces")
    op.drop_index("ix_adt_causal_chain", table_name="agent_decision_traces")
    op.drop_index("ix_adt_student_agent", table_name="agent_decision_traces")
    op.drop_index("ix_adt_context_key", table_name="agent_decision_traces")
    op.drop_index("ix_adt_session", table_name="agent_decision_traces")
    op.drop_index("ix_adt_correlation", table_name="agent_decision_traces")
    op.drop_index("ix_adt_trace_id", table_name="agent_decision_traces")
    op.drop_constraint("uq_adt_trace_id", "agent_decision_traces", type_="unique")
    op.drop_table("agent_decision_traces")
