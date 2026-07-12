"""S3 — Superficie de lectura: el Estado Final de una sesión (RFC-0010
§2, S3; RFC-0002 §1, la anatomía completa del `LearningState`). Los
observadores jamás escriben: `materializar_sesion` ya reconstruye el
estado completo (facts, claims, deliberaciones, decisiones) — esta
superficie solo lo expone, sin proyectar ni resumir nada.

Distinta de S1 (`consultar_entrega_vigente`, solo el claim de Adaptar
vigente) y de S3-traza (`consultar_traza`, la secuencia de eventos): esta
es la fotografía completa del agregado en su último tiempo lógico.
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import materializar_sesion
from runtime.kernel.state.state import LearningState


def consultar_estado(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> LearningState:
    """Abre o reanuda la sesión (mismo criterio que las demás surfaces S3)
    y devuelve el `LearningState` tal como `materializar_sesion` ya lo
    reconstruye — nunca corre el grafo, nunca registra nada nuevo."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    return sesion.estado
