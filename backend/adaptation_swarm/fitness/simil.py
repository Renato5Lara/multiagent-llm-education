"""Simil(S,W) = 1 − ½·‖s − W‖₁  con  s_m = e_m / Σe  (DECISION-CLOSURE §6.1).

Rango [0,1]; determinista; ambos vectores suman 1 (similitud por variación total).
Caso degenerado Σe = 0 (las 4 modalidades en "apoyo"): s = uniforme 1/4 — definido
aquí porque el cierre no cubre el 0/0; queda documentado y probado.
"""

from __future__ import annotations

from typing import Sequence


def emphasis_distribution(emphasis: Sequence[int]) -> tuple[float, ...]:
    total = sum(emphasis)
    if total == 0:
        return tuple(0.25 for _ in emphasis)
    return tuple(e / total for e in emphasis)


def simil(emphasis: Sequence[int], weights_by_modality: Sequence[float]) -> float:
    """`emphasis` y `weights_by_modality` en el orden MODALITIES (code, diagram, text, audio)."""
    if len(emphasis) != len(weights_by_modality):
        raise ValueError("emphasis y W deben tener igual longitud")
    s = emphasis_distribution(emphasis)
    l1 = sum(abs(a - b) for a, b in zip(s, weights_by_modality))
    return 1.0 - 0.5 * l1
