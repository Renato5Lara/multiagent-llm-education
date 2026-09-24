"""Motor PSO: ecuaciones literales de la asesoría, p_best/g_best, parada literal (ε=0.001, k_max=15)."""

import numpy as np
import pytest

from adaptation_swarm.pso import engine
from adaptation_swarm.pso.decode import phi
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.pso.space import N_DIMS, all_configurations
from adaptation_swarm.schemas.states import StopReason


class FixedRng:
    """RNG que devuelve r1 y r2 fijados (para verificar las ecuaciones a mano)."""

    def __init__(self, r1, r2):
        self._seq = [np.asarray(r1, float), np.asarray(r2, float)]

    def random(self, shape):
        return np.broadcast_to(self._seq.pop(0), shape).copy()


def small_state(params, x, v, pbest_x, gbest_x):
    n = params.n_particles
    st = engine.initialize(params, make_rng(1))
    st.x = np.array(x, float).reshape(n, N_DIMS)
    st.v = np.array(v, float).reshape(n, N_DIMS)
    st.pbest_x = np.array(pbest_x, float).reshape(n, N_DIMS)
    st.gbest_x = np.array(gbest_x, float)
    st.registered = True
    return st


def test_params_match_decision_closure():
    p = PSOParams()
    assert (p.n_particles, p.w, p.c1, p.c2, p.v_max, p.k_max, p.epsilon) == (20, 0.729, 1.494, 1.494, 1.0, 15, 0.001)


def test_velocity_and_position_equations_literal():
    p = PSOParams(n_particles=1)
    x = [0.5, 1.0, 1.5, 0.0, 2.0, 1.0, 0.2, 1.8]
    v = [0.1, -0.2, 0.3, 0.0, 0.05, -0.1, 0.2, -0.3]
    pb = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    gb = [2.0, 0.0, 2.0, 0.0, 0.0, 2.0, 0.0, 2.0]
    r1, r2 = 0.3, 0.6
    st = small_state(p, x, v, pb, gb)
    engine.advance(st, FixedRng(r1, r2))
    exp_v = p.w * np.array(v) + p.c1 * r1 * (np.array(pb) - np.array(x)) + p.c2 * r2 * (np.array(gb) - np.array(x))
    exp_v = np.clip(exp_v, -1.0, 1.0)                  # única adición autorizada (DEC-08): |v| ≤ 1.0
    assert np.allclose(st.v[0], exp_v)
    assert np.allclose(st.x[0], np.array(x) + exp_v)   # x(k+1) = x(k) + v(k+1), sin φ
    assert st.k == 1


def test_velocity_is_clamped_to_vmax():
    p = PSOParams(n_particles=1)
    st = small_state(p, [0] * 8, [1.0] * 8, [0] * 8, [50] * 8)       # atracción enorme hacia g_best
    engine.advance(st, FixedRng(1.0, 1.0))
    assert np.all(np.abs(st.v) <= 1.0 + 1e-12)
    assert np.allclose(st.x[0], 1.0)


def test_position_is_not_clipped_or_decoded_in_update():
    p = PSOParams(n_particles=1)
    st = small_state(p, [1.9] * 8, [1.0] * 8, [1.9] * 8, [1.9] * 8)
    engine.advance(st, FixedRng(0.0, 0.0))
    assert np.allclose(st.x[0], 1.9 + 0.729)             # x latente continuo puede salirse de [0,2]
    assert st.x[0, 0] > 2.0 and int(phi(st.x[0])[0]) == 2


def test_initialization_uniform_0_2_with_labeled_heuristic():
    p = PSOParams()
    hx = np.array([2.0, 1.0, 0.5, 1.0, 0.7, 1.0, 0.2, 1.0])
    st = engine.initialize(p, make_rng(7), hx)
    assert st.x.shape == (20, 8) and np.all((st.x >= 0) & (st.x <= 2))
    assert np.array_equal(st.x[0], hx) and st.heuristic_particle == 0
    assert np.all(st.v == 0)
    st2 = engine.initialize(p, make_rng(7))
    assert st2.heuristic_particle is None and np.array_equal(st.x[1:], st2.x[1:])


def test_pbest_gbest_update_strict_improvement():
    p = PSOParams(n_particles=3)
    st = small_state(p, np.zeros((3, 8)), np.zeros((3, 8)), np.zeros((3, 8)), np.zeros(8))
    st.pbest_F = np.full(3, -np.inf)
    st.gbest_F = -np.inf
    st.x = np.arange(24, dtype=float).reshape(3, 8)
    engine.register(st, np.array([0.1, 0.5, 0.3]))
    assert st.gbest_F == 0.5 and st.gbest_particle == 1 and np.array_equal(st.gbest_x, st.x[1])
    old_x = st.x.copy()
    engine.advance(st, make_rng(0))
    engine.register(st, np.array([0.2, 0.4, 0.3]))            # p0 mejora; p1 empeora (conserva p_best)
    assert st.pbest_F.tolist() == [0.2, 0.5, 0.3]
    assert np.array_equal(st.pbest_x[1], old_x[1]) and np.array_equal(st.pbest_x[0], st.x[0])
    assert st.gbest_F == 0.5                                   # g_best no empeora nunca
    engine.advance(st, make_rng(0))
    engine.register(st, np.array([0.2, 0.5, 0.3]))              # empate: se conserva el anterior (mejora estricta)
    assert st.gbest_particle == 1 and st.gbest_F_history == [0.5, 0.5, 0.5]


