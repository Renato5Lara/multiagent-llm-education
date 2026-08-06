"""drop agent_decision_traces table — orphaned infrastructure (Ficha 04
legacy retirement, ADR-0011 criterion)

Sesión 5 Frente B, Paso 4 (docs/bug_reports/tech_debt/2026-08-05_SESION5_
FRENTE_B_PASO3_clasificacion.md): its only writer (TraceStore) was
already removed in Ficha 04 (ADR-0011 retiro físico de BaseAgent/
SwarmOrchestrator). Verified in Paso 2 with 0 rows, no feature flag
gating it, no pending migration, and no reservation by RFC-0007
(the observability system that was actually built uses a completely
different data model: runtime_transitions/runtime_sessions/
runtime_blobs). `downgrade()` mirrors c3d4e5f6a7b8_add_agent_decision_
traces.py exactly, so this is fully reversible if ever needed.

Revision ID: 3a1a6681df05
Revises: f3a4b5c6d7e8
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3a1a6681df05"
down_revision: Union[str, Sequence[str], None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_adt_created_at", table_name="agent_decision_traces")
    op.drop_index("ix_adt_causal_chain", table_name="agent_decision_traces")
    op.drop_index("ix_adt_student_agent", table_name="agent_decision_traces")
    op.drop_index("ix_adt_context_key", table_name="agent_decision_traces")
    op.drop_index("ix_adt_session", table_name="agent_decision_traces")
    op.drop_index("ix_adt_correlation", table_name="agent_decision_traces")
    op.drop_index("ix_adt_trace_id", table_name="agent_decision_traces")
    op.drop_constraint("uq_adt_trace_id", "agent_decision_traces", type_="unique")
    op.drop_table("agent_decision_traces")


def downgrade() -> None:
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

    op.create_unique_constraint(
        "uq_adt_trace_id",
        "agent_decision_traces",
        ["trace_id"],
    )

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
