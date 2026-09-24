"""add_experiment_cmg_results (P2 — persistencia del experimento CMG)

Tabla aditiva y aislada para la Iteración de Investigación "efecto del
mecanismo multiagente en la adaptación de contenido multimodal
(CMG)". Una fila por (Concept × condición: "experimental"/"control").
No afecta ninguna tabla existente, no se consume desde el flujo
productivo del estudiante — solo desde
`backend/scripts/experimento_cmg_runner.py`.

Guarded: si la tabla ya existe, no se toca (mismo criterio que
f6a7b8c9d0e1_add_research_experiment_layer.py).

Revision ID: f101101bc75d
Revises: e7f8a9b0c1d2
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f101101bc75d"
down_revision: Union[str, Sequence[str], None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("experiment_cmg_results"):
        op.create_table(
            "experiment_cmg_results",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "concept_id", sa.String(36), sa.ForeignKey("concepts.id"),
                nullable=False, index=True,
            ),
            sa.Column(
                "learning_objective_id", sa.String(36),
                sa.ForeignKey("learning_objectives.id"), nullable=False, index=True,
            ),
            sa.Column("condition", sa.String(20), nullable=False, index=True),
            sa.Column("configuration_source", sa.String(30), nullable=False),
            sa.Column("configuration", sa.JSON(), nullable=False),
            sa.Column("cmg", sa.JSON(), nullable=False),
            sa.Column("d1", sa.JSON(), nullable=False),
            sa.Column("d2", sa.JSON(), nullable=False),
            sa.Column("d3", sa.JSON(), nullable=False),
            sa.Column("execution_valid", sa.Boolean(), nullable=False),
            sa.Column("traceability", sa.JSON(), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "condition IN ('experimental', 'control')", name="ck_ecr_condition"
            ),
        )
        op.create_index(
            "ix_ecr_concept_condition",
            "experiment_cmg_results",
            ["concept_id", "condition"],
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("experiment_cmg_results"):
        op.drop_index("ix_ecr_concept_condition", table_name="experiment_cmg_results")
        op.drop_table("experiment_cmg_results")
