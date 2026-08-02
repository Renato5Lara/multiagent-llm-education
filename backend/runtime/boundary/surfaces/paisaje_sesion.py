"""S3 — Superficie de lectura: el Paisaje cognitivo reconstruido por
transición de una sesión (RFC-0010 §2, S3; RFC-0007 §2.2, fila "Paisaje
(H8)", y §5 — "el visor de replay... define qué expone: estados,
eventos, paisaje reconstruido por transición"). Los observadores jamás
escriben: esta función nunca registra un hecho ni invoca una capacidad
nueva — materializa la sesión exactamente como S3-replay y deriva el
paisaje del mismo replay ya reconstruido.

Distinta de S3-replay (`consultar_replay`, el `LearningState` completo
por transición): aquí cada eslabón es la proyección de lectura sobre
`claims` que RFC-0007/CONCEPT-0001 llaman paisaje — densidad, conflicto
y entropía por asunto, más la estabilidad entre transiciones y el
tiempo lógico de estabilización por asunto."""

from __future__ import annotations

from typing import Mapping

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    TransicionPaisaje,
    derivar_paisaje,
    reconstruir_con_replay,
)
from runtime.engine.graph.walkthrough import materializar_sesion
from runtime.kernel.deliberation.politica import resolver_politica


def consultar_paisaje(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> tuple[tuple[TransicionPaisaje, ...], Mapping[str, int]]:
    """Abre o reanuda la sesión (mismo criterio que las demás surfaces S3)
    y deriva el paisaje de su historia persistida — nunca corre el
    grafo, nunca registra nada nuevo. `((), {})` si la sesión todavía no
    tiene transiciones. La política es la fijada al abrir la sesión
    (`Identidad.version_politica`, RFC-0003 INV-1) — nunca una elegida
    por quien consulta."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    if not sesion.registros:
        return (), {}
    _, replay = reconstruir_con_replay(
        identidad, sesion.estado.contexto, sesion.registros
    )
    politica = resolver_politica(identidad.version_politica)
    return derivar_paisaje(replay, politica)
