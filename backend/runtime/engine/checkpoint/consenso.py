"""engine.checkpoint.consenso — Landscape/Consensus Metrics (RFC-0007
§2.2, fila "Consenso (RFC-0006)"); RFC-0006 §8, H10 ("distintas
versiones de política... producen dinámicas de adaptación medibles y
comparables — incluso sobre las mismas sesiones, vía replay con
política alternativa. Se evalúa... con los instrumentos del RFC-0007").

Mismo régimen que `engine/checkpoint/paisaje.py`: función pura sobre
`(Replay, Politica)`, cero mutación, cero I/O nuevo, cero sección nueva
del `LearningState` — una proyección de lectura sobre `deliberaciones` y
`decisiones` (ambas append-only, RFC-0003 §2), no un almacén paralelo.

Nombre deliberado: `MetricasConsenso`, nunca `ConsensusEngine` — ese
nombre perteneció al sistema de votación legacy en `app/core/consensus.py`
(retirado del flujo en vivo por ADR-0011, retirado físicamente por
ADR-0017) y reutilizarlo aquí confundiría dos mecanismos que no
tuvieron relación."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from runtime.engine.checkpoint.reconstruccion import Replay
from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import Politica
from runtime.kernel.state.entries import (
    Aplazada,
    ClaimEntry,
    DecisionEntry,
    DeliberacionEntry,
    Escalada,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import LearningState


@dataclass(frozen=True, slots=True)
class MetricasConsenso:
    """Resumen de consenso de una sesión completa (RFC-0007 §2.2, fila
    "Consenso") — proyección de lectura sobre `deliberaciones`/
    `decisiones`, nunca una sección nueva del estado (mismo principio
    que `Paisaje`, CONCEPT-0001). A diferencia de `Paisaje`, esto es un
    resumen sobre TODA la sesión, no una serie por transición: el
    consenso no tiene un "instante" — un episodio o ya ocurrió o no."""

    convocatorias: int
    """Episodios de deliberación registrados (RFC-0006 §4) — cada
    `DeliberacionEntry` de la sesión es una convocatoria; solo existe
    cuando `tension_bloqueante()` encontró rivalidad real."""

    no_convocatorias: int
    """Decisiones derivadas directamente de una propuesta única sin
    rival (RFC-0006 §3, D3 — `derivar_decision_directa`): el sistema
    decidió sin necesitar convocar consenso. Artefacto positivo y
    persistido (la propia `DecisionEntry` cuyo origen es un claim, no
    una deliberación) — "no-convocatoria REGISTRADA" (RFC-0007 §2.2,
    énfasis del propio RFC: no es la ausencia de un evento, es un
    evento distinto ya persistido)."""

    resueltas: int
    aplazadas: int
    escaladas: int
    """Conteo bruto por tipo de resultado (RFC-0006 §4) — la proporción
    es cálculo del consumidor, no de este módulo."""

    margenes_resolucion: tuple[Decimal, ...]
    """Un margen por cada deliberación `Resuelta` o `Aplazada` — ver
    `_margen`. Ninguna `Escalada` aporta margen (ver su docstring)."""

    confianza_resolucion: tuple[Decimal, ...]
    """`Resuelta.confianza` de cada deliberación resuelta, verbatim: el
    `ce` del ganador que `mecanica.convocar()` ya calculó y persistió
    (RFC-0006 §4) — sin recomputar nada."""

    longitud_cadenas_reconvocacion: tuple[int, ...]
    """Cantidad de episodios `Aplazada` en cada cadena `enlaza_a`
    (CONCEPT-0002 §5) que tuvo al menos una reconvocatoria — una
    entrada por cadena; cadenas sin ningún aplazamiento (resueltas o
    escaladas en el primer episodio) quedan excluidas."""


def _peso(tipo: TipoClaim, asunto: str, politica: Politica) -> Decimal:
    """Mismo criterio que `mecanica.convocar()` (RFC-0006 §4, D2:
    "puntaje = confianza efectiva × peso de política pedagógica para
    ese asunto"): D1 nunca pondera (peso 1 siempre); D2 usa el peso
    registrado para el asunto, o 1 si no hay entrada (neutro)."""
    if tipo is not TipoClaim.PROPUESTA:
        return Decimal("1")
    return politica.pesos_asunto.get(asunto, Decimal("1"))


def _estado_en_transicion(replay: Replay, transicion: int) -> LearningState | None:
    for paso in replay:
        if paso.transicion == transicion:
            return paso.estado
    return None


def _margen(
    deliberacion: DeliberacionEntry, estado: LearningState, politica: Politica
) -> Decimal | None:
    """El margen entre el puntaje del ganador y el de su rival más
    cercano, tal como lo vio `mecanica.convocar()` al resolver esta
    deliberación (RFC-0006 §4) — recalculado con la MISMA función
    pública (`calcular_confianza_efectiva`, nunca reimplementada) sobre
    el estado tal como quedó en la transición que registró esta
    deliberación: los participantes no cambian después (son claims
    inmutables ya existentes), así que cualquier estado desde esa
    transición en adelante los ve igual.

    Solo se calcula para `Resuelta`/`Aplazada` — ambas SIEMPRE pasan
    por el cálculo de puntajes (RFC-0006 §4). Una `Escalada` puede
    haber llegado por dos vías: RESERVA (la política le quita la
    autoridad a la mecánica ANTES de comparar nada — no hay margen que
    observar) o LÍMITE (sí lo calculó, y coincide con el último margen
    insuficiente ya aplazado). Distinguir ambas vías exigiría
    reproducir la verificación de `asuntos_reservados` fuera de
    `mecanica.py` — duplicar una RAMA DE DECISIÓN, no una
    clasificación de lectura como `_cabezas_de_cadena` — se deja fuera
    por ese motivo: `None` para toda `Escalada`."""
    if not isinstance(deliberacion.resultado, (Resuelta, Aplazada)):
        return None
    participantes = [estado.buscar(p) for p in deliberacion.participantes]
    if any(not isinstance(p, ClaimEntry) for p in participantes):
        return None
    asunto = participantes[0].asunto
    tipo = participantes[0].tipo
    puntajes = sorted(
        (
            calcular_confianza_efectiva(p, estado, politica) * _peso(tipo, asunto, politica)
            for p in participantes
        ),
        reverse=True,
    )
    return puntajes[0] - puntajes[1]


def _es_no_convocatoria(decision: DecisionEntry, estado: LearningState) -> bool:
    """RFC-0006 §3, D3 (`derivar_decision_directa`): una decisión cuyo
    origen es un claim-propuesta único, nunca una deliberación — el
    sistema decidió sin necesitar convocar consenso."""
    origen = estado.buscar(decision.origen)
    return isinstance(origen, ClaimEntry)


def _cabezas_de_cadena(estado: LearningState) -> tuple[DeliberacionEntry, ...]:
    """Toda deliberación que NO es el `enlaza_a` de ninguna otra — el
    eslabón más reciente de su cadena, resuelta o no (a diferencia de
    `mecanica._cabezas_abiertas`, que solo cuenta las SIN resolver: aquí
    se quiere la longitud de TODA cadena, incluidas las que terminaron
    en `Resuelta` tras uno o más aplazamientos)."""
    enlazadas = {d.enlaza_a for d in estado.deliberaciones if d.enlaza_a is not None}
    return tuple(d for d in estado.deliberaciones if d.id not in enlazadas)


def _longitud_cadena(cabeza: DeliberacionEntry, estado: LearningState) -> int:
    """Cuenta los episodios `Aplazada` de la cadena que termina en
    `cabeza`, siguiendo `enlaza_a` hacia atrás — mismo criterio que
    `mecanica._aplazamientos_en_cadena` (CONCEPT-0002 §5), generalizado
    a cadenas ya cerradas (no solo a las que siguen abiertas)."""
    contador = 0
    actual: DeliberacionEntry | None = cabeza
    while actual is not None:
        if isinstance(actual.resultado, Aplazada):
            contador += 1
        actual = estado.buscar(actual.enlaza_a) if actual.enlaza_a is not None else None
    return contador


def derivar_consenso(replay: Replay, politica: Politica) -> MetricasConsenso:
    """Proyección de lectura sobre `LearningState.deliberaciones`/
    `.decisiones` en el ÚLTIMO paso del `Replay` — a diferencia de
    `derivar_paisaje` (Landscape/H8), esto es un resumen sobre TODO lo
    ya ocurrido en la sesión, no una serie por transición. El margen de
    cada resolución sí necesita el estado tal como quedó en SU propia
    transición (ver `_margen`), así que recorre `replay` para
    localizarlo — sin volver a tocar Postgres ni el grafo."""
    if not replay:
        return MetricasConsenso(
            convocatorias=0,
            no_convocatorias=0,
            resueltas=0,
            aplazadas=0,
            escaladas=0,
            margenes_resolucion=(),
            confianza_resolucion=(),
            longitud_cadenas_reconvocacion=(),
        )
    estado_final = replay[-1].estado

    resueltas = aplazadas = escaladas = 0
    margenes: list[Decimal] = []
    confianzas: list[Decimal] = []
    for deliberacion in estado_final.deliberaciones:
        if isinstance(deliberacion.resultado, Resuelta):
            resueltas += 1
            confianzas.append(deliberacion.resultado.confianza)
        elif isinstance(deliberacion.resultado, Aplazada):
            aplazadas += 1
        elif isinstance(deliberacion.resultado, Escalada):
            escaladas += 1
        estado_transicion = (
            _estado_en_transicion(replay, deliberacion.id.transicion) or estado_final
        )
        margen = _margen(deliberacion, estado_transicion, politica)
        if margen is not None:
            margenes.append(margen)

    no_convocatorias = sum(
        1 for d in estado_final.decisiones if _es_no_convocatoria(d, estado_final)
    )

    cadenas = tuple(
        longitud
        for cabeza in _cabezas_de_cadena(estado_final)
        if (longitud := _longitud_cadena(cabeza, estado_final)) > 0
    )

    return MetricasConsenso(
        convocatorias=len(estado_final.deliberaciones),
        no_convocatorias=no_convocatorias,
        resueltas=resueltas,
        aplazadas=aplazadas,
        escaladas=escaladas,
        margenes_resolucion=tuple(margenes),
        confianza_resolucion=tuple(confianzas),
        longitud_cadenas_reconvocacion=cadenas,
    )
