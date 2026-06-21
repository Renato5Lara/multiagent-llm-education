"""add engagement tables for 5E Engage phase

Cuatro tablas para el sistema de engagement adaptativo:
  - engagement_sessions     : una sesión por estudiante × módulo
  - engagement_resources    : recursos generados (¿Sabías que?, quiz, reto…)
  - engagement_events       : stream de eventos para métricas
  - engagement_interactions : detalle granular de cada interacción

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-06-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── engagement_sessions ──────────────────────────────────────────────────
    op.create_table(
        "engagement_sessions",

        sa.Column("id",          sa.String(36), primary_key=True),
        sa.Column("student_id",  sa.String(36), sa.ForeignKey("users.id"),        nullable=False),
        sa.Column("module_id",   sa.String(36), sa.ForeignKey("path_modules.id"), nullable=False),

        # Estado: pending | active | completed | skipped
        sa.Column("status",           sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("modality_profile", sa.String(20)),

        # Métricas
        sa.Column("resources_shown",       sa.Integer(), server_default="0"),
        sa.Column("resources_interacted",  sa.Integer(), server_default="0"),
        sa.Column("xp_earned",             sa.Integer(), server_default="0"),

        # Gamificación — lista JSON de slugs de insignias
        sa.Column("earned_badges", sa.JSON(), server_default="[]"),

        # Timestamps
        sa.Column("started_at",   sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_eng_session_student", "engagement_sessions", ["student_id"])
    op.create_index("ix_eng_session_module",  "engagement_sessions", ["module_id"])

    # ── engagement_resources ─────────────────────────────────────────────────
    op.create_table(
        "engagement_resources",

        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False),

        # Tipo controla qué card React se renderiza
        sa.Column("resource_type",    sa.String(40),   nullable=False),
        sa.Column("title",            sa.String(500),  nullable=False),
        sa.Column("content",          sa.String(2000), nullable=False),
        sa.Column("media_url",        sa.String(1000)),
        sa.Column("modality_target",  sa.String(20)),
        sa.Column("display_order",    sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_interactive",   sa.Boolean(), server_default="false"),

        # Carga específica por tipo (quiz options, challenge prompt, etc.)
        sa.Column("resource_metadata", sa.JSON(), server_default="{}"),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_eng_resource_session", "engagement_resources", ["session_id"])

    # ── engagement_events ────────────────────────────────────────────────────
    op.create_table(
        "engagement_events",

        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", sa.String(36),
                  sa.ForeignKey("engagement_resources.id", ondelete="SET NULL")),

        # Tipo: session_started | resource_viewed | quiz_answered | etc.
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("xp_delta",   sa.Integer(), server_default="0"),
        sa.Column("payload",    sa.JSON(),    server_default="{}"),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_eng_event_session", "engagement_events", ["session_id"])

    # ── engagement_interactions ──────────────────────────────────────────────
    op.create_table(
        "engagement_interactions",

        sa.Column("id",         sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36),
                  sa.ForeignKey("engagement_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("resource_id", sa.String(36),
                  sa.ForeignKey("engagement_resources.id", ondelete="CASCADE"), nullable=False),

        sa.Column("interaction_type",    sa.String(20), nullable=False),  # view|answer|submit|skip
        sa.Column("time_spent_seconds",  sa.Integer(),  server_default="0"),
        sa.Column("is_correct",          sa.Boolean()),                    # NULL = no evaluable
        sa.Column("response_data",       sa.JSON(),     server_default="{}"),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("ix_eng_interaction_session",  "engagement_interactions", ["session_id"])
    op.create_index("ix_eng_interaction_resource", "engagement_interactions", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_eng_interaction_resource", table_name="engagement_interactions")
    op.drop_index("ix_eng_interaction_session",  table_name="engagement_interactions")
    op.drop_table("engagement_interactions")

    op.drop_index("ix_eng_event_session", table_name="engagement_events")
    op.drop_table("engagement_events")

    op.drop_index("ix_eng_resource_session", table_name="engagement_resources")
    op.drop_table("engagement_resources")

    op.drop_index("ix_eng_session_module",  table_name="engagement_sessions")
    op.drop_index("ix_eng_session_student", table_name="engagement_sessions")
    op.drop_table("engagement_sessions")
