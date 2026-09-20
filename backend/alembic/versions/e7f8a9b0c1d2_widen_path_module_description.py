"""widen_path_module_description

2C-3.19 (Deliberacion - Cruce Auditoria 01 x Auditoria 02.md), D19.1:
`path_modules.description` era `VARCHAR(500)`, snapshot directo de
`LearningObjective.description`. Desde D1-D8/B2, esa descripción es
prosa de alcance pedagógico general -- 6 de los 8 módulos de IS301
superan los 500 caracteres tras la transformación 4->8 (2C-3.18).
Confirmado por ejecución real en D15.7: StringDataRightTruncation al
generar una ruta contra la base de datos ya transformada, y el mismo
riesgo en el segundo escritor real (`academic_activation_service.py`,
ruta `POST /teacher-assignments`).

Auditoría de consumidores (D19, previa a esta migración): ningún
esquema Pydantic declara `max_length` sobre este campo, ningún
componente de frontend trunca o depende de su longitud, ninguna
suite de tests lo asume, y ningún servicio lo exporta hacia un
almacenamiento con límite menor. Ampliar a `Text` no altera la
semántica del dato ni el modelo de snapshot -- solo corrige una
incompatibilidad de capacidad de almacenamiento descubierta después
de que el contenido pedagógico ya había sido aprobado.

No se modifican las descripciones D1-D8, no se trunca contenido, no
se tocan los escritores ni los lectores -- únicamente el tipo de la
columna.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-09-19 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "path_modules",
        "description",
        existing_type=sa.String(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    # No se trunca contenido real al bajar: si alguna fila real ya
    # supera 500 caracteres (esperado, dado que este es justamente el
    # problema que esta migración resuelve), un downgrade que reduzca
    # el tipo a VARCHAR(500) fallaría de forma explícita en Postgres en
    # vez de truncar en silencio -- comportamiento honesto, no una
    # reversión falsa.
    op.alter_column(
        "path_modules",
        "description",
        existing_type=sa.Text(),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
