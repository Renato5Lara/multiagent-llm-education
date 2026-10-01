"""Líneas base convencionales de OE2 (`baselines/conventional.py`): se ejecutan sobre la biblioteca REAL (sin mocks) y deben cumplir las mismas condiciones que la propuesta
(paquete de 4 modalidades validado, mismo 𝓕) para que la comparación sea equivalente."""

import numpy as np
import pytest

from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.baselines.conventional import SYSTEMS, ConventionalAdapter
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.metrics.search_quality import brute_force_optimum
from adaptation_swarm.profiles.w_mapping import compute_weights, heuristic_start
from adaptation_swarm.pso.decode import decode
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.space import SPACE_SIZE

pytestmark = pytest.mark.requires_library_audio


def test_unknown_system_is_rejected(store):
    with pytest.raises(ValueError):
        ConventionalAdapter(store, "monolitico-llm")
    assert SYSTEMS == ("rules", "bruteforce")


@pytest.mark.parametrize("system", SYSTEMS)
def test_baseline_delivers_a_valid_four_modality_package(store, slice_profile, system):
    r = ConventionalAdapter(store, system).adapt(slice_profile)
    assert r.status == "completed" and r.error is None
    p = r.package
    assert p["chain_valid"] and p["validation"]["valid"] and len(p["S"]) == 8
    assert p["code"]["source"] and p["diagram"]["mermaid"] and p["text"]["text"] and p["audio"]["path"]
    assert 0 < r.t_conv_ms <= r.total_ms and r.predicted_dominant in ("code", "diagram", "text", "audio")


def test_rules_system_is_the_heuristic_without_search(store, slice_profile):
    r = ConventionalAdapter(store, "rules").adapt(slice_profile)
    assert r.S == list(decode(np.array(heuristic_start(compute_weights(slice_profile)))).vector) and r.n_evaluations == 0


def test_bruteforce_is_the_global_optimum_and_bounds_pso_and_rules(store, slice_profile):
    bf = ConventionalAdapter(store, "bruteforce").adapt(slice_profile)
    rules = ConventionalAdapter(store, "rules").adapt(slice_profile)
    opt = brute_force_optimum(store, slice_profile.concept_id, compute_weights(slice_profile), FitnessWeights())
    pso = replay_cycle(store, slice_profile, PSOParams(), FitnessWeights(), 20260923)
    assert bf.n_evaluations == SPACE_SIZE and bf.F == pytest.approx(opt.F)
    assert bf.F >= pso["F"] - 1e-12 and bf.F >= rules.F - 1e-12


def test_invalid_profile_fails_explicitly(store):
    r = ConventionalAdapter(store, "rules").adapt({"profile_id": "x"})
    assert r.status == "failed" and r.error and r.package is None
