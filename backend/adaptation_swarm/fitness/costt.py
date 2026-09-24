"""CostT(S) = min(1, Σ_m t̂_m(v_m) / T_ref)  (DECISION-CLOSURE §6.1).

t̂_m(v_m) es el tiempo MEDIANO de realización de la variante v_m de la modalidad m,
medido en la calibración de la biblioteca M1 y CONGELADO en su manifiesto — nunca un
reloj en caliente dentro de 𝓕. T_ref = Σ_m max_v t̂_m(v) (el costo de la combinación
más cara), de modo que CostT ∈ [0,1] y 1 corresponde a la configuración más costosa.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from adaptation_swarm.pso.space import K_LEVELS, MODALITIES


@dataclass(frozen=True, slots=True)
class CostTable:
    """t̂[modalidad][variante] en milisegundos."""

    times_ms: Mapping[str, tuple[float, ...]]

    def __post_init__(self) -> None:
        for m in MODALITIES:
            row = self.times_ms.get(m)
            if row is None or len(row) != K_LEVELS:
                raise ValueError(f"CostTable requiere {K_LEVELS} tiempos para {m!r}")
            if any(t < 0 for t in row):
                raise ValueError("los tiempos no pueden ser negativos")

    @property
    def t_ref(self) -> float:
        return sum(max(self.times_ms[m]) for m in MODALITIES)

    def to_dict(self) -> dict:
        return {m: list(self.times_ms[m]) for m in MODALITIES}

    @classmethod
    def from_dict(cls, d: Mapping[str, Sequence[float]]) -> "CostTable":
        return cls({m: tuple(float(x) for x in d[m]) for m in MODALITIES})


def costt(variants: Sequence[int], table: CostTable) -> float:
    """`variants` = (v_code, v_diagram, v_text, v_audio)."""
    total = sum(table.times_ms[m][v] for m, v in zip(MODALITIES, variants))
    ref = table.t_ref
    if ref <= 0:
        return 0.0
    return min(1.0, total / ref)
