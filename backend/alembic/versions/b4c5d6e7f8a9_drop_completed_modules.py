"""drop_completed_modules

Elimina learning_paths.completed_modules (auditoría de concurrencia,
2026-08-09): contador cacheado, escrito solo por
student_service.update_module_progress() vía un COUNT() recalculado sin
lock. Race condition confirmada con HTTP real concurrente contra Postgres
real (3/3 reproducciones, lost update silencioso) y 15/73 learning_paths
reales ya desincronizados en producción al momento de esta migración (ver
FLOW_AUDIT.md). El resto del producto (evidence_service, course_service,
learning_experience_service, knowledge_test_service — este último por el
mismo bug, Iteración 6.1) ya derivaba el dato en vivo desde
PathModule.status en vez de confiar en esta columna. Regla de derivación
(CLAUDE.md): un atributo reconstruible determinísticamente no debe
persistirse.

Revision ID: b4c5d6e7f8a9
Revises: 3a1a6681df05
Create Date: 2026-08-09 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "3a1a6681df05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("learning_paths")}
    if "completed_modules" in columns:
        op.drop_column("learning_paths", "completed_modules")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("learning_paths")}
    if "completed_modules" not in columns:
        # No se restauran los 15/73 valores desincronizados que existían
        # antes de esta migración (documentados en FLOW_AUDIT.md) — el
        # downgrade solo recrea la columna vacía; el dato derivado en vivo
        # sigue disponible desde PathModule.status en cualquier momento.
        op.add_column(
            "learning_paths",
            sa.Column("completed_modules", sa.Integer(), nullable=True, server_default=sa.text("0")),
        )
