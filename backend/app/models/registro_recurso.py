"""Registro de Recursos — RFC-0011/1 (Persistencia, Parte 0).

Persiste cada `RecursoGenerado` (app/services/resource_prompt_generation.py,
Parte A) para permitir su reutilización (RFC-0011/2, Parte B: no
regenerar un prompt ya producido para la misma combinación
asunto×forma×modalidad×version_plantilla).

No confundir con `app.models.resource.Resource`: ese modelo son
archivos subidos por docentes (PDF/video/imagen); este es un artefacto
de prompt generado por el sistema a partir de una decisión de Adaptar.
Conceptos distintos, tablas distintas (`resources` vs
`recursos_generados`).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RegistroRecurso(Base):
    """Fila persistida de un `RecursoGenerado`.

    Clave de reutilización (ROADMAP-RFC-0011.md §3, Parte 0):
    `(asunto, forma, modalidad, version_plantilla)` — única. `origen` se
    persiste tal cual lo produjo la Parte A (referencia, nunca
    interpretación nueva). `referencia_recurso` es nulo hasta que el
    recurso físico se genera externamente y se adjunta (RFC-0011/3).
    """

    __tablename__ = "recursos_generados"
    __table_args__ = (
        UniqueConstraint(
            "asunto", "forma", "modalidad", "version_plantilla",
            name="uq_recurso_generado_clave_reutilizacion",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asunto: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    forma: Mapped[str] = mapped_column(String(40), nullable=False)
    modalidad: Mapped[str] = mapped_column(String(40), nullable=False)
    concepto: Mapped[str] = mapped_column(String(255), nullable=False)
    texto_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    version_plantilla: Mapped[str] = mapped_column(String(20), nullable=False)
    origen: Mapped[dict] = mapped_column(JSON, nullable=False)
    referencia_recurso: Mapped[str | None] = mapped_column(String(512), nullable=True)
    veces_reutilizado: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:
        return f"<RegistroRecurso {self.asunto} forma={self.forma}>"
