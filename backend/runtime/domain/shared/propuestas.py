"""¿Sigue en pie la palabra de una capacidad sobre un asunto? (CONCEPT-
0002 §5; ciclo adaptativo continuo, 2026-07-13).

Infraestructura de recorrido del estado compartida por Remediar y
Orientar (mismo criterio de extracción que `causal.py`: dos consumidores
genuinos, cero lógica de negocio de una capacidad concreta). El grafo
usa la MISMA función en su guardia (`_propuesta_con_suelo` delega aquí)
— patrón "misma función que el nodo" (PR-2..PR-5).

Una propuesta previa de la capacidad sobre el asunto CUENTA (⇒ no
re-proponer) únicamente si:

1. su respaldo sigue íntegramente vigente (si el suelo fue corregido,
   la palabra cayó con él — cascada), y
2. la propuesta sigue vigente, O fue descartada por una deliberación
   cuyo claim aceptado SIGUE vigente ("perdí limpio ante un vencedor
   vivo" — re-hablar aquí sería churn de consenso).

Si el vencedor que la descartó cayó después (nueva evidencia — CONCEPT-
0002 §5: "un claim participante de una resuelta es supersedido"), el
debate quedó huérfano: la capacidad relee el paisaje y vuelve a hablar.
"""

from __future__ import annotations

from runtime.kernel.state.entries import (
    Capacidad,
    DeliberacionEntry,
    Resuelta,
)
from runtime.kernel.state.state import LearningState


def palabra_en_pie(estado: LearningState, autor: Capacidad, asunto: str) -> bool:
    vigentes = {c.id for c in estado.claims if c.vigencia.vigente} | {
        f.id for f in estado.facts if f.vigencia.vigente
    }
    for claim in estado.claims:
        if claim.autor is not autor or claim.asunto != asunto:
            continue
        if not all(ref in vigentes for ref in claim.respaldo):
            continue  # el suelo de esta palabra fue corregido: no cuenta
        if claim.vigencia.vigente:
            return True
        superseded_por = claim.vigencia.superseded_por
        delib = estado.buscar(superseded_por) if superseded_por else None
        if isinstance(delib, DeliberacionEntry) and isinstance(
            delib.resultado, Resuelta
        ):
            aceptado = estado.buscar(delib.resultado.aceptados[0])
            if aceptado is not None and aceptado.vigencia.vigente:
                return True  # perdió limpio ante un vencedor vivo
        # vencedor caído o descarte por cascada: el debate quedó
        # huérfano — esta palabra ya no silencia a la capacidad
    return False
