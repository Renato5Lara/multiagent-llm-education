"""Convocatoria y resolución (RFC-0006 §3–§4; política politica-v1).

Todo aquí es función pura de `(estado, política)` (P12): sin reloj, sin
azar, sin LLM. `tension_bloqueante()` clasifica D1/D2 (RFC-0006 §3,
CONCEPT-0002 §1; Parte B). `convocar()` resuelve por tipo (RFC-0006 §4,
Parte D): D1 por `ce` directo, D2 por `ce × peso de política` — la
regla de politica-v1, `mayor-confianza-declarada`, queda registrada por
nombre en cada resolución (INV-7); los desempates son deterministas
(orden textual del id). `derivar_decision_directa()` deriva decisión de
una propuesta única bajo el umbral θ (RFC-0006 §3, D3; Parte C).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import Politica
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


def convocar(estado: LearningState, politica: Politica) -> TransitionIntent | None:
    """Resuelve la tensión bloqueante por tipo (RFC-0006 §4, Parte D):
    D1 (interpretativo) compara `ce` directamente; D2 (prescriptivo)
    pondera `ce × peso de política pedagógica del asunto`
    (`politica.pesos_asunto`, neutro=1 si el asunto no está registrado).
    El ganador es el de mayor puntaje; si el margen sobre el rival no
    alcanza `politica.delta`, NO se resuelve — margen insuficiente es
    Parte E (aplazamiento/decisión provisional, no implementada
    todavía). `Resuelta.confianza` guarda el `ce` crudo del ganador, no
    el puntaje ponderado — así siempre respeta [0,1] (INV-7) sin
    importar el peso, y su significado ("cuánta confianza merece el
    claim ganador") no cambia entre D1 y D2.

    Bajo `"v1"` (delta=0, pesos_asunto vacío): el margen entre dos
    puntajes nunca es negativo, así que `margen >= delta=0` siempre se
    cumple — nunca se difiere. Y con todo peso neutro (=1), el puntaje
    de D2 es literalmente `ce`, igual que D1 — la comparación se reduce
    exactamente a "mayor ce gana", que para v1 (ce == confianza
    declarada, RFC-0006/1) es matemáticamente `mayor-confianza-
    declarada` — de ahí que `REGLA_POLITICA_V1` siga siendo el nombre
    correcto para registrar, no solo el histórico."""
    tension = tension_bloqueante(estado)
    if tension is None:
        return None
    tipo, asunto, participantes = tension
    claims = [estado.buscar(ref) for ref in participantes]
    ces = {c.id: calcular_confianza_efectiva(c, estado, politica) for c in claims}
    peso = politica.pesos_asunto.get(asunto, Decimal("1")) if tipo == "D2" else Decimal("1")
    puntajes = {claim_id: ce * peso for claim_id, ce in ces.items()}

    ordenados = sorted(claims, key=lambda c: (puntajes[c.id], str(c.id)), reverse=True)
    ganador, rival = ordenados[0], ordenados[1]
    margen = puntajes[ganador.id] - puntajes[rival.id]
    if margen < politica.delta:
        return None

    return TransitionIntent(
        productor="kernel",
        operacion="registrar_deliberacion",
        argumentos={
            "participantes": participantes,
            "resultado": Resuelta(
                regla=REGLA_POLITICA_V1,
                aceptados=(ganador.id,),
                confianza=ces[ganador.id],
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


def derivar_decision_directa(
    estado: LearningState, politica: Politica
) -> TransitionIntent | None:
    """Propuesta única deriva decisión directa si `ce` alcanza θ (RFC-0006
    §3, D3; RFC-0003 INV-6, "el origen de una decisión es ... el
    claim-propuesta único"; ROADMAP-RFC-0006 Parte C).

    Corrección de un bug preexistente, no una capacidad nueva desde
    cero: `registrar_decision` ya aceptaba un origen `ClaimEntry` desde
    RFC-0003 — nada en el grafo lo invocaba así. Antes de esta función,
    un asunto con una única propuesta vigente (sin rival, por lo tanto
    nunca convocado por `tension_bloqueante`/`convocar`) nunca derivaba
    decisión: el ejemplo real es `"siguiente-paso(sesion)"` cuando
    `dominada=True` — Orientar propone solo, Remediar nunca compite, y
    el walkthrough terminaba en `END` sin decisión ni Adaptar.

    Solo considera asuntos con EXACTAMENTE una propuesta vigente — un
    asunto con ≥2 es tensión (`tension_bloqueante`, ya resuelto por
    `convocar`/`derivar_decision`, con prioridad: `enrutar()` solo llama
    a esta función cuando ya no hay tensión bloqueante ni deliberación
    pendiente). Si `ce < theta`: insuficiencia (D3) — no deriva nada;
    el "camino de evidencia" que RFC-0006 §3 describe (enrutar hacia
    Evaluar) no es un nodo del grafo hoy (Evaluar es entrada externa,
    E2 — RFC-0010), así que la insuficiencia se traduce, por ahora, en
    que el walkthrough termina sin decisión y espera una reanudación
    con más evidencia (mismo patrón ya documentado en
    `ejecutar_walkthrough`: "`END` sin evidencia suficiente aún")."""
    con_decision = {d.origen for d in estado.decisiones}
    por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
    for claim in _claims_vigentes_de(estado, TipoClaim.PROPUESTA):
        por_asunto[claim.asunto].append(claim)
    for asunto in sorted(por_asunto):
        candidatos = por_asunto[asunto]
        if len(candidatos) != 1:
            continue
        claim = candidatos[0]
        if claim.id in con_decision:
            continue
        ce = calcular_confianza_efectiva(claim, estado, politica)
        if ce < politica.theta:
            continue
        return TransitionIntent(
            productor="kernel",
            operacion="registrar_decision",
            argumentos={
                "origen": claim.id,
                "contenido": dict(claim.afirmacion),
            },
            base=estado.transicion,
        )
    return None
