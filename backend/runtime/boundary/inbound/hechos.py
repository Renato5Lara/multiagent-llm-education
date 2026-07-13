"""E2 — Hechos del mundo, y opcionalmente E4 — Cerrar sesión, en la
misma llamada (RFC-0010 §1) — igual que `ejecutar_walkthrough` ya las
unifica vía `cerrar_sesion`. El Boundary autora el fact, jamás un claim
(Grieta A, ajuste de RFC-0003)."""

from __future__ import annotations

from runtime.boundary.inbound.dto import PeticionHechoDelMundo
from runtime.boundary.inbound.productores import (
    productor_diagnostico_activo,
    productor_orientar_activo,
    productor_remediar_activo,
)
from runtime.boundary.outbound.entregas import Entrega, proyectar_entrega
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import ejecutar_walkthrough
from runtime.kernel.state.entries import BOUNDARY, Provenance
from runtime.kernel.transitions import TransitionIntent


def registrar_hecho(
    peticion: PeticionHechoDelMundo,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Entrega:
    """Traduce el hecho a un `TransitionIntent` de `registrar_fact`
    (regla 1 del contrato: `contenido` viaja sin interpretar), corre el
    walkthrough, y proyecta S1 (`Entrega`) desde el estado resultante.
    `cerrar_sesion=True` exige `almacen_memoria` (ADR-0008 §2.4) — ya lo
    exige `ejecutar_walkthrough`, este handler no repite la validación."""
    intent = TransitionIntent(
        productor=BOUNDARY,
        operacion="registrar_fact",
        argumentos={
            "autor": BOUNDARY,
            "contenido": peticion.contenido,
            "provenance": Provenance.de(peticion.origen),
        },
        base=0,
    )
    resultado = ejecutar_walkthrough(
        almacen,
        peticion.identidad,
        hechos_del_mundo=(intent,),
        productor_diagnostico=productor_diagnostico_activo(),
        productor_remediar=productor_remediar_activo(),
        productor_orientar=productor_orientar_activo(),
        cerrar_sesion=peticion.cerrar_sesion,
        almacen_memoria=almacen_memoria,
        urgente=peticion.urgente,
    )
    return proyectar_entrega(resultado["estado"])