def test_register_rejects_bad_input():
    st = engine.initialize(PSOParams(n_particles=2), make_rng(1))
    with pytest.raises(ValueError):
        engine.register(st, np.array([1.0]))
    with pytest.raises(ValueError):
        engine.register(st, np.array([1.0, np.nan]))


def test_advance_and_check_stop_require_registration():
    st = engine.initialize(PSOParams(n_particles=2), make_rng(1))
    with pytest.raises(RuntimeError):
        engine.advance(st, make_rng(1))
    with pytest.raises(RuntimeError):
        engine.check_stop(st)


def _run_with_gbest_sequence(seq, k_max=15):
    p = PSOParams(n_particles=2, k_max=k_max)
    st = engine.initialize(p, make_rng(1))
    reason = None
    for f in seq:
        engine.register(st, np.array([f, f - 1.0]))
        reason = engine.check_stop(st)
        if reason is not None:
            return st, reason
        engine.advance(st, make_rng(st.k))
    return st, reason


def test_stop_epsilon_literal_no_patience():
    # |F(g^1) − F(g^0)| = 0.0005 < 0.001 ⇒ para en k=1 (sin regla de paciencia, DEC-10)
    st, reason = _run_with_gbest_sequence([1.0, 1.0005, 2.0])
    assert reason is StopReason.EPSILON and st.k == 1


def test_no_stop_at_k0_and_no_stop_when_delta_not_below_epsilon():
    st = engine.initialize(PSOParams(n_particles=2), make_rng(1))
    engine.register(st, np.array([1.0, 0.0]))
    assert st.k == 0 and engine.check_stop(st) is None                 # nunca se para en k=0
    st, reason = _run_with_gbest_sequence([1.0, 1.002, 1.004, 1.0041], k_max=15)   # Δ=0.002 ≥ ε ⇒ sigue
    assert st.k == 3 and reason is StopReason.EPSILON                             # Δ=0.0001 < ε en k=3


def test_stop_k_max_15():
    seq = [1.0 + 0.01 * i for i in range(20)]            # mejora siempre ≥ 0.01: nunca converge por ε
    st, reason = _run_with_gbest_sequence(seq)
    assert reason is StopReason.K_MAX and st.k == 15


def test_epsilon_has_precedence_over_k_max():
    seq = [1.0 + 0.01 * i for i in range(15)] + [1.14 + 0.0001]     # en k=15 converge y agota iteraciones
    st, reason = _run_with_gbest_sequence(seq)
    assert st.k == 15 and reason is StopReason.EPSILON


def _synthetic_F(cfg_matrix):
    """Aptitud sintética sobre S=φ(x): determinista y con un único óptimo global."""
    target = np.array([2, 1, 0, 2, 1, 0, 2, 1])
    return -np.abs(cfg_matrix - target).sum(axis=1).astype(float)


def _run_pso(seed, F_fn=_synthetic_F, k_max=15):
    p = PSOParams(k_max=k_max)
    rng = make_rng(seed)
    st = engine.initialize(p, rng)
    engine.register(st, F_fn(st.decoded()))
    while engine.check_stop(st) is None:
        engine.advance(st, rng)
        engine.register(st, F_fn(st.decoded()))
    return st


def test_determinism_same_seed_bit_for_bit_and_different_seed_differs():
    a, b, c = _run_pso(123), _run_pso(123), _run_pso(124)
    assert a.k == b.k and np.array_equal(a.gbest_x, b.gbest_x) and a.gbest_F == b.gbest_F
    assert np.array_equal(a.x, b.x) and np.array_equal(a.v, b.v)
    assert not np.array_equal(a.x, c.x)


def test_gbest_history_is_monotone_non_decreasing_and_pbest_never_worsens():
    p = PSOParams()
    rng = make_rng(5)
    st = engine.initialize(p, rng)
    prev_pbest = np.full(p.n_particles, -np.inf)
    engine.register(st, _synthetic_F(st.decoded()))
    for _ in range(6):
        assert np.all(st.pbest_F >= prev_pbest)
        prev_pbest = st.pbest_F.copy()
        engine.advance(st, rng)
        engine.register(st, _synthetic_F(st.decoded()))
    h = st.gbest_F_history
    assert all(b >= a for a, b in zip(h, h[1:]))


def test_pso_never_beats_brute_force_optimum_and_gets_close():
    confs = np.array([c.vector for c in all_configurations()])
    optimum = _synthetic_F(confs).max()
    assert optimum == 0.0
    best = max(_run_pso(s, k_max=15).gbest_F for s in range(10))
    assert best <= optimum
    assert best >= -4                                    # el enjambre se acerca al óptimo global
