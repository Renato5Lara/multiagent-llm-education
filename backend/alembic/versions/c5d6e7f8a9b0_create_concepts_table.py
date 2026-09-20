"""create_concepts_table

Entidad curricular `Concept` (2C-3.10, Deliberacion - Cruce Auditoria 01 x
Auditoria 02.md): unidad propia de los 32 conceptos del catálogo cerrado
en 4a.2, independiente de `ProgrammingConcept`. Pertenece a un único
`LearningObjective`/Módulo de introducción (2C-3.2, cardinalidad 1:N).

No incluye `course_id` (se deriva transitivamente vía
`learning_objective_id` → `learning_objectives.course_id`, regla de
derivación ya vigente en el proyecto), ni `runtime_subject`/`asunto`
(2C-3.7: el asunto del Runtime se deriva bajo demanda de `Concept.title`
vía `normalizar_asunto()`, nunca se persiste), ni relación con
`LearningCycle` (2C-3.9: no es una entidad persistida), ni FK de
prerrequisitos (2C-3.3: el orden lineal de módulo/concepto ya captura las
dependencias identificadas), ni campos de contenido/generación (eso
pertenece al futuro `Artifact`, deliberadamente diferido).

Solo esquema — sin datos. La transformación de `IS301` y la siembra de
los 32 conceptos se hacen en la revisión siguiente
(migrate_is301_to_8_modules), para no mezclar un cambio de esquema
trivialmente reversible con una migración de datos.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-09-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column(
            "learning_objective_id",
            sa.String(length=36),
            sa.ForeignKey("learning_objectives.id"),
            nullable=False,
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.UniqueConstraint(
            "learning_objective_id", "order", name="uq_concepts_objective_order"
        ),
    )


def downgrade() -> None:
    op.drop_table("concepts")
