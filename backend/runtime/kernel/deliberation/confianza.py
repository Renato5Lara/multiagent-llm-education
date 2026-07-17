"""kernel.deliberation.confianza — la confianza efectiva (RFC-0006 §1,
axiomas A1-A8; ROADMAP-RFC-0006 Parte A).

Función pura sobre `(claim, estado, politica)` — nunca importa
`mecanica.py` (la mecánica de deliberación es quien USARÁ esta función
desde RFC-0006/3 en adelante, no de quien esta función depende), nunca
ejecuta el grafo, nunca toca Postgres, nunca invoca un modelo, un reloj
de pared o el azar (A3: determinismo y pureza — mismo input, mismo
output, sin importar cuándo se llame).

**Garantías de esta implementación, una por axioma:**

- **A1 (Acotación):** `ce` siempre en `[0, 1]` — el `max`/`min` final
  de `calcular_confianza_efectiva` lo hace incondicional, sin excepción
  de camino.
- **A2 (Anclaje):** en el instante en que un claim se registra
  (`estado.transicion == claim.id.transicion`), no hay decisiones
  derivadas ni validaciones todavía — refuerzos=0, refutaciones=0,
  edad=0 — así que `ce` es exactamente `claim.confianza`, la declarada.
- **A3 (Determinismo y pureza):** ver arriba.
- **A4 (Tiempo lógico):** toda noción de "edad" se mide en índices de
  transición (`estado.transicion`, `EntryId.transicion`) — nunca en
  reloj de pared.
- **A5 (Monotonicidad ante evidencia):** una validación positiva en la
  cadena causal del claim solo puede sumar (`+ politica.peso_refuerzo`,
  nunca resta); una negativa solo puede restar
  (`- politica.peso_refutacion`) — los signos de la fórmula son fijos,
  nunca se invierten según el estado. El término de contradicción ("un
  fact contradictorio con su respaldo no la aumenta") **no se
  implementa todavía** — no hay ningún criterio normativo de qué hace a
  un fact "contradictorio" con un claim (RFC-0006 no lo especifica;
  probablemente nace junto con la detección real de tensión D1,
  RFC-0006/2). Al no implementarse, esa cláusula de A5 se satisface
  vacuamente (nunca se viola porque nunca se ejerce) — es una función
  con menos entradas de las que el RFC anticipa como posibles, no una
  violación del contrato. Se amplía cuando haga falta.
- **A6 (Decaimiento sin refuerzo):** sin evidencia nueva, `ce` no crece
  — ver `edad_logica` en `calcular_confianza_efectiva`.
- **A7 (Localidad causal):** `ce` solo lee la cadena causal del claim
  (su respaldo hacia atrás, las decisiones/validaciones derivadas hacia
  adelante) — nunca `estado.transicion` en bruto ni entradas de otros
  asuntos. Ver la nota "corrección encontrada durante la
  implementación" en `calcular_confianza_efectiva` — un test real de
  este axioma (`TestA7_LocalidadCausal`) refutó una primera versión de
  A4/A6 que sí violaba A7.
- **A8 (La vigencia domina):** la vigencia es una precondición del
  llamador — esta función no la valida, no la conoce, no la filtra;
  opera sobre un dominio ya restringido a claims vigentes por quien
  llama (`mecanica.py`, RFC-0006/3), nunca por sí misma.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.deliberation.politica import Politica
from runtime.kernel.state.entries import Capacidad, ClaimEntry, DeliberacionEntry, EntryId, Resuelta
from runtime.kernel.state.state import LearningState

_CERO = Decimal("0")
_UNO = Decimal("1")


def _decisiones_originadas_por(claim_id: EntryId, estado: LearningState) -> set[EntryId]:
    """Decisiones cuyo origen es este claim — directamente (propuesta
    única, INV-6) o a través de una deliberación que lo aceptó
    (`Resuelta.aceptados`, INV-7). Parte de la cadena causal "hacia
    adelante" que A7 autoriza a leer."""
    ids: set[EntryId] = set()
    for decision in estado.decisiones:
        if decision.origen == claim_id:
            ids.add(decision.id)
            continue
        origen = estado.buscar(decision.origen)
        if (
            isinstance(origen, DeliberacionEntry)
            and isinstance(origen.resultado, Resuelta)
            and claim_id in origen.resultado.aceptados
        ):
            ids.add(decision.id)
    return ids


def _validaciones_de(
    decision_ids: set[EntryId], estado: LearningState
) -> tuple[int, int, int | None]:
    """(refuerzos, refutaciones, última transición relevante) — cuenta
    los claims de Validar (vigentes) cuyo `respaldo` referencia alguna
    de estas decisiones, clasificados por `afirmacion["funciono"]` (el
    veredicto de Validar, RFC-0003/Walkthrough-0001, no un campo nuevo),
    y recuerda en qué transición ocurrió la más reciente — el ancla que
    `calcular_confianza_efectiva` usa para medir "edad lógica" (A6) SIN
    salirse de la cadena causal del claim (A7): ver docstring del módulo,
    "Corrección encontrada durante la implementación"."""
    refuerzos = 0
    refutaciones = 0
    ultima_transicion: int | None = None
    for c in estado.claims:
        if c.autor is not Capacidad.VALIDAR or not c.vigencia.vigente:
            continue
        if not any(ref in decision_ids for ref in c.respaldo):
            continue
        funciono = c.afirmacion.get("funciono")
        if funciono is True:
            refuerzos += 1
        elif funciono is False:
            refutaciones += 1
        else:
            continue
        if ultima_transicion is None or c.id.transicion > ultima_transicion:
            ultima_transicion = c.id.transicion
    return refuerzos, refutaciones, ultima_transicion


def calcular_confianza_efectiva(
    claim: ClaimEntry, estado: LearningState, politica: Politica
) -> Decimal:
    """Implementa A1-A8 — ver el resumen "Garantías" en el docstring del
    módulo. Precondición del llamador: `claim` vigente (A8) — esta
    función no lo comprueba ni lo conoce.

    "Edad lógica" (A6) se mide desde la validación más reciente EN LA
    CADENA CAUSAL DEL CLAIM — nunca desde `estado.transicion` en bruto.
    Sin ninguna validación todavía, la edad es 0 (congelada): actividad
    de otros asuntos no puede decaer un claim que nunca tocó (A7,
    "localidad causal" — P6: toda ce debe ser explicable exhibiendo
    solo esas entradas, y "pasó el tiempo en otro asunto" no es una de
    ellas). Con al menos una validación, la edad se cuenta desde ESA
    transición — nunca desde el origen del claim, por el mismo motivo:
    contar desde el origen haría que cualquier transición ajena en el
    sistema decayera el claim, violando A7 exactamente igual."""
    decisiones = _decisiones_originadas_por(claim.id, estado)
    refuerzos, refutaciones, ultima_transicion = _validaciones_de(decisiones, estado)
    edad_logica = (
        _CERO
        if ultima_transicion is None
        else Decimal(estado.transicion - ultima_transicion)
    )

    ce = (
        claim.confianza
        + politica.peso_refuerzo * refuerzos
        - politica.peso_refutacion * refutaciones
        - politica.peso_decaimiento * edad_logica
    )
    return max(_CERO, min(_UNO, ce))
