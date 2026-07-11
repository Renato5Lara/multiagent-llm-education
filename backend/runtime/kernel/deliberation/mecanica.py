"""Convocatoria y resolución mínimas (RFC-0006 §3–§4; política politica-v1).

Todo aquí es función pura del estado (P12): sin reloj, sin azar, sin LLM.
La regla de politica-v1 — `mayor-confianza-declarada` — queda registrada
por nombre en cada resolución (INV-7); los desempates son deterministas
(orden textual del id).
"""

from __future__ import annotations

from collections import defaultdict

from runtime.kernel.state.entries import ClaimEntry, EntryId, Resuelta, TipoClaim
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

REGLA_POLITICA_V1 = "mayor-confianza-declarada"


def _propuestas_vigentes(estado: LearningState) -> tuple[ClaimEntry, ...]:
    return tuple(
        c
        for c in estado.claims
        if c.tipo is TipoClaim.PROPUESTA and c.vigencia.vigente
    )


def tension_bloqueante(
    estado: LearningState,
) -> tuple[str, tuple[EntryId, ...]] | None:
    """≥2 propuestas vigentes sobre el MISMO asunto (RFC-0006 §3)."""
    por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
    for claim in _propuestas_vigentes(estado):
        por_asunto[claim.asunto].append(claim)
    for asunto in sorted(por_asunto):
        rivales = por_asunto[asunto]
        if len(rivales) >= 2:
            return asunto, tuple(sorted((c.id for c in rivales), key=str))
    return None


def convocar(estado: LearningState) -> TransitionIntent | None:
    """Resuelve la tensión bloqueante bajo politica-v1 y propone el episodio."""
    tension = tension_bloqueante(estado)
    if tension is None:
        return None
    _, participantes = tension
    claims = [estado.buscar(ref) for ref in participantes]
    ganador = max(claims, key=lambda c: (c.confianza, str(c.id)))
    return TransitionIntent(
        productor="kernel",
        operacion="registrar_deliberacion",
        argumentos={
            "participantes": participantes,
            "resultado": Resuelta(
                regla=REGLA_POLITICA_V1,
                aceptados=(ganador.id,),
                confianza=ganador.confianza,
            ),
        },
        base=estado.transicion,
    )


def derivar_decision(estado: LearningState) -> TransitionIntent | None:
    """Deriva la decisión de la primera deliberación resuelta sin decisión."""
    con_decision = {d.origen for d in estado.decisiones}
    for deliberacion in estado.deliberaciones:
        if not isinstance(deliberacion.resultado, Resuelta):
            continue
        if deliberacion.id in con_decision:
            continue
        aceptado = estado.buscar(deliberacion.resultado.aceptados[0])
        return TransitionIntent(
            productor="kernel",
            operacion="registrar_decision",
            argumentos={
                "origen": deliberacion.id,
                "contenido": dict(aceptado.afirmacion),
            },
            base=estado.transicion,
        )
    return None
