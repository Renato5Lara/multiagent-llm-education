"""Registro de Recursos — reutilización (RFC-0011/2, Parte B).

Antes de generar un `RecursoGenerado` nuevo (Parte A,
resource_prompt_generation.py), consulta el Registro (Parte 0,
`RegistroRecurso`) por la clave de reutilización
`(asunto, forma, modalidad, version_plantilla)`. Si existe, lo
reutiliza — nunca vuelve a llamar a `generar_prompt_recurso()` para la
misma clave, ni regenera `texto_prompt`. Si no existe, genera y
persiste.

Nunca decide pedagogía ni toca `backend/runtime/` — solo persistencia y
reutilización, mismo locus que `adaptive_form_selection.py`. No
modifica la lógica de `seleccionar_forma()`: recibe `forma`/`modalidad`
ya decididas por el llamador (ROADMAP-RFC-0011.md §7, ficha RFC-0011/2).
"""

from __future__ import annotations

from typing import Mapping

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.registro_recurso import RegistroRecurso
from app.services.resource_prompt_generation import (
    VERSION_PLANTILLA,
    generar_prompt_recurso,
)


def _buscar_existente(
    db: Session, asunto: str, forma: str, modalidad: str
) -> RegistroRecurso | None:
    return (
        db.query(RegistroRecurso)
        .filter_by(
            asunto=asunto,
            forma=forma,
            modalidad=modalidad,
            version_plantilla=VERSION_PLANTILLA,
        )
        .one_or_none()
    )


def obtener_o_generar_recurso(
    db: Session,
    forma: str,
    modalidad: str,
    asunto: str,
    concepto: str,
    *,
    nivel: str | None = None,
    objetivo: str | None = None,
    alternativas_descartadas: tuple[Mapping[str, str], ...] = (),
) -> RegistroRecurso:
    """Reutiliza el `RegistroRecurso` de la misma clave si ya existe;
    si no, genera uno nuevo (Parte A) y lo persiste.

    Clave de reutilización: `(asunto, forma, modalidad,
    version_plantilla)` — misma que la `UniqueConstraint` de la tabla
    (ROADMAP-RFC-0011.md §3, Parte 0). Transparente para el llamador:
    siempre devuelve un `RegistroRecurso`, reutilizado o recién creado
    (distinguible por `veces_reutilizado`).
    """
    existente = _buscar_existente(db, asunto, forma, modalidad)
    if existente is not None:
        existente.veces_reutilizado += 1
        db.commit()
        db.refresh(existente)
        return existente

    recurso = generar_prompt_recurso(
        forma, modalidad, asunto, concepto,
        nivel=nivel, objetivo=objetivo,
        alternativas_descartadas=alternativas_descartadas,
    )
    fila = RegistroRecurso(
        asunto=recurso.asunto,
        forma=recurso.forma,
        modalidad=recurso.modalidad,
        concepto=recurso.concepto,
        texto_prompt=recurso.texto_prompt,
        version_plantilla=recurso.version_plantilla,
        origen=dict(recurso.origen),
        referencia_recurso=recurso.referencia_recurso,
    )
    db.add(fila)
    try:
        db.commit()
    except IntegrityError:
        # Dos peticiones concurrentes generaron la misma clave a la vez
        # (p. ej. dos estudiantes fallando el mismo concepto al mismo
        # tiempo) — la UniqueConstraint de la tabla ya lo impidió; la
        # petición perdedora reutiliza la fila que sí se insertó, en vez
        # de fallar. Mismo criterio de "reutilización transparente".
        db.rollback()
        existente = _buscar_existente(db, asunto, forma, modalidad)
        if existente is None:
            raise
        existente.veces_reutilizado += 1
        db.commit()
        db.refresh(existente)
        return existente

    db.refresh(fila)
    return fila
