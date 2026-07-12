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
from decimal import Decimal
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import aget_current_docente, aget_current_estudiante
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
    consultar_estado,
    consultar_memoria,
    consultar_replay,
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
    """RFC-0010 regla 2: vocabulario del runtime, sin traducir — recorre
    cualquier valor del kernel (eventos, entradas del estado, uniones
    como `ResultadoDeliberacion`) hasta que solo queden tipos JSON-nativos.
    Los enum de vocabulario ya son `str, Enum`; `EntryId` y `Decimal`
    (ADR-0001 §4, exactitud decimal) son los únicos que se stringifican."""
    if isinstance(valor, (EntryId, Decimal)):
        return str(valor)
    if dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        return {
            campo.name: _valor_json(getattr(valor, campo.name))
            for campo in dataclasses.fields(valor)
        }
    if isinstance(valor, (tuple, list)):
        return [_valor_json(v) for v in valor]
    return valor


def _evento_out(evento: DomainEvent) -> EventoOut:
    datos = {
        campo.name: _valor_json(getattr(evento, campo.name))
        for campo in dataclasses.fields(evento)
        if campo.name != "transicion"
    }
    return EventoOut(tipo=type(evento).__name__, datos=datos)


class EstadoOut(BaseModel):
    transicion: int
    facts: list[Mapping[str, Any]]
    claims: list[Mapping[str, Any]]
    deliberaciones: list[Mapping[str, Any]]
    decisiones: list[Mapping[str, Any]]


class MemoriaOut(BaseModel):
    student_id: str
    session_id: str
    catalogo: Mapping[str, Any]


class PasoReplayOut(BaseModel):
    transicion: int
    estado: EstadoOut


def _estado_out(learning_state: Any) -> EstadoOut:
    return EstadoOut(
        transicion=learning_state.transicion,
        facts=[_valor_json(f) for f in learning_state.facts],
        claims=[_valor_json(c) for c in learning_state.claims],
        deliberaciones=[_valor_json(d) for d in learning_state.deliberaciones],
        decisiones=[_valor_json(d) for d in learning_state.decisiones],
    )


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


def _peticion_de(session_id: str, current_user: User) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id=str(current_user.id),
        version_banco=VERSION_BANCO,
        version_politica=VERSION_POLITICA,
        spec_version=SPEC_VERSION,
    )


def _verificar_pertenencia(session_id: str, current_user: User, almacen: Any) -> None:
    """Las tres surfaces S3 de solo lectura (traza/estado/memoria) no
    reciben una `identidad` en el cuerpo que contrastar como sí hace
    `hecho()` (es un GET) — `resolver_identidad` tampoco verifica
    pertenencia por sí sola, así que se verifica aquí, explícitamente,
    contra lo ya persistido."""
    existente = almacen.identidad_existente(session_id)
    if existente is not None and existente.student_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no pertenece al usuario autenticado",
        )


@router.get("/sessions/{session_id}/traza", response_model=list[PasoTrazaOut])
def traza(
    session_id: str,
    current_user: User = Depends(aget_current_estudiante),
) -> list[PasoTrazaOut]:
    """RFC-0007 §2.1 — la traza de eventos de la sesión, derivada de lo
    persistido (S3, RFC-0010 §2). Modo Evidencia (docente/admin) es una
    superficie posterior — no inventada aquí."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    pasos = consultar_traza(
        _peticion_de(session_id, current_user),
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


@router.get("/sessions/{session_id}/estado", response_model=EstadoOut)
def estado(
    session_id: str,
    current_user: User = Depends(aget_current_estudiante),
) -> EstadoOut:
    """RFC-0002 §1 — el LearningState completo de la sesión (S3, RFC-0010
    §2): facts, claims, deliberaciones, decisiones, tal como el kernel
    los tiene, sin proyectar ni resumir."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    learning_state = consultar_estado(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    return _estado_out(learning_state)


@router.get("/sessions/{session_id}/memoria", response_model=MemoriaOut | None)
def memoria(
    session_id: str,
    current_user: User = Depends(aget_current_estudiante),
) -> MemoriaOut | None:
    """RFC-0005 §2 — la versión de memoria que ESTA sesión tiene fijada
    (S3, RFC-0010 §2), nunca "la más reciente" del estudiante. `None`
    si `version_student_model` es "0" (RFC-0005 §1.1): el estudiante
    todavía no consolidó ninguna sesión — un estado válido, no un error."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    version = consultar_memoria(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    if version is None:
        return None
    return MemoriaOut(
        student_id=version.student_id,
        session_id=version.session_id,
        catalogo=version.catalogo,
    )


@router.get("/sessions/{session_id}/replay", response_model=list[PasoReplayOut])
def replay(
    session_id: str,
    current_user: User = Depends(aget_current_estudiante),
) -> list[PasoReplayOut]:
    """RFC-0008 §3, modo Reconstrucción — el `LearningState` completo tal
    como quedó después de cada transición (S3, RFC-0010 §2). Distinto de
    `/traza` (solo eventos): aquí cada paso lleva el estado acumulado
    completo, la base para recorrer la sesión paso a paso."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    pasos = consultar_replay(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    return [
        PasoReplayOut(transicion=paso.transicion, estado=_estado_out(paso.estado))
        for paso in pasos
    ]


class HechoDocenteIn(BaseModel):
    contenido: Mapping[str, Any]
    human_reason: str | None = None


@router.post("/sessions/{session_id}/hechos-docente", response_model=EntregaOut)
def hecho_docente(
    session_id: str,
    peticion: HechoDocenteIn,
    current_user: User = Depends(aget_current_docente),
) -> EntregaOut:
    """RFC-0009 §2, entrada 2 (intervención espontánea) — E3, RFC-0010 §1:
    "juicios... del docente" como facts con provenance `humano`. Reutiliza
    `registrar_hecho` sin cambios: el Boundary no distingue autor humano
    de fact estudiantil salvo por `provenance` (Grieta A). No exige que
    el docente "sea dueño" de la sesión — es autoridad, no participante
    del consenso (RFC-0009 §3); el alcance de qué estudiantes ve cada
    docente es una capacidad de Inteligencia Docente, no de este Boundary."""
    almacen, almacen_memoria = almacenes()
    identidad = almacen.identidad_existente(session_id)
    if identidad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La sesión no existe"
        )
    contenido = dict(peticion.contenido)
    if peticion.human_reason is not None:
        contenido["human_reason"] = peticion.human_reason
    entrega = registrar_hecho(
        PeticionHechoDelMundo(
            identidad=identidad,
            contenido=contenido,
            origen=OrigenProvenance.HUMANO,
        ),
        almacen,
        almacen_memoria,
    )
    return EntregaOut(asunto=entrega.asunto, diseno=entrega.diseno)
