"""Instrumentación del PSO (Fase 2): solo observa; no altera ecuaciones ni criterio de parada."""

import numpy as np

from adaptation_swarm.metrics.pso_diagnostics import cycle_diagnostics, swarm_diagnostics
from adaptation_swarm.pso import engine
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng


def test_swarm_diagnostics_counts_unique_and_duplicate_particles():
    S = np.array([[0, 1], [0, 1], [2, 2], [1, 0]])
    x = np.array([[0.1, 1.0], [0.0, 0.9], [2.0, 2.0], [1.0, 0.0]])
    d = swarm_diagnostics(x, S, np.array([0.5, 0.5, 0.7, 0.1]))
    assert d["unique_positions_S"] == 3 and d["duplicate_particles_pct"] == 25.0 and d["unique_F"] == 3
    assert d["F_min"] == 0.1 and d["F_max"] == 0.7 and abs(d["F_mean"] - 0.45) < 1e-12
    assert d["mean_pairwise_distance_S_l1"] > 0 and d["mean_pairwise_distance_x_l2"] > 0


def test_identical_swarm_has_zero_distance():
    d = swarm_diagnostics(np.ones((5, 8)), np.ones((5, 8), int), np.full(5, 0.3))
    assert d["mean_pairwise_distance_x_l2"] == 0 and d["duplicate_particles_pct"] == 80.0


def test_engine_counters_track_pbest_gbest_updates_and_first_change():
    p = PSOParams(n_particles=3)
    st = engine.initialize(p, make_rng(2))
    engine.register(st, np.array([0.1, 0.2, 0.3]))
    assert st.pbest_updates == [3] and st.gbest_updates == [True] and st.first_gbest_change_k is None
    engine.advance(st, make_rng(3))
    engine.register(st, np.array([0.05, 0.25, 0.1]))          # solo la partícula 1 mejora; g_best NO mejora (0.3 > 0.25)
    assert st.pbest_updates == [3, 1] and st.gbest_updates == [True, False] and st.first_gbest_change_k is None
    engine.advance(st, make_rng(4))
    engine.register(st, np.array([0.05, 0.25, 0.9]))          # g_best mejora en k=2
    assert st.gbest_updates[-1] is True and st.first_gbest_change_k == 2 and st.pbest_updates[-1] == 1


def test_instrumentation_does_not_change_the_search():
    def run(seed):
        rng, st = make_rng(seed), None
        st = engine.initialize(PSOParams(), rng)
        f = lambda S: -np.abs(S - 1).sum(axis=1).astype(float)
        engine.register(st, f(st.decoded()))
        while engine.check_stop(st) is None:
            engine.advance(st, rng)
            engine.register(st, f(st.decoded()))
        return st
    a, b = run(9), run(9)
    assert np.array_equal(a.gbest_x, b.gbest_x) and a.k == b.k and a.pbest_updates == b.pbest_updates


def test_cycle_diagnostics_summary():
    its = [{"diagnostics": {"duplicate_particles_pct": 10.0}}, {"diagnostics": {"duplicate_particles_pct": 30.0}}]
    d = cycle_diagnostics(its, [20, 4], [True, False], None)
    assert d["pbest_updates_after_init"] == 4 and d["gbest_updates_after_init"] == 0
    assert d["gbest_never_changed_after_init"] and d["mean_duplicate_particles_pct"] == 20.0
