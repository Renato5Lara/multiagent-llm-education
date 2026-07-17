"""S3 — Superficie de lectura: la Traza de eventos de una sesión
(RFC-0010 §2, S3; RFC-0007 §2.1 — "la secuencia de transiciones de una
sesión, con sus eventos... la traza no se construye: se recorre"). Los
observadores jamás escriben (regla 2): esta función nunca registra un
hecho ni invoca una capacidad nueva — materializa la sesión exactamente
como S3-entrega y deriva la traza del mismo log ya leído, en vocabulario
del runtime, sin traducirlo.

Primer consumidor previsto: Modo Evidencia v2 (RFC-0007 §5), hoy 100%
legacy (lee tablas v1, cero contacto con `runtime_transitions`).
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    Traza,
    reconstruir_con_traza,
)
from runtime.engine.graph.walkthrough import materializar_sesion


def consultar_traza(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Traza:
    """Abre o reanuda la sesión (mismo criterio que `consultar_entrega_
    vigente`) y deriva la traza de su historia persistida — nunca corre
    el grafo, nunca registra nada nuevo. `()` si la sesión todavía no
    tiene transiciones (p. ej. estudiante nuevo, recién abierta)."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    if not sesion.registros:
        return ()
    _, traza = reconstruir_con_traza(
        identidad, sesion.estado.contexto, sesion.registros
    )
    return traza
