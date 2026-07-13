"""Convocatoria y resolución (RFC-0006 §3–§4; política politica-v1).

Todo aquí es función pura de `(estado, política)` (P12): sin reloj, sin
azar, sin LLM. `tension_bloqueante()` clasifica D1/D2 (RFC-0006 §3,
CONCEPT-0002 §1; Parte B). `convocar()` resuelve por tipo (RFC-0006 §4,
Partes D, E y F): D1 por `ce` directo, D2 por `ce × peso de política`;
si el margen no alcanza δ, aplaza declarando la evidencia que falta —
o resuelve provisionalmente si el slot es urgente (Parte E) — o escala
al docente (Parte F: asunto reservado por política, o límite de
reconvocatoria agotado en la cadena `enlaza_a`). La regla aplicada
queda registrada por nombre en cada resolución (INV-7); los desempates
son deterministas (orden textual del id).
`derivar_decision_directa()` deriva decisión de una propuesta única
bajo el umbral θ (RFC-0006 §3, D3; Parte C).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import Politica
from runtime.kernel.state.entries import (
    Aplazada,
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    EntryId,
    Escalada,
    Resuelta,
    ResultadoDeliberacion,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState
from runtime.kernel.transitions import TransitionIntent

REGLA_POLITICA_V1 = "mayor-confianza-declarada"

REGLA_PROVISIONAL = "provisional-por-urgencia"
"""Resolución provisional (RFC-0006 §4; CONCEPT-0002 §4/§5 bis): "no es
un concepto nuevo: es una decisión con confianza de resolución baja,
que INV-12 ya obliga a validar". Un nombre más del catálogo de reglas
de RFC-0006 — mismo estatus que `"decision-humana"` en
`boundary/inbound/escalada.py` — nunca un tipo de resultado nuevo."""

_TIPOS_EN_ORDEN = (("D1", TipoClaim.INTERPRETACION), ("D2", TipoClaim.PROPUESTA))
"""D1 antes que D2 al escanear: "los desacuerdos prescriptivos suelen
tener raíz interpretativa... se resuelve D1 antes que D2" (CONCEPT-0002
§1). Esto NO implementa la regla de la raíz completa (H7, Parte G) — es
solo el orden en que esta función encuentra una tensión candidata
cuando hay más de una simultánea; Parte G decide qué hacer con esa
prioridad de verdad, no esta función."""


def _claims_vigentes_de(estado: LearningState, tipo: TipoClaim) -> tuple[ClaimEntry, ...]:
    return tuple(c for c in estado.claims if c.tipo is tipo and c.vigencia.vigente)


def _cabezas_abiertas(estado: LearningState) -> dict[str, DeliberacionEntry]:
    """Asunto → su deliberación abierta: aplazada (espera el camino de
    evidencia, CONCEPT-0002 §4) o escalada (espera la autoridad humana,
    RFC-0009 §3), sin ninguna deliberación posterior `enlaza_a` ella.
    No hay reapertura (INV-3, P14): lo que cierra una cabeza es siempre
    una NUEVA deliberación enlazada — la resolución humana la produce
    `boundary/inbound/escalada.py`; la reconvocatoria por evidencia
    nueva la produce `convocar` (Parte F). A lo sumo una cabeza por
    asunto, por construcción: toda deliberación nueva sobre un asunto
    con cabeza nace enlazada a ella."""
    enlazadas = {d.enlaza_a for d in estado.deliberaciones if d.enlaza_a is not None}
    cabezas: dict[str, DeliberacionEntry] = {}
    for deliberacion in estado.deliberaciones:
        if isinstance(deliberacion.resultado, Resuelta):
            continue
        if deliberacion.id in enlazadas:
            continue
        participante = estado.buscar(deliberacion.participantes[0])
        cabezas[participante.asunto] = deliberacion
    return cabezas


def _aplazamientos_en_cadena(
    estado: LearningState, cabeza: DeliberacionEntry | None
) -> int:
    """Cuántas `Aplazada` acumula la cadena `enlaza_a` que termina en
    `cabeza` (CONCEPT-0002 §5: "la cadena deliberación → deliberación'
    es, ella misma, evidencia longitudinal"). Se sigue el enlace hacia
    atrás — nunca se cuentan deliberaciones sueltas del mismo asunto
    como si fueran la misma cadena (ROADMAP-RFC-0006 Parte F: ese es el
    error sutil que este recorrido evita)."""
    contador = 0
    actual = cabeza
    while actual is not None:
        if isinstance(actual.resultado, Aplazada):
            contador += 1
        actual = (
            estado.buscar(actual.enlaza_a) if actual.enlaza_a is not None else None
        )
    return contador


def tension_bloqueante(
    estado: LearningState,
) -> tuple[str, str, tuple[EntryId, ...]] | None:
    """(tipo, asunto, participantes) — RFC-0006 §3, CONCEPT-0002 §1.
    `tipo` es "D1" (≥2 `INTERPRETACION` vigentes rivales del mismo
    asunto) o "D2" (≥2 `PROPUESTA` vigentes rivales del mismo asunto) —
    mismo criterio de rivalidad que antes (≥2 vigentes, mismo asunto),
    ahora aplicado también a `INTERPRETACION`, no solo a `PROPUESTA`.

    Con cabeza abierta (Parte E/F): una tensión ESCALADA jamás vuelve a
    ser bloqueante — resolverla por mecánica sería el bypass que
    RFC-0009 §3 prohíbe; solo la cierra el docente (E3). Una tensión
    APLAZADA vuelve a ser bloqueante únicamente cuando el paisaje del
    asunto cambió — el conjunto de rivales vigentes difiere de los
    participantes registrados en la cabeza (CONCEPT-0002 §5: "llega la
    evidencia declarada faltante" / "aparece una nueva propuesta rival";
    la cascada que tumba un participante y la re-propuesta que lo
    reemplaza son exactamente ese cambio). Con el paisaje idéntico,
    reconvocar reproduciría la misma resolución bit a bit (los `ce` de
    una tensión aplazada no pueden variar sin evidencia nueva en su
    cadena — sin decisión derivada no hay refuerzo, refutación ni ancla
    de decaimiento): sería churn, no consenso."""
    cabezas = _cabezas_abiertas(estado)
    for tipo, filtro in _TIPOS_EN_ORDEN:
        por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
        for claim in _claims_vigentes_de(estado, filtro):
            por_asunto[claim.asunto].append(claim)
        for asunto in sorted(por_asunto):
            rivales = por_asunto[asunto]
            if len(rivales) < 2:
                continue
            participantes = tuple(sorted((c.id for c in rivales), key=str))
            cabeza = cabezas.get(asunto)
            if cabeza is not None:
                if isinstance(cabeza.resultado, Escalada):
                    continue
                if cabeza.participantes == participantes:
                    continue
            return tipo, asunto, participantes
    return None


def convocar(
    estado: LearningState, politica: Politica, urgente: bool = False
) -> TransitionIntent | None:
    """Resuelve la tensión bloqueante por tipo (RFC-0006 §4, Partes D+E):
    D1 (interpretativo) compara `ce` directamente; D2 (prescriptivo)
    pondera `ce × peso de política pedagógica del asunto`
    (`politica.pesos_asunto`, neutro=1 si el asunto no está registrado).
    El ganador es el de mayor puntaje. `Resuelta.confianza` guarda el
    `ce` crudo del ganador, no el puntaje ponderado — así siempre
    respeta [0,1] (INV-7) sin importar el peso, y su significado
    ("cuánta confianza merece el claim ganador") no cambia entre D1 y D2.

    Margen < δ (Parte E): la regla no puede discriminar. Si nadie espera
    (`urgente=False`), se aplaza declarando QUÉ evidencia discriminaría
    (INV-7; CONCEPT-0002 §4: "el aplazamiento es productivo"). Si el
    slot es urgente — hay un estudiante esperando la entrega en la
    pantalla; información del Boundary, jamás de `estado.ejecucion`
    (ROADMAP-RFC-0006 §5/2) — se resuelve con el mejor claim disponible
    como decisión provisional (`REGLA_PROVISIONAL`): la confianza
    registrada sigue siendo el `ce` del ganador ("la mejor confianza
    disponible", ROADMAP Parte E) y la decisión derivada queda, como
    todas, pendiente-de-validación (INV-12). Siempre que hay tensión se
    registra un resultado — el espacio es cerrado (CONCEPT-0002 §5 bis),
    y el grafo jamás cicla en "deliberar" sin avance.

    Escalada (RFC-0006 §4, Parte F) — dos vías, ambas de política:
    (1) RESERVA: una tensión sobre un asunto de
    `politica.asuntos_reservados` se escala sin computar resolución —
    la política le quitó a la mecánica la autoridad sobre ese asunto, y
    ni la urgencia la devuelve (resolver provisionalmente lo reservado
    sería el bypass de RFC-0009 §3); (2) LÍMITE DE RECONVOCATORIA: si
    la cadena `enlaza_a` ya acumula `limite_reconvocatoria` aplazadas y
    el margen sigue sin discriminar, el resultado es `Escalada` —
    "ninguna deliberación puede diferirse para siempre". La urgencia sí
    precede al límite (CONCEPT-0002 §4: "la provisionalidad es para el
    estudiante" — escalar es esperar a una persona, y el estudiante no
    puede esperar). Toda deliberación sobre un asunto con cabeza
    abierta nace `enlaza_a` ella (CONCEPT-0002 §5: jamás reapertura) —
    la cadena resultante es la evidencia longitudinal que S2/Replay
    exhiben.

    Bajo `"v1"` (delta=0, pesos_asunto vacío, sin asuntos reservados):
    el margen entre dos puntajes nunca es negativo, así que
    `margen >= delta=0` siempre se cumple — las Partes E y F son
    estructuralmente inalcanzables y la comparación se reduce a "mayor
    ce gana", que para v1 (ce == confianza declarada, RFC-0006/1) es
    matemáticamente `mayor-confianza-declarada` — de ahí que
    `REGLA_POLITICA_V1` siga siendo el nombre correcto para registrar,
    no solo el histórico."""
    tension = tension_bloqueante(estado)
    if tension is None:
        return None
    tipo, asunto, participantes = tension
    cabeza = _cabezas_abiertas(estado).get(asunto)

    resultado: ResultadoDeliberacion
    if asunto in politica.asuntos_reservados:
        resultado = Escalada()
    else:
        claims = [estado.buscar(ref) for ref in participantes]
        ces = {c.id: calcular_confianza_efectiva(c, estado, politica) for c in claims}
        peso = politica.pesos_asunto.get(asunto, Decimal("1")) if tipo == "D2" else Decimal("1")
        puntajes = {claim_id: ce * peso for claim_id, ce in ces.items()}

        ordenados = sorted(claims, key=lambda c: (puntajes[c.id], str(c.id)), reverse=True)
        ganador, rival = ordenados[0], ordenados[1]
        margen = puntajes[ganador.id] - puntajes[rival.id]

        if margen >= politica.delta:
            resultado = Resuelta(
                regla=REGLA_POLITICA_V1,
                aceptados=(ganador.id,),
                confianza=ces[ganador.id],
            )
        elif urgente:
            resultado = Resuelta(
                regla=REGLA_PROVISIONAL,
                aceptados=(ganador.id,),
                confianza=ces[ganador.id],
            )
        elif (
            _aplazamientos_en_cadena(estado, cabeza)
            >= politica.limite_reconvocatoria
        ):
            resultado = Escalada()
        else:
            resultado = Aplazada(
                evidencia_faltante=(
                    f"evidencia sobre '{asunto}' que discrimine entre "
                    f"{ganador.id} y {rival.id}: margen {margen} < "
                    f"delta {politica.delta}"
                )
            )

    argumentos: dict = {"participantes": participantes, "resultado": resultado}
    if cabeza is not None:
        argumentos["enlaza_a"] = cabeza.id
    return TransitionIntent(
        productor="kernel",
        operacion="registrar_deliberacion",
        argumentos=argumentos,
        base=estado.transicion,
    )


def derivar_decision(estado: LearningState) -> TransitionIntent | None:
    """Deriva la decisión de la primera deliberación resuelta sin
    decisión — SOLO si aceptó una PROPUESTA (INV-6: "las decisiones
    derivan de propuestas"). Una resolución D1 (interpretaciones en
    tensión) refina el paisaje, jamás deriva decisión: su efecto es la
    interpretación ganadora + la cascada sobre lo respaldado en la
    perdedora — el ciclo continúa por re-propuesta, no por derivación."""
    con_decision = {d.origen for d in estado.decisiones}
    for deliberacion in estado.deliberaciones:
        if not isinstance(deliberacion.resultado, Resuelta):
            continue
        if deliberacion.id in con_decision:
            continue
        aceptado = estado.buscar(deliberacion.resultado.aceptados[0])
        if not isinstance(aceptado, ClaimEntry) or aceptado.tipo is not TipoClaim.PROPUESTA:
            continue
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
    pendiente). Un asunto cuya decisión vigente conserva su suelo (el
    claim del que deriva sigue vigente) tampoco deriva de nuevo — solo
    cuando la cascada (2026-07-13) tumbó ese suelo, la propuesta única
    fresca reemplaza a la decisión obsoleta (y `registrar_decision` la
    supersede). Si `ce < theta`: insuficiencia (D3) — no deriva nada;
    el "camino de evidencia" que RFC-0006 §3 describe (enrutar hacia
    Evaluar) no es un nodo del grafo hoy (Evaluar es entrada externa,
    E2 — RFC-0010), así que la insuficiencia se traduce, por ahora, en
    que el walkthrough termina sin decisión y espera una reanudación
    con más evidencia (mismo patrón ya documentado en
    `ejecutar_walkthrough`: "`END` sin evidencia suficiente aún")."""
    con_decision = {d.origen for d in estado.decisiones}
    asuntos_con_decision_firme = set()
    for decision in estado.decisiones:
        if not decision.vigencia.vigente:
            continue
        origen = estado.buscar(decision.origen)
        if isinstance(origen, DeliberacionEntry) and isinstance(
            origen.resultado, Resuelta
        ):
            origen = estado.buscar(origen.resultado.aceptados[0])
        if isinstance(origen, ClaimEntry) and origen.vigencia.vigente:
            asuntos_con_decision_firme.add(decision.asunto)
    def _ejecuta_una_decision(claim: ClaimEntry) -> bool:
        """Un claim cuyo respaldo referencia una DECISIÓN no propone un
        siguiente paso: EJECUTA uno ya decidido (la adaptación de
        Adaptar, RFC-0002 R7). Derivar una decisión de él crearía
        cadenas decisión→claim→decisión sin deliberación de por medio."""
        return any(
            isinstance(estado.buscar(ref), DecisionEntry) for ref in claim.respaldo
        )

    por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
    for claim in _claims_vigentes_de(estado, TipoClaim.PROPUESTA):
        por_asunto[claim.asunto].append(claim)
    for asunto in sorted(por_asunto):
        candidatos = por_asunto[asunto]
        if len(candidatos) != 1:
            continue
        if asunto in asuntos_con_decision_firme:
            continue
        claim = candidatos[0]
        if claim.id in con_decision:
            continue
        if _ejecuta_una_decision(claim):
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
