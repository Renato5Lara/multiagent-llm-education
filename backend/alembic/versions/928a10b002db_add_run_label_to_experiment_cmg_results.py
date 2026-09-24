"""add_run_label_to_experiment_cmg_results

R28/R29 — metadato de trazabilidad de la oleada de recolección
experimental. `run_label` es ortogonal a VI/VD/condición: identifica
QUÉ corrida escribió la fila (`pilot_1` | `corrida_2`), nunca decide
configuración, D1/D2/D3 ni entra al evaluador o al generador.

Backfill: las filas ya existentes (Piloto 1, 64 filas al momento de
esta migración) se etiquetan explícitamente como `pilot_1` dentro de
esta misma migración, antes de fijar la columna como NOT NULL — sin
`server_default`, a propósito: una fila futura sin `run_label`
explícito debe fallar por NOT NULL, nunca heredar `pilot_1` en
silencio (R29 Parte 6: "no inferirlo").

Revision ID: 928a10b002db
Revises: f101101bc75d
Create Date: 2026-09-22 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "928a10b002db"
down_revision: Union[str, Sequence[str], None] = "f101101bc75d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_NAME = "experiment_cmg_results"


def _has_column(inspector: sa.Inspector, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        raise RuntimeError(f"{TABLE_NAME} must exist before applying revision {revision}.")

    if not _has_column(inspector, "run_label"):
        op.add_column(TABLE_NAME, sa.Column("run_label", sa.String(20), nullable=True))
        op.execute(
            sa.text(f"UPDATE {TABLE_NAME} SET run_label = 'pilot_1' WHERE run_label IS NULL")
        )
        op.alter_column(TABLE_NAME, "run_label", nullable=False)
        op.create_check_constraint(
            "ck_ecr_run_label",
            TABLE_NAME,
            "run_label IN ('pilot_1', 'corrida_2')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    if _has_column(inspector, "run_label"):
        op.drop_constraint("ck_ecr_run_label", TABLE_NAME, type_="check")
        op.drop_column(TABLE_NAME, "run_label")
