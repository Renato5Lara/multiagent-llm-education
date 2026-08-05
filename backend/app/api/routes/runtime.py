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

from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import aget_current_docente, aget_current_estudiante, aget_current_user
from app.models.user import User, UserRole
from app.services.runtime_connection import (
    SPEC_VERSION,
    VERSION_BANCO,
    VERSION_POLITICA,
    almacenes,
)
from app.services.runtime_trace_serialization import evento_a_dict, valor_json
from runtime.boundary import (
    Identidad,
    PeticionAbrirSesion,
    PeticionHechoDelMundo,
    abrir_sesion,
    consultar_consenso,
    consultar_escaladas_pendientes,
    consultar_estado,
    consultar_memoria,
    consultar_paisaje,
    consultar_replay,
    consultar_traza,
    registrar_hecho,
    resolver_escalada,
)
from runtime.kernel.events import DomainEvent
from runtime.kernel.state.entries import EntryId, OrigenProvenance

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


async def aget_authorized_evidence_viewer(
    current_user: User = Depends(aget_current_user),
) -> User:
    """Las surfaces S3 de solo lectura (traza/estado/memoria/replay/paisaje/
    consenso/escaladas) las lee: el estudiante dueño, el docente (RFC-0009
    §1: es el humano del loop), y Admin/Investigador — Modo Evidencia
    (CLAUDE.md) es la superficie de observabilidad que aloja Runtime
    Console, y su backend no puede rechazar al rol que la aloja (auditoría
    2026-08-05, Ficha 06). `_verificar_pertenencia` deja pasar a los tres
    roles no-estudiante sin exigir que sean el dueño (autoridad/observador,
    no participante — RFC-0009 §3), igual criterio que ya rige
    `hecho_docente`."""
    if current_user.role not in (
        UserRole.ESTUDIANTE,
        UserRole.DOCENTE,
        UserRole.ADMIN,
        UserRole.INVESTIGADOR,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de estudiante, docente, administrador o investigador",
        )
    return current_user


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


#: RFC-0010 regla 2 (vocabulario del runtime, sin traducir) — implementación
#: compartida en runtime_trace_serialization.py; `evidence_service.py` (Modo
#: Evidencia v2, RFC-0007 §5) sirve la misma forma sin duplicar esta lógica.
_valor_json = valor_json


def _evento_out(evento: DomainEvent) -> EventoOut:
    d = evento_a_dict(evento)
    return EventoOut(tipo=d["tipo"], datos=d["datos"])


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


class PaisajeOut(BaseModel):
    densidad: Mapping[str, int]
    conflicto: Mapping[str, str]
    entropia: Mapping[str, float]


class PasoPaisajeOut(BaseModel):
    transicion: int
    paisaje: PaisajeOut
    estabilidad: int


class RespuestaPaisajeOut(BaseModel):
    transiciones: list[PasoPaisajeOut]
    tiempo_estabilizacion: Mapping[str, int]


class ConsensoOut(BaseModel):
    convocatorias: int
    no_convocatorias: int
    resueltas: int
    aplazadas: int
    escaladas: int
    margenes_resolucion: list[str]
    confianza_resolucion: list[str]
    longitud_cadenas_reconvocacion: list[int]


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
            # RFC-0006 §4 (Parte E): esta llamada es síncrona y quien la
            # hace es el propio estudiante esperando su entrega — el slot
            # es urgente; con margen < δ el consenso resuelve provisional
            # en vez de aplazar. `hecho_docente` reutiliza este mismo
            # boundary con el default (False): nadie espera en vivo.
            urgente=True,
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
    """Las surfaces S3 de solo lectura (traza/estado/memoria/replay) no
    reciben una `identidad` en el cuerpo que contrastar como sí hace
    `hecho()` (es un GET) — `resolver_identidad` tampoco verifica
    pertenencia por sí sola, así que se verifica aquí, explícitamente,
    contra lo ya persistido. Docente, Admin e Investigador quedan exentos:
    son autoridad/observadores sobre el loop, no participantes con ámbito
    por estudiante (RFC-0009 §3) — mismo criterio que ya rige
    `hecho_docente`, extendido a Modo Evidencia (Ficha 06, auditoría
    2026-08-05)."""
    if current_user.role in (UserRole.DOCENTE, UserRole.ADMIN, UserRole.INVESTIGADOR):
        return
    existente = almacen.identidad_existente(session_id)
    if existente is not None and existente.student_id != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La sesión no pertenece al usuario autenticado",
        )


@router.get("/sessions/{session_id}/traza", response_model=list[PasoTrazaOut])
def traza(
    session_id: str,
    current_user: User = Depends(aget_authorized_evidence_viewer),
) -> list[PasoTrazaOut]:
    """RFC-0007 §2.1 — la traza de eventos de la sesión, derivada de lo
    persistido (S3, RFC-0010 §2). Lee el estudiante dueño o el docente
    (RFC-0009 §1, HITL)."""
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
    current_user: User = Depends(aget_authorized_evidence_viewer),
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
    current_user: User = Depends(aget_authorized_evidence_viewer),
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
    current_user: User = Depends(aget_authorized_evidence_viewer),
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


