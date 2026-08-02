"""S3 — Superficie de lectura: las métricas de consenso de una sesión
completa (RFC-0010 §2, S3; RFC-0007 §2.2, fila "Consenso (RFC-0006)").
Los observadores jamás escriben: esta función nunca registra un hecho
ni invoca una capacidad nueva — materializa la sesión exactamente como
S3-paisaje y deriva el consenso del mismo replay ya reconstruido.

Distinta de S3-paisaje (`consultar_paisaje`, una serie por transición):
aquí el resultado es un resumen único sobre TODA la sesión — el
consenso no tiene un "instante", un episodio o ya ocurrió o no."""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import (
    AlmacenMemoria,
    AlmacenTransiciones,
    MetricasConsenso,
    derivar_consenso,
    reconstruir_con_replay,
)
from runtime.engine.graph.walkthrough import materializar_sesion
from runtime.kernel.deliberation.politica import resolver_politica


def consultar_consenso(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> MetricasConsenso:
    """Abre o reanuda la sesión (mismo criterio que las demás surfaces S3)
    y deriva las métricas de consenso de su historia persistida — nunca
    corre el grafo, nunca registra nada nuevo. Métricas en cero/vacías
    si la sesión todavía no tiene transiciones. La política es la
    fijada al abrir la sesión (`Identidad.version_politica`, RFC-0003
    INV-1) — nunca una elegida por quien consulta."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    if not sesion.registros:
        return derivar_consenso((), resolver_politica(identidad.version_politica))
    _, replay = reconstruir_con_replay(
        identidad, sesion.estado.contexto, sesion.registros
    )
    politica = resolver_politica(identidad.version_politica)
    return derivar_consenso(replay, politica)
