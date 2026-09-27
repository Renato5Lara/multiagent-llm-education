"""widen_rule_version_and_add_archetype_panel

Respuestas del asesor 2026-09-26 (P4, R5): (a) la `rule_version` OFICIAL de gold-v2 (gold + inclusión + agregación + protocolo del panel, p. ej. `gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2`,
57 caracteres) no cabe en `String(20)`: se ensanchan `gold_panel_ratings.rule_version` y `swarm_profiles.gold_rule_version` a 80 (operación no destructiva: ningún dato histórico se pierde ni se modifica);
(b) tabla NUEVA `gold_panel_archetype_ratings` para el juicio del panel por ARQUETIPO (Aprobar/Rechazar el conjunto completo). Se crea VACÍA: sin datos ni valoraciones (votos Aprobar/Rechazar por evaluador; la matriz absoluta, AC1 y la decisión se derivan de ellos y se exportan). `gold_panel_ratings` (gold-v1,
20 celdas) se conserva intacta para el historial.

Revision ID: c3a91d27e5f0
Revises: b2f4c9d10a02
Create Date: 2026-09-26 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3a91d27e5f0"
down_revision: Union[str, Sequence[str], None] = "b2f4c9d10a02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("gold_panel_ratings", "rule_version", existing_type=sa.String(20), type_=sa.String(80), existing_nullable=False)
    op.alter_column("swarm_profiles", "gold_rule_version", existing_type=sa.String(20), type_=sa.String(80), existing_nullable=False)
    op.create_table(
        "gold_panel_archetype_ratings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("participant_id", sa.String(36), sa.ForeignKey("sus_participants.id"), nullable=False),
        sa.Column("rule_version", sa.String(80), nullable=False),
        sa.Column("archetype", sa.String(40), nullable=False),
        sa.Column("approves", sa.Boolean, nullable=False),
        sa.Column("comment", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("participant_id", "rule_version", "archetype", name="uq_gold_panel_archetype_rating"),
    )


def downgrade() -> None:
    # Reducir a 20 fallaría (PostgreSQL) si ya existen versiones más largas: el retroceso solo es seguro antes de registrar datos de gold-v2.
    op.drop_table("gold_panel_archetype_ratings")
    op.alter_column("swarm_profiles", "gold_rule_version", existing_type=sa.String(80), type_=sa.String(20), existing_nullable=False)
    op.alter_column("gold_panel_ratings", "rule_version", existing_type=sa.String(80), type_=sa.String(20), existing_nullable=False)
