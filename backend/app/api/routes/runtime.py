"""Router HTTP del runtime nuevo (RFC-0010, ADR-0009) — la primera
superficie que ejecuta LangGraph sin pasar por BaseAgent (Épica 1;
CLAUDE.md, actualización 2026-07-12).

Único módulo de `app/` que importa `runtime.boundary` (regla de
importación de BLUEPRINT: `app/` → `boundary/` únicamente). Traduce
HTTP ↔ DTOs del Boundary; el Boundary traduce DTOs ↔ runtime — cada capa
hace solo su propia mitad (ADR-0009 §2.3). Aditivo: no toca
`app/agents/` ni `/api/sessions/*` — esa migración es la Épica 2.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import aget_current_estudiante
from app.models.user import User
from runtime.boundary import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    registrar_hecho,
)
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.kernel.state.entries import OrigenProvenance

router = APIRouter(prefix="/api/runtime", tags=["runtime"])

#: Baseline fijo hasta que `runtime/policy/` formalice el versionado de
#: política y banco (Épica 5, RFC-0006). No existe todavía un catálogo
#: real entre el cual elegir — inventar un contrato HTTP para elegirlo
#: fabricaría una capacidad inexistente (ADR-0009 §4, límite explícito).
_VERSION_BANCO = "v1"
_VERSION_POLITICA = "v1"
_SPEC_VERSION = "foundation-2026-07-10"

_RUNTIME_URL = os.environ.get(
    "RUNTIME_DATABASE_URL",
    "postgresql://upao_user:upao_pass@localhost:5432/upao_mas_edu",
)
_RUNTIME_ESQUEMA = os.environ.get("RUNTIME_DATABASE_SCHEMA", "runtime")


@lru_cache(maxsize=1)
def _almacenes() -> tuple[AlmacenTransiciones, AlmacenMemoria]:
    """Conexión propia del runtime (ADR-0009 §2.4) — nunca el
    AsyncSession de la plataforma. Perezosa (primer uso, no import de
    este módulo): igual que el resto de la app, Postgres solo se exige
    a quien de verdad ejecuta una petición — importar este router no
    debe requerir Postgres arriba (evita romper la colección de tests
    que no tocan `/api/runtime/*`, p. ej. los que usan SQLite). Sin
    estado mutable propio (cada método abre y cierra su propia conexión
    psycopg2): compartir la instancia entre requests concurrentes del
    threadpool de FastAPI es seguro."""
    almacen = AlmacenTransiciones(_RUNTIME_URL, esquema=_RUNTIME_ESQUEMA)
    almacen_memoria = AlmacenMemoria(_RUNTIME_URL, esquema=_RUNTIME_ESQUEMA)
    almacen.preparar()
    almacen_memoria.preparar()
    return almacen, almacen_memoria


class IdentidadOut(BaseModel):
    session_id: str
    student_id: str
    version_student_model: str
    version_banco: str
    version_politica: str
    spec_version: str

    @classmethod
    def de(cls, identidad: Identidad) -> "IdentidadOut":
        return cls(
            session_id=identidad.session_id,
            student_id=identidad.student_id,
            version_student_model=identidad.version_student_model,
            version_banco=identidad.version_banco,
            version_politica=identidad.version_politica,
            spec_version=identidad.spec_version,
        )

    def a_identidad(self) -> Identidad:
        return Identidad(
            session_id=self.session_id,
            student_id=self.student_id,
            version_student_model=self.version_student_model,
            version_banco=self.version_banco,
            version_politica=self.version_politica,
            spec_version=self.spec_version,
        )


class AbrirSesionIn(BaseModel):
    session_id: str


class HechoIn(BaseModel):
    identidad: IdentidadOut
    contenido: Mapping[str, Any]
    origen: str
    cerrar_sesion: bool = False


class EntregaOut(BaseModel):
    asunto: str | None
    diseno: Mapping[str, Any] | None


@router.post("/sessions", response_model=IdentidadOut)
def abrir(
    peticion: AbrirSesionIn,
    current_user: User = Depends(aget_current_estudiante),
) -> IdentidadOut:
    """E1 — abrir o reanudar sesión. `student_id` viene del usuario
    autenticado, jamás del cuerpo de la petición — el Boundary traduce,
    no confía en identidad autodeclarada por el cliente."""
    almacen, almacen_memoria = _almacenes()
    identidad = abrir_sesion(
        PeticionAbrirSesion(
            session_id=peticion.session_id,
            student_id=str(current_user.id),
            version_banco=_VERSION_BANCO,
            version_politica=_VERSION_POLITICA,
            spec_version=_SPEC_VERSION,
        ),
        almacen,
        almacen_memoria,
    )
    return IdentidadOut.de(identidad)


@router.post("/hechos", response_model=EntregaOut)
def hecho(
    peticion: HechoIn,
    current_user: User = Depends(aget_current_estudiante),
) -> EntregaOut:
    """E2 (+ E4 si `cerrar_sesion=True`) — un hecho del mundo. La
    identidad completa se reenvía tal cual la devolvió `/sessions`
    (R5, INV-2); esta capa solo verifica que pertenezca al usuario
    autenticado, nunca la reinterpreta."""
    if peticion.identidad.student_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La identidad de sesión no pertenece al usuario autenticado",
        )
    try:
        origen = OrigenProvenance(peticion.origen)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"origen inválido: {peticion.origen!r}",
        ) from exc
    almacen, almacen_memoria = _almacenes()
    entrega = registrar_hecho(
        PeticionHechoDelMundo(
            identidad=peticion.identidad.a_identidad(),
            contenido=peticion.contenido,
            origen=origen,
            cerrar_sesion=peticion.cerrar_sesion,
        ),
        almacen,
        almacen_memoria,
    )
    return EntregaOut(asunto=entrega.asunto, diseno=entrega.diseno)
