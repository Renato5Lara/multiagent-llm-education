"""S2 — Notificaciones de escalada (RFC-0010 §2): "aviso al docente de
que una deliberación espera su autoridad, con su contexto navegable" —
distinta de S3 (superficies de lectura generales): S2 es la salida
dedicada a UNA pregunta ("¿qué espera al docente ahora mismo?"), no una
vista derivada de `/estado` en el frontend.

Los observadores jamás escriben: esta función nunca registra un hecho
ni invoca una capacidad nueva — filtra las deliberaciones que
`materializar_sesion` ya reconstruye. Una escalada sigue pendiente
mientras ninguna otra deliberación la enlace (`enlaza_a`) — el mismo
criterio que ya usa `resolver_escalada` (E3) para rechazar una segunda
resolución (RFC-0009 §3).
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import materializar_sesion
from runtime.kernel.state.entries import DeliberacionEntry, Escalada


def consultar_escaladas_pendientes(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> tuple[DeliberacionEntry, ...]:
    """Abre o reanuda la sesión (mismo criterio que las demás surfaces) y
    filtra las deliberaciones escaladas sin resolver — nunca corre el
    grafo, nunca registra nada nuevo. `()` si no hay ninguna pendiente."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    estado = sesion.estado
    resueltas = {d.enlaza_a for d in estado.deliberaciones if d.enlaza_a is not None}
    return tuple(
        d
        for d in estado.deliberaciones
        if isinstance(d.resultado, Escalada) and d.id not in resueltas
    )
