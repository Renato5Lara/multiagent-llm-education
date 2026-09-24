"""𝓕(S) = α·Simil(S,W) + β·Coher(S) − γ·Redund(S) − δ·CostT(S),  α+β+γ+δ = 1
(asesoría §3.3.2; pesos DECISION-CLOSURE §6.2: 0.40 / 0.30 / 0.15 / 0.15).
Rango de 𝓕 con términos en [0,1]: [−(γ+δ), α+β].
"""

from __future__ import annotations

from dataclasses import dataclass

from adaptation_swarm.fitness.simil import simil
from adaptation_swarm.pso.space import Configuration


@dataclass(frozen=True, slots=True)
class FitnessWeights:
    alpha: float = 0.40   # Simil
    beta: float = 0.30    # Coher
    gamma: float = 0.15   # Redund
    delta: float = 0.15   # CostT

    def __post_init__(self) -> None:
        if abs(self.alpha + self.beta + self.gamma + self.delta - 1.0) > 1e-9:
            raise ValueError("α+β+γ+δ debe ser 1")
        if min(self.alpha, self.beta, self.gamma, self.delta) < 0:
            raise ValueError("los pesos no pueden ser negativos")

    def to_dict(self) -> dict[str, float]:
        return {"alpha": self.alpha, "beta": self.beta, "gamma": self.gamma, "delta": self.delta}


@dataclass(frozen=True, slots=True)
class FitnessBreakdown:
    F: float
    simil: float
    coher: float
    redund: float
    costt: float

    def to_dict(self) -> dict[str, float]:
        return {"F": self.F, "simil": self.simil, "coher": self.coher,
                "redund": self.redund, "costt": self.costt}


def evaluate(
    config: Configuration, weights_by_modality: tuple[float, ...],
    coher_value: float, redund_value: float, costt_value: float,
    fw: FitnessWeights = FitnessWeights(),
) -> FitnessBreakdown:
    """Simil depende del énfasis e_m de S; Coher/Redund/CostT de las variantes v_m
    realizadas (los recibe ya calculados: sobre las piezas de la biblioteca)."""
    s = simil(config.emphasis, weights_by_modality)
    F = fw.alpha * s + fw.beta * coher_value - fw.gamma * redund_value - fw.delta * costt_value
    return FitnessBreakdown(F=F, simil=s, coher=coher_value, redund=redund_value, costt=costt_value)
