"""HITL, entrada 1 — Resolución de escalada (RFC-0009 §2.1, §3): el
docente ejerce autoridad sobre una deliberación escalada, no participa
del consenso. Dos transiciones en la misma invocación, ambas ya
existentes (RFC-0009: "sin conceptos nuevos"):

1. El fact humano (Grieta A: el Boundary autora facts, jamás claims;
   provenance `humano`) — la justificación (`human_reason`) viaja en su
   `contenido`, evidencia de investigación, nunca derivación (RFC-0009
   §3).
2. La deliberación que cierra la escalada con la regla explícita
   `decision-humana` (un nombre de regla más del catálogo de RFC-0006,
   no un tipo nuevo), `enlaza_a` la escalada original — nunca la reabre
   (CONCEPT-0002 §5), la resuelve por la vía normal.

Ambas viajan como `hechos_del_mundo` de la MISMA invocación de
`ejecutar_walkthrough` (su propio contrato ya anticipa esto: "invariante
que gobernará también... a cualquier reanudación vía HITL"): el grafo,
tras aplicarlas, enruta normalmente — "decidir" deriva la decisión de la
deliberación recién resuelta, y el walkthrough continúa exactamente como
si la hubiera resuelto una capacidad (RFC-0009: "el sistema no finge que
decidió solo", pero tampoco se detiene a esperar más que eso).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.boundary.inbound.productores import (
    productor_diagnostico_activo,
    productor_orientar_activo,
    productor_remediar_activo,
)
from runtime.boundary.outbound.entregas import Entrega, proyectar_entrega
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import ejecutar_walkthrough, materializar_sesion
from runtime.kernel.state.entries import (
    BOUNDARY,
    DeliberacionEntry,
    EntryId,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
)
from runtime.kernel.state.state import Identidad
from runtime.kernel.transitions import TransitionIntent

REGLA_DECISION_HUMANA = "decision-humana"


def resolver_escalada(
    identidad: Identidad,
    escalada_id: EntryId,
    claim_elegido: EntryId,
    human_reason: str | None,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Entrega:
    """`ValueError` (ADR-0004 E-2, defecto del llamador, no del dominio)
    si `escalada_id` no existe, no es una deliberación escalada, ya fue
    resuelta, o `claim_elegido` no es uno de sus participantes — la
    autoridad humana selecciona entre lo que la escalada puso sobre la
    mesa, jamás crea (P15)."""
    sesion = materializar_sesion(almacen, almacen_memoria, identidad)
    estado = sesion.estado

    escalada = estado.buscar(escalada_id)
    if not isinstance(escalada, DeliberacionEntry) or not isinstance(
        escalada.resultado, Escalada
    ):
        raise ValueError(f"{escalada_id} no es una deliberación escalada")
    if any(d.enlaza_a == escalada_id for d in estado.deliberaciones):
        raise ValueError(f"la escalada {escalada_id} ya fue resuelta")
    if claim_elegido not in escalada.participantes:
        raise ValueError(
            f"P15: {claim_elegido} no es uno de los participantes de "
            f"{escalada_id} — la autoridad humana selecciona, no crea"
        )

    contenido: dict[str, object] = {
        "escalada_id": str(escalada_id),
        "claim_elegido": str(claim_elegido),
    }
    if human_reason is not None:
        contenido["human_reason"] = human_reason

    intent_fact = TransitionIntent(
        productor=BOUNDARY,
        operacion="registrar_fact",
        argumentos={
            "autor": BOUNDARY,
            "contenido": contenido,
            "provenance": Provenance.de(OrigenProvenance.HUMANO),
        },
        base=0,
    )
    intent_deliberacion = TransitionIntent(
        productor="kernel",
        operacion="registrar_deliberacion",
        argumentos={
            "participantes": escalada.participantes,
            "resultado": Resuelta(
                regla=REGLA_DECISION_HUMANA,
                aceptados=(claim_elegido,),
                confianza=Decimal("1"),
            ),
            "enlaza_a": escalada_id,
        },
        base=0,
    )
    resultado = ejecutar_walkthrough(
        almacen,
        identidad,
        hechos_del_mundo=(intent_fact, intent_deliberacion),
        productor_diagnostico=productor_diagnostico_activo(),
        productor_remediar=productor_remediar_activo(),
        productor_orientar=productor_orientar_activo(),
        almacen_memoria=almacen_memoria,
    )
    return proyectar_entrega(resultado["estado"])
