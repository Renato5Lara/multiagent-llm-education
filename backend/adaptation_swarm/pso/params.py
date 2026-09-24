"""Parámetros del PSO (DECISION-CLOSURE §5.1 y §10 — DEC-02, DEC-08, DEC-10)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from adaptation_swarm.schemas.ids import sha256_text


@dataclass(frozen=True, slots=True)
class PSOParams:
    n_particles: int = 20        # DEC-08: N = 20 (barrido de sensibilidad {10,20,30} pre-registrado)
    w: float = 0.729             # DEC-08: inercia (constricción de Clerc–Kennedy)
    c1: float = 1.494            # DEC-08: coeficiente cognitivo
    c2: float = 1.494            # DEC-08: coeficiente social
    v_max: float = 1.0           # saturación ±1.0 (mitad del rango [0,2])
    k_max: int = 15              # asesoría §3.3.2
    epsilon: float = 0.001       # asesoría §3.3.2
    init_low: float = 0.0        # x^(0) ~ U(0,2)
    init_high: float = 2.0

    def __post_init__(self) -> None:
        if self.n_particles < 1:
            raise ValueError("n_particles >= 1")
        if self.k_max < 1:
            raise ValueError("k_max >= 1")
        if self.epsilon <= 0:
            raise ValueError("epsilon > 0")
        if self.v_max <= 0:
            raise ValueError("v_max > 0")

    def to_dict(self) -> dict:
        return asdict(self)

    def config_hash(self) -> str:
        return sha256_text(json.dumps(self.to_dict(), sort_keys=True))
