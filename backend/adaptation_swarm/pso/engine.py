"""Motor PSO (asesoría §3.3.2; DECISION-CLOSURE §5.1). Puro: sin Redis, sin LLM,
sin reloj — determinista dado (params, semilla, función de aptitud).

Ecuaciones LITERALES de la asesoría (x, v ∈ ℝ; φ solo se usa para evaluar 𝓕):

    v_ij(k+1) = w·v_ij(k) + c1·r1·(p_ij − x_ij(k)) + c2·r2·(g_j − x_ij(k))
    x_ij(k+1) = x_ij(k) + v_ij(k+1)

Único añadido (autorizado, DEC-08): saturación de velocidad a ±v_max.

Ciclo de uso (lo orquesta AG0):
    state = initialize(params, rng, heuristic_x)      # k = 0
    register(state, F_k0)                             # evalúa 𝓕(φ(x)) fuera del motor
    while (reason := check_stop(state)) is None:
        advance(state, rng)                           # k += 1: v y x
        register(state, F_k)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from adaptation_swarm.pso.decode import decode, phi
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.particle import ParticleRecord, make_record
from adaptation_swarm.pso.space import N_DIMS
from adaptation_swarm.schemas.states import StopReason


@dataclass
class PSOState:
    params: PSOParams
    k: int
    x: np.ndarray                 # (N, 8) posiciones latentes continuas
    v: np.ndarray                 # (N, 8) velocidades
    pbest_x: np.ndarray           # (N, 8)
    pbest_F: np.ndarray           # (N,)
    gbest_x: np.ndarray           # (8,)
    gbest_F: float
    gbest_particle: int
    F_current: np.ndarray         # (N,) 𝓕(φ(x)) de la iteración actual
    gbest_F_history: list[float] = field(default_factory=list)   # índice = k
    heuristic_particle: int | None = None
    registered: bool = False
    # ── instrumentación (Fase 2): solo OBSERVA, no altera ninguna ecuación ni criterio ──
    pbest_updates: list[int] = field(default_factory=list)       # nº de p_best mejorados en cada iteración (k=0: todos)
    gbest_updates: list[bool] = field(default_factory=list)      # ¿mejoró g_best en cada iteración?
    first_gbest_change_k: int | None = None                      # primera iteración k≥1 en la que g_best mejoró

    def decoded(self) -> np.ndarray:
        """S_i = φ(x_i) de todas las partículas: (N, 8) enteros."""
        return phi(self.x)

    def gbest_S(self) -> tuple[int, ...]:
        return decode(self.gbest_x).vector

    def records(self) -> list[ParticleRecord]:
        return [
            make_record(i, self.k, self.x[i], self.v[i], self.F_current[i],
                        self.pbest_F[i], self.pbest_x[i], i == self.heuristic_particle)
            for i in range(self.params.n_particles)
        ]


def initialize(
    params: PSOParams, rng: np.random.Generator, heuristic_x: np.ndarray | None = None
) -> PSOState:
    """x^(0) ~ U(0,2) por dimensión. Si se da `heuristic_x` (arranque derivado de W,
    DEC-02), la partícula 0 lo toma y queda etiquetada — el tamaño del enjambre
    sigue siendo N. v^(0) = 0."""
    n = params.n_particles
    x = rng.uniform(params.init_low, params.init_high, size=(n, N_DIMS))
    heuristic_particle = None
    if heuristic_x is not None:
        hx = np.asarray(heuristic_x, dtype=float)
        if hx.shape != (N_DIMS,):
            raise ValueError(f"heuristic_x debe tener forma ({N_DIMS},)")
        x[0] = hx
        heuristic_particle = 0
    return PSOState(
        params=params, k=0, x=x, v=np.zeros((n, N_DIMS)),
        pbest_x=x.copy(), pbest_F=np.full(n, -np.inf),
        gbest_x=x[0].copy(), gbest_F=-np.inf, gbest_particle=0,
        F_current=np.full(n, -np.inf), heuristic_particle=heuristic_particle,
    )


def advance(state: PSOState, rng: np.random.Generator) -> None:
    """Un paso de las ecuaciones de la asesoría (k → k+1). r1, r2 ~ U(0,1) por
    partícula y dimensión, en el orden fijo (r1 primero, luego r2)."""
    if not state.registered:
        raise RuntimeError("advance() exige haber registrado la aptitud de la iteración actual")
    p = state.params
    r1 = rng.random(state.x.shape)
    r2 = rng.random(state.x.shape)
    v_new = (
        p.w * state.v
        + p.c1 * r1 * (state.pbest_x - state.x)
        + p.c2 * r2 * (state.gbest_x[None, :] - state.x)
    )
    v_new = np.clip(v_new, -p.v_max, p.v_max)
    state.v = v_new
    state.x = state.x + v_new
    state.k += 1
    state.registered = False


def register(state: PSOState, F: np.ndarray) -> None:
    """Registra 𝓕(φ(x_i)) de la iteración actual; actualiza p_best y g_best
    (mejora estricta) y la historia de 𝓕(g_best)."""
    F = np.asarray(F, dtype=float)
    if F.shape != (state.params.n_particles,):
        raise ValueError(f"F debe tener forma ({state.params.n_particles},)")
    if not np.all(np.isfinite(F)):
        raise ValueError("F contiene valores no finitos")
    state.F_current = F.copy()
    improved = F > state.pbest_F
    state.pbest_F = np.where(improved, F, state.pbest_F)
    state.pbest_x = np.where(improved[:, None], state.x, state.pbest_x)
    state.pbest_updates.append(int(improved.sum()))
    best = int(np.argmax(state.pbest_F))          # primer máximo en empate (determinista)
    gbest_improved = bool(state.pbest_F[best] > state.gbest_F)
    if gbest_improved:
        state.gbest_F = float(state.pbest_F[best])
        state.gbest_x = state.pbest_x[best].copy()
        state.gbest_particle = best
    state.gbest_updates.append(gbest_improved)
    if gbest_improved and state.k >= 1 and state.first_gbest_change_k is None:
        state.first_gbest_change_k = state.k
    state.gbest_F_history.append(state.gbest_F)
    state.registered = True


def check_stop(state: PSOState) -> StopReason | None:
    """Criterio LITERAL de la asesoría: |𝓕(g_best^k) − 𝓕(g_best^(k−1))| < ε, o k = k_max.
    Sin paciencia ni modificaciones (DEC-10). ε tiene precedencia si ambas se cumplen."""
    if not state.registered:
        raise RuntimeError("check_stop() exige haber registrado la aptitud de la iteración actual")
    hist = state.gbest_F_history
    if state.k >= 1 and abs(hist[state.k] - hist[state.k - 1]) < state.params.epsilon:
        return StopReason.EPSILON
    if state.k >= state.params.k_max:
        return StopReason.K_MAX
    return None
