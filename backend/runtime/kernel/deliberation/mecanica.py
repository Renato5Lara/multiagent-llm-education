"""Convocatoria y resolución mínimas (RFC-0006 §3–§4; política politica-v1).

Todo aquí es función pura del estado (P12): sin reloj, sin azar, sin LLM.
La regla de politica-v1 — `mayor-confianza-declarada` — queda registrada
por nombre en cada resolución (INV-7); los desempates son deterministas
(orden textual del id).

`tension_bloqueante()` clasifica D1/D2 (RFC-0006 §3, CONCEPT-0002 §1;
ROADMAP-RFC-0006 Parte B) — pero `convocar()` todavía resuelve ambas
igual (`REGLA_POLITICA_V1`): distinguir el tipo sin resolver distinto
es exactamente el alcance de esta pieza; la resolución por tipo (D1 por
margen δ, D2 por peso de política) es Parte D, no aquí.
"""

from __future__ import annotations

from collections import defaultdict

from runtime.kernel.state.entries import ClaimEntry, EntryId, Resuelta, TipoClaim
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

REGLA_POLITICA_V1 = "mayor-confianza-declarada"

_TIPOS_EN_ORDEN = (("D1", TipoClaim.INTERPRETACION), ("D2", TipoClaim.PROPUESTA))
"""D1 antes que D2 al escanear: "los desacuerdos prescriptivos suelen
tener raíz interpretativa... se resuelve D1 antes que D2" (CONCEPT-0002
§1). Esto NO implementa la regla de la raíz completa (H7, Parte G) — es
solo el orden en que esta función encuentra una tensión candidata
cuando hay más de una simultánea; Parte G decide qué hacer con esa
prioridad de verdad, no esta función."""


def _claims_vigentes_de(estado: LearningState, tipo: TipoClaim) -> tuple[ClaimEntry, ...]:
    return tuple(c for c in estado.claims if c.tipo is tipo and c.vigencia.vigente)


def tension_bloqueante(
    estado: LearningState,
) -> tuple[str, str, tuple[EntryId, ...]] | None:
    """(tipo, asunto, participantes) — RFC-0006 §3, CONCEPT-0002 §1.
    `tipo` es "D1" (≥2 `INTERPRETACION` vigentes rivales del mismo
    asunto) o "D2" (≥2 `PROPUESTA` vigentes rivales del mismo asunto) —
    mismo criterio de rivalidad que antes (≥2 vigentes, mismo asunto),
    ahora aplicado también a `INTERPRETACION`, no solo a `PROPUESTA`."""
    for tipo, filtro in _TIPOS_EN_ORDEN:
        por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
        for claim in _claims_vigentes_de(estado, filtro):
            por_asunto[claim.asunto].append(claim)
        for asunto in sorted(por_asunto):
            rivales = por_asunto[asunto]
            if len(rivales) >= 2:
                return tipo, asunto, tuple(sorted((c.id for c in rivales), key=str))
    return None


def convocar(estado: LearningState) -> TransitionIntent | None:
    """Resuelve la tensión bloqueante bajo politica-v1 y propone el episodio.
    Ignora `tipo` deliberadamente: D1 y D2 se resuelven igual hasta
    Parte D (ROADMAP-RFC-0006) — clasificar sin resolver distinto es el
    alcance exacto de Parte B."""
    tension = tension_bloqueante(estado)
    if tension is None:
        return None
    _, _, participantes = tension
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
