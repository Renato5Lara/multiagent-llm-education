"""Router HTTP del runtime nuevo (RFC-0010, ADR-0009) — la primera
superficie que ejecuta LangGraph sin pasar por BaseAgent (Épica 1;
CLAUDE.md, actualización 2026-07-12).

Traduce HTTP ↔ DTOs del Boundary; el Boundary traduce DTOs ↔ runtime —
cada capa hace solo su propia mitad (ADR-0009 §2.3). Comparte la
conexión al runtime de `app/services/runtime_connection.py` con
cualquier otro módulo de `app/` que también invoque el runtime — p. ej.
`app/services/runtime_bridge.py` (Épica 2) — ninguno abre su propia
instancia (ADR-0009 §6). Aditivo: no toca `app/agents/` — el retiro de
BaseAgent es una épica posterior.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import aget_current_estudiante
from app.models.user import User
from app.services.runtime_connection import (
    SPEC_VERSION,
    VERSION_BANCO,
    VERSION_POLITICA,
    almacenes,
)
from runtime.boundary import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    consultar_traza,
    registrar_hecho,
)
from runtime.kernel.events import DomainEvent
from runtime.kernel.state.entries import EntryId, OrigenProvenance

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


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


class EventoOut(BaseModel):
    tipo: str
    datos: Mapping[str, Any]


class PasoTrazaOut(BaseModel):
    transicion: int
    eventos: list[EventoOut]


def _valor_json(valor: Any) -> Any:
    """`EntryId` es el único tipo del kernel en los eventos que no es ya
    JSON-nativo (los enum de vocabulario son `str, Enum`)."""
    return str(valor) if isinstance(valor, EntryId) else valor


def _evento_out(evento: DomainEvent) -> EventoOut:
    """RFC-0010 regla 2: vocabulario del runtime, sin traducir — cada
    campo del evento viaja tal cual, solo `EntryId` se stringifica."""
    datos = {
        campo.name: _valor_json(getattr(evento, campo.name))
        for campo in dataclasses.fields(evento)
        if campo.name != "transicion"
    }
    return EventoOut(tipo=type(evento).__name__, datos=datos)


@router.post("/sessions", response_model=IdentidadOut)
def abrir(
    peticion: AbrirSesionIn,
    current_user: User = Depends(aget_current_estudiante),
) -> IdentidadOut:
    """E1 — abrir o reanudar sesión. `student_id` viene del usuario
    autenticado, jamás del cuerpo de la petición — el Boundary traduce,
    no confía en identidad autodeclarada por el cliente."""
    almacen, almacen_memoria = almacenes()
    identidad = abrir_sesion(
        PeticionAbrirSesion(
            session_id=peticion.session_id,
            student_id=str(current_user.id),
            version_banco=VERSION_BANCO,
            version_politica=VERSION_POLITICA,
            spec_version=SPEC_VERSION,
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
    almacen, almacen_memoria = almacenes()
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


@router.get("/sessions/{session_id}/traza", response_model=list[PasoTrazaOut])
def traza(
    session_id: str,
    current_user: User = Depends(aget_current_estudiante),
) -> list[PasoTrazaOut]:
    """RFC-0007 §2.1 — la traza de eventos de la sesión, derivada de lo
    persistido (S3, RFC-0010 §2). Esta pieza solo autoriza al estudiante
    dueño de la sesión: `resolver_identidad` no verifica pertenencia por
    sí solo (a diferencia de `hecho()`, aquí no hay `identidad` en el
    cuerpo que contrastar, así que se verifica explícitamente contra lo
    ya persistido). Modo Evidencia (docente/admin) es una superficie
    posterior — no inventada aquí."""
    almacen, almacen_memoria = almacenes()
    existente = almacen.identidad_existente(session_id)
    if existente is not None and existente.student_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no pertenece al usuario autenticado",
        )
    pasos = consultar_traza(
        PeticionAbrirSesion(
            session_id=session_id,
            student_id=str(current_user.id),
            version_banco=VERSION_BANCO,
            version_politica=VERSION_POLITICA,
            spec_version=SPEC_VERSION,
        ),
        almacen,
        almacen_memoria,
    )
    return [
        PasoTrazaOut(
            transicion=paso.transicion,
            eventos=[_evento_out(evento) for evento in paso.eventos],
        )
        for paso in pasos
    ]
