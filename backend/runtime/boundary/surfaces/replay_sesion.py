"""S3 — Superficie de lectura: el Replay Cognitivo de una sesión
(RFC-0010 §2, S3; RFC-0008 §3, modo Reconstrucción; RFC-0007 §5 —
"estados... reconstruido por transición"). Los observadores jamás
escriben: esta función nunca registra un hecho ni invoca una capacidad
nueva — materializa la sesión exactamente como S3-traza y deriva el
replay del mismo log ya leído.

Distinta de S3-traza (`consultar_traza`, solo eventos por transición):
aquí cada eslabón lleva el `LearningState` completo, acumulado hasta esa
transición — la base para "scrubbear" la sesión paso a paso.
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    Replay,
    reconstruir_con_replay,
)
from runtime.engine.graph.walkthrough import materializar_sesion


def consultar_replay(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Replay:
    """Abre o reanuda la sesión (mismo criterio que las demás surfaces S3)
    y deriva el replay de su historia persistida — nunca corre el grafo,
    nunca registra nada nuevo. `()` si la sesión todavía no tiene
    transiciones."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    if not sesion.registros:
        return ()
    _, replay = reconstruir_con_replay(
        identidad, sesion.estado.contexto, sesion.registros
    )
    return replay
