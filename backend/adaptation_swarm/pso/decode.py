"""Decodificador determinista φ (DECISION-CLOSURE §5.1, DEC-02):

    φ_j(x) = min(2, max(0, round(x)))

`round` es half-to-even (comportamiento estándar de Python y de `numpy.rint`),
fijado por test para no depender del intérprete. φ se aplica SOLO para evaluar
𝓕 y reportar S; nunca modifica las ecuaciones de actualización.
"""

from __future__ import annotations

import numpy as np

from adaptation_swarm.pso.space import LEVEL_MAX, LEVEL_MIN, Configuration


def phi(x: np.ndarray) -> np.ndarray:
    """φ vectorizado sobre cualquier arreglo de reales → enteros en {0,1,2}."""
    arr = np.asarray(x, dtype=float)
    return np.clip(np.rint(arr), LEVEL_MIN, LEVEL_MAX).astype(int)


def phi_scalar(x: float) -> int:
    return min(LEVEL_MAX, max(LEVEL_MIN, round(x)))


def decode(x: np.ndarray) -> Configuration:
    """x ∈ ℝ^8 → S = φ(x) como `Configuration`."""
    return Configuration(tuple(int(v) for v in phi(x)))
