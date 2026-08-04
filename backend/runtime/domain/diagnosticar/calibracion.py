"""Calibración de la confianza declarada de Diagnosticar-LLM (RFC-0002
R2; RFC-0006 §1 A2; RESEARCH_ITERATIONS.md Iteración 5.8, cadena H10).

Diagnosticar interpreta CADA hecho evaluativo nuevo, siempre — "mapa
completo" (commit `504e09d`, `productor.py`/`productor_llm.py`): esta
pieza no decide SI se produce el claim, decide QUÉ confianza declara al
producirlo. D1 sigue resolviendo "mayor confianza efectiva gana"
exactamente como RFC-0006 §4 lo fija (Engineering Review, Iteración
5.7) — la asimetría vive aquí, nunca en `kernel/deliberation/`.

`evidence_strength` es una abstracción versionable (Iteración 5.8): la
implementación inicial es el límite inferior de un intervalo de Wilson
(95%) sobre la proporción que sostiene la afirmación PROPIA del claim
— aciertos si `dominada=True`, errores si `dominada=False` (Iteración
5.5 documenta el error de calcularlo siempre sobre aciertos). Un
cambio de fórmula futuro es una nueva versión, nunca una edición
silenciosa de esta.

`THETA_MEJORA_V1` es un parámetro pedagógico nombrado y versionado por
sufijo (mismo patrón que `_UMBRAL_ERRORES` en `productor.py` y los
`_PROMPT_ID` versionados de las capacidades LLM) — no una constante de
`Politica` en esta iteración: el alcance aprobado para este commit
excluye `kernel/deliberation/`.

`evidence_strength` se relocalizó a `runtime/domain/shared/calibracion.py`
(ADR-0013): es matemática pura, sin nada específico de Diagnosticar, y
Remediar/Orientar la reutilizan directo. Se re-exporta aquí sin cambio de
comportamiento — todo importador existente de este módulo sigue
funcionando igual.
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.shared.calibracion import evidence_strength

__all__ = ["THETA_MEJORA_V1", "evidence_strength", "calibrar_confianza_nueva"]

THETA_MEJORA_V1 = Decimal("0")
"""Umbral mínimo de fuerza de evidencia para aceptar una mejora
(`dominada`: False→True) frente al claim vigente — Iteración 5.8:
matemáticamente suficiente bajo evidencia positiva no nula, decisión
pedagógica explícita, no necesidad estadística."""


def calibrar_confianza_nueva(
    *,
    nueva_dominada: bool,
    fuerza_nueva: Decimal,
    vigente_dominada: bool | None,
    fuerza_vigente: Decimal | None,
    theta_mejora: Decimal = THETA_MEJORA_V1,
) -> Decimal:
    """Confianza declarada final del claim nuevo (Iteración 5.6/5.8).

    Sin claim vigente rival: la fuerza de la evidencia se declara tal
    cual — no hay transición que calificar. Con vigente del MISMO
    veredicto (`vigente_dominada == nueva_dominada`, reconfirmación sin
    cambio de dirección): fuera del alcance de 5.6/5.8 (que solo
    definió mejora y retroceso) — se declara `fuerza_nueva` sin ajuste,
    D1 decide como siempre. Con vigente de veredicto CONTRARIO: mejora
    (False→True) se acepta con evidencia mínima (`> theta_mejora`);
    retroceso (True→False) exige igualar o superar la fuerza del
    vigente.

    D1 sigue siendo "mayor confianza efectiva gana" sin modificar (RFC-
    0006 §4) — por eso "aceptar" una mejora no puede declarar solo
    `fuerza_nueva` tal cual: si el vigente (retroceso, con muestra
    grande) tiene una `ce` propia más alta que la nueva evidencia
    pequeña, D1 elegiría al vigente de todos modos y la "aceptación" no
    tendría efecto real (bug encontrado en la primera validación E2E
    real contra Postgres — Iteración 5.8, cuenta `estudiante.calib1`: la
    mejora declaraba 0.3424 contra un vigente de 0.7575 y perdía D1 pese
    a "aceptarse"). Aceptar una mejora declara `max(fuerza_nueva,
    fuerza_vigente)` — empata con el vigente en vez de perder ante él; el
    empate lo resuelve el desempate por recencia que YA EXISTE en el
    kernel (`sorted(claims, key=lambda c: (puntaje, str(c.id)),
    reverse=True)`, sin tocarlo), igual que Caso B ya dependía de ese
    mismo desempate. Retroceso no necesita este ajuste: comparar
    directamente contra `fuerza_vigente` ya produce una victoria real en
    D1 cuando la condición se cumple."""
    if fuerza_vigente is None or vigente_dominada is None:
        return fuerza_nueva
    if vigente_dominada == nueva_dominada:
        return fuerza_nueva
    if nueva_dominada:
        if fuerza_nueva > theta_mejora:
            return max(fuerza_nueva, fuerza_vigente)
        return Decimal("0")
    return fuerza_nueva if fuerza_nueva >= fuerza_vigente else Decimal("0")
