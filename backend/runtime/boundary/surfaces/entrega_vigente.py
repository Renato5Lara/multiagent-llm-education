"""S3 — Superficie de lectura: la Entrega vigente de una sesión (RFC-
0010 §2, "consulta del student model vigente" — aquí, de la decisión de
experiencia vigente, S1). Los observadores jamás escriben (regla 2):
esta función nunca registra un hecho ni invoca una capacidad nueva —
materializa la sesión exactamente como E1 y proyecta S1 sobre el estado
resultante, sin más.

Épica 2: el primer consumidor es `module_orchestration_service`, para
dejar de decidir `bloom_target` por sí mismo y leer en cambio la
decisión que el runtime ya tomó a partir de evidencia de evaluación.
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.boundary.outbound.entregas import Entrega, proyectar_entrega
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import materializar_sesion


def consultar_entrega_vigente(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Entrega:
    """Abre o reanude la sesión (mismo criterio que `abrir_sesion`, E1)
    y proyecta la Entrega vigente — nunca corre el grafo, nunca registra
    un hecho nuevo. `Entrega(asunto=None, diseno=None)` si el
    walkthrough todavía no llegó a adaptar (p. ej. estudiante nuevo, sin
    evidencia todavía) — un estado válido, no un error."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    return proyectar_entrega(sesion.estado)
