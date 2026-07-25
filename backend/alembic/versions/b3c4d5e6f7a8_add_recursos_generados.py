"""add_recursos_generados

Crea la tabla recursos_generados (RFC-0011/1, Parte 0 — Registro de
Recursos). Persiste cada RecursoGenerado (prompt + metadata + origen)
producido por generar_prompt_recurso() (Parte A), con clave de
reutilización (asunto, forma, modalidad, version_plantilla).

No relacionada con la tabla `resources` (archivos subidos por
docentes, app/models/resource.py) — conceptos distintos.

Revision ID: b3c4d5e6f7a8
Revises: f6a7b8c9d0e1
Create Date: 2026-07-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TABLE_NAME = "recursos_generados"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(TABLE_NAME):
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asunto", sa.String(255), nullable=False, index=True),
        sa.Column("forma", sa.String(40), nullable=False),
        sa.Column("modalidad", sa.String(40), nullable=False),
        sa.Column("concepto", sa.String(255), nullable=False),
        sa.Column("texto_prompt", sa.Text(), nullable=False),
        sa.Column("version_plantilla", sa.String(20), nullable=False),
        sa.Column("origen", sa.JSON(), nullable=False),
        sa.Column("referencia_recurso", sa.String(512), nullable=True),
        sa.Column("veces_reutilizado", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "asunto", "forma", "modalidad", "version_plantilla",
            name="uq_recurso_generado_clave_reutilizacion",
        ),
    )
    # `index=True` en la columna "asunto" ya crea
    # ix_recursos_generados_asunto durante create_table — no se declara
    # un op.create_index() adicional para el mismo índice.


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table(TABLE_NAME):
        return

    op.drop_table(TABLE_NAME)
