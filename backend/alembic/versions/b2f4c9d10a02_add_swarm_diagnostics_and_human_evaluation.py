"""add_swarm_diagnostics_and_human_evaluation

Fase 2 del PoC `adaptation_swarm`: (a) diagnósticos del PSO por iteración/ciclo (columnas JSON nullable) y
(b) infraestructura de evaluación humana (SUS y panel de validación del gold): participantes con consentimiento,
respuestas SUS con restricciones 1–5 y valoraciones de celdas del gold. Las tablas se crean VACÍAS: no contienen
datos ni se generan; SUS y panel son PENDIENTE DE RECOLECCIÓN HUMANA.

Revision ID: b2f4c9d10a02
Revises: a17c0de5a001
Create Date: 2026-09-23 22:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2f4c9d10a02"
down_revision: Union[str, Sequence[str], None] = "a17c0de5a001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("swarm_iterations", sa.Column("diagnostics", sa.JSON))
    op.add_column("swarm_cycles", sa.Column("pso_diagnostics", sa.JSON))
    op.create_table(
        "sus_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("pseudonym", sa.String(40), nullable=False, unique=True),
        sa.Column("role", sa.String(30), nullable=False),
        sa.Column("years_experience", sa.Integer),
        sa.Column("consent", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("consent = true", name="ck_sus_participants_consent"),
        sa.CheckConstraint("role in ('docente_programacion','ingeniero_software')", name="ck_sus_participants_role"),
    )
    op.create_table(
        "sus_responses",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("participant_id", sa.String(36), sa.ForeignKey("sus_participants.id"), nullable=False),
        sa.Column("instrument_version", sa.String(40), nullable=False),
        sa.Column("task_script_version", sa.String(40), nullable=False),
        *[sa.Column(f"item_{i}", sa.Integer, nullable=False) for i in range(1, 11)],
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("participant_id", "instrument_version", name="uq_sus_responses_participant_instrument"),
        *[sa.CheckConstraint(f"item_{i} between 1 and 5", name=f"ck_sus_responses_item_{i}") for i in range(1, 11)],
    )
    op.create_table(
        "gold_panel_ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("participant_id", sa.String(36), sa.ForeignKey("sus_participants.id"), nullable=False),
        sa.Column("rule_version", sa.String(20), nullable=False),
        sa.Column("archetype", sa.String(40), nullable=False),
        sa.Column("difficulty", sa.String(40), nullable=False),
        sa.Column("agrees", sa.Boolean, nullable=False),
        sa.Column("rating", sa.Integer),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("participant_id", "rule_version", "archetype", "difficulty", name="uq_gold_panel_rating_cell"),
        sa.CheckConstraint("rating is null or rating between 1 and 5", name="ck_gold_panel_rating_range"),
    )


def downgrade() -> None:
    for t in ("gold_panel_ratings", "sus_responses", "sus_participants"):
        op.drop_table(t)
    op.drop_column("swarm_cycles", "pso_diagnostics")
    op.drop_column("swarm_iterations", "diagnostics")