@router.get("/sessions/{session_id}/paisaje", response_model=RespuestaPaisajeOut)
def paisaje(
    session_id: str,
    current_user: User = Depends(aget_authorized_evidence_viewer),
) -> RespuestaPaisajeOut:
    """RFC-0007 §2.2, fila "Paisaje (H8)", y §5 — el paisaje cognitivo
    reconstruido por transición (S3, RFC-0010 §2). Distinto de `/replay`
    (el `LearningState` completo): aquí cada paso es la proyección de
    lectura sobre `claims` que RFC-0007/CONCEPT-0001 llaman paisaje —
    densidad, conflicto y entropía por asunto, más la estabilidad entre
    transiciones y el tiempo lógico de estabilización por asunto."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    pasos, tiempo_estabilizacion = consultar_paisaje(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    return RespuestaPaisajeOut(
        transiciones=[
            PasoPaisajeOut(
                transicion=paso.transicion,
                paisaje=PaisajeOut(
                    densidad=paso.paisaje.densidad,
                    conflicto=paso.paisaje.conflicto,
                    entropia=paso.paisaje.entropia,
                ),
                estabilidad=paso.estabilidad,
            )
            for paso in pasos
        ],
        tiempo_estabilizacion=tiempo_estabilizacion,
    )


@router.get("/sessions/{session_id}/consenso", response_model=ConsensoOut)
def consenso(
    session_id: str,
    current_user: User = Depends(aget_authorized_evidence_viewer),
) -> ConsensoOut:
    """RFC-0007 §2.2, fila "Consenso (RFC-0006)" — resumen de consenso de
    la sesión completa (S3, RFC-0010 §2). Distinto de `/paisaje` (una
    serie por transición): aquí el resultado es un único resumen sobre
    toda la sesión, porque el consenso no tiene un "instante" — un
    episodio de deliberación ya ocurrió o no. `Decimal` se stringifica
    (mismo criterio que `valor_json`, ADR-0001 §4: exactitud decimal)."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    metricas = consultar_consenso(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    return ConsensoOut(
        convocatorias=metricas.convocatorias,
        no_convocatorias=metricas.no_convocatorias,
        resueltas=metricas.resueltas,
        aplazadas=metricas.aplazadas,
        escaladas=metricas.escaladas,
        margenes_resolucion=[str(m) for m in metricas.margenes_resolucion],
        confianza_resolucion=[str(c) for c in metricas.confianza_resolucion],
        longitud_cadenas_reconvocacion=list(metricas.longitud_cadenas_reconvocacion),
    )


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


class ResolverEscaladaIn(BaseModel):
    # `EntryId` se imprime "T-000005/e1" (barra incluida) — incompatible
    # como segmento de URL; ambos ids viajan en el cuerpo, no en el path.
    escalada_id: str
    claim_elegido: str
    human_reason: str | None = None


@router.post("/sessions/{session_id}/escaladas/resolver", response_model=EntregaOut)
def escalada_resolver(
    session_id: str,
    peticion: ResolverEscaladaIn,
    current_user: User = Depends(aget_current_docente),
) -> EntregaOut:
    """RFC-0009 §2.1, §3, entrada 1 (escalada) — E3, RFC-0010 §1: la
    autoridad humana cierra una deliberación escalada. El disparador
    orgánico de la escalada (RFC-0006 §4) queda fuera del alcance de esta
    pieza (Plataforma Operativa 4) — esta ruta resuelve una escalada que
    ya existe en la historia, cualquiera sea su origen."""
    almacen, almacen_memoria = almacenes()
    identidad = almacen.identidad_existente(session_id)
    if identidad is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="La sesión no existe"
        )
    try:
        entrega = resolver_escalada(
            identidad,
            escalada_id=EntryId.parse(peticion.escalada_id),
            claim_elegido=EntryId.parse(peticion.claim_elegido),
            human_reason=peticion.human_reason,
            almacen=almacen,
            almacen_memoria=almacen_memoria,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    return EntregaOut(asunto=entrega.asunto, diseno=entrega.diseno)


class EscaladaOut(BaseModel):
    id: str
    participantes: list[str]
    resultado: Mapping[str, Any]


@router.get("/sessions/{session_id}/escaladas", response_model=list[EscaladaOut])
def escaladas(
    session_id: str,
    current_user: User = Depends(aget_authorized_evidence_viewer),
) -> list[EscaladaOut]:
    """RFC-0010 §2, S2 — "aviso al docente de que una deliberación espera
    su autoridad, con su contexto navegable": la notificación dedicada,
    no una vista derivada de `/estado` en el frontend."""
    almacen, almacen_memoria = almacenes()
    _verificar_pertenencia(session_id, current_user, almacen)
    pendientes = consultar_escaladas_pendientes(
        _peticion_de(session_id, current_user),
        almacen,
        almacen_memoria,
    )
    return [
        EscaladaOut(
            id=str(d.id),
            participantes=[str(p) for p in d.participantes],
            resultado=_valor_json(d.resultado),
        )
        for d in pendientes
    ]
