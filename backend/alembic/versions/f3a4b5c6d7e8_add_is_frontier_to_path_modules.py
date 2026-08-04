"""add_is_frontier_to_path_modules

Añade `PathModule.is_frontier` — marca explícitamente cuál posición de la
ruta es el frente de trabajo real (dominado-y-saltable vs. frente real
comparten hoy el mismo `status="available"`, sin distinción). Corrección
de adaptación por nivel (auditoría causal de adaptación, ago. 2026,
Punto A): el frontend debe navegar al frente real, no al primer
`available` en orden de arreglo.

Revision ID: f3a4b5c6d7e8
Revises: b3c4d5e6f7a8
Create Date: 2026-08-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "path_modules"


def _has_column(inspector: sa.Inspector, column_name: str) -> bool:
    return column_name in {column["name"] for column in inspector.get_columns(TABLE_NAME)}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        raise RuntimeError(
            f"{TABLE_NAME} must exist before applying revision {revision}."
        )

    if not _has_column(inspector, "is_frontier"):
        op.add_column(
            TABLE_NAME,
            sa.Column(
                "is_frontier",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    if _has_column(inspector, "is_frontier"):
        op.drop_column(TABLE_NAME, "is_frontier")
