"""Vista de una partícula (registro de trazabilidad p_best / posición / decodificación)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from adaptation_swarm.pso.decode import decode


@dataclass(frozen=True, slots=True)
class ParticleRecord:
    idx: int
    k: int
    x: tuple[float, ...]
    v: tuple[float, ...]
    S: tuple[int, ...]
    F: float
    pbest_F: float
    pbest_x: tuple[float, ...]
    heuristic_seed: bool

    def to_dict(self) -> dict:
        return {
            "idx": self.idx, "k": self.k, "x": list(self.x), "v": list(self.v),
            "S": list(self.S), "F": self.F, "pbest_F": self.pbest_F,
            "pbest_x": list(self.pbest_x), "heuristic_seed": self.heuristic_seed,
        }


def make_record(idx: int, k: int, x: np.ndarray, v: np.ndarray, F: float,
                pbest_F: float, pbest_x: np.ndarray, heuristic_seed: bool) -> ParticleRecord:
    return ParticleRecord(
        idx=idx, k=k, x=tuple(float(a) for a in x), v=tuple(float(a) for a in v),
        S=decode(x).vector, F=float(F), pbest_F=float(pbest_F),
        pbest_x=tuple(float(a) for a in pbest_x), heuristic_seed=heuristic_seed,
    )
