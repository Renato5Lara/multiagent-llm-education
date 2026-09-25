"""Análisis de sensibilidad del PSO (`adaptation_swarm_sensitivity.json`): evidencia COMPLEMENTARIA, no una corrida principal, y no
modifica las corridas congeladas. Puras: leen JSON, dataset y biblioteca versionados y re-ejecutan EN PROCESO el motor PSO (sin bus,
sin Redis, sin audio, sin PostgreSQL, sin red). La brecha al óptimo global (fuerza bruta, lenta) no se re-ejecuta aquí."""

import hashlib
import json
import re
import statistics
from pathlib import Path

import numpy as np
import pytest

from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.coher import coher
from adaptation_swarm.fitness.costt import costt
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.fitness.redund import redund
from adaptation_swarm.gold.dataset import gold_for
from adaptation_swarm.gold.f1 import f1_report
from adaptation_swarm.gold.rubric import predicted_dominant
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.w_mapping import compute_weights, heuristic_start
from adaptation_swarm.pso import engine
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.rng import make_rng
from adaptation_swarm.pso.space import Configuration
from adaptation_swarm.schemas.ids import derive_seed

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "backend" / "experiments" / "results"
SENSITIVITY = RESULTS / "adaptation_swarm_sensitivity.json"
DOC = RESULTS / "adaptation_swarm_sensitivity.md"
FROZEN_DOC = RESULTS / "adaptation_swarm_frozen_runs.md"
REFERENCE = FitnessWeights()
ENTRIES = ("alpha=0.3", "alpha=0.4(ref)", "alpha=0.5", "N=10", "N=20(ref)", "N=30")


def _block(doc: Path) -> dict:
    return json.loads(re.search(r"```json\n(.*?)\n```", doc.read_text(encoding="utf-8"), re.S).group(1))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _weights_with_alpha(alpha: float) -> FitnessWeights:
    """α variable; β, γ, δ reescalados proporcionalmente para conservar α+β+γ+δ = 1 (DECISION-CLOSURE §6.2)."""
    k = (1.0 - alpha) / (REFERENCE.beta + REFERENCE.gamma + REFERENCE.delta)
    return FitnessWeights(alpha, REFERENCE.beta * k, REFERENCE.gamma * k, REFERENCE.delta * k)


GRID = {"alpha=0.3": (PSOParams(), _weights_with_alpha(0.3)), "alpha=0.4(ref)": (PSOParams(), _weights_with_alpha(0.4)),
        "alpha=0.5": (PSOParams(), _weights_with_alpha(0.5)), "N=10": (PSOParams(n_particles=10), REFERENCE),
        "N=20(ref)": (PSOParams(n_particles=20), REFERENCE), "N=30": (PSOParams(n_particles=30), REFERENCE)}


def _replay_cycle(store, prof, params, fw, batch_seed):
    """Réplica en proceso del ciclo de AG0 (semilla → evaluar 𝓕 → avanzar hasta la parada literal), con el motor PSO versionado."""
    rng = make_rng(derive_seed(batch_seed, prof.profile_id, 0))
    w = compute_weights(prof)
    ps = engine.initialize(params, rng, np.array(heuristic_start(w)))
    anchor, table, memo = store.anchor(prof.concept_id), store.calibration(), {}
    while True:
        F = []
        for row in ps.decoded():
            c = Configuration(tuple(int(v) for v in row))
            if c.variants not in memo:
                vc, vd, vt, _ = c.variants
                code, diagram, text = store.code(prof.concept_id, vc).text, store.diagram(prof.concept_id, vc, vd).text, store.text(prof.concept_id, vt).text
                memo[c.variants] = (coher(anchor, code, diagram, text).value, redund(anchor, code, diagram, text), costt(c.variants, table))
            F.append(evaluate(c, w.by_modality(), *memo[c.variants], fw).F)
        engine.register(ps, np.array(F))
        reason = engine.check_stop(ps)
        if reason is not None:
            S = ps.gbest_S()
            return {"S": list(S), "F": ps.gbest_F, "k": ps.k, "epsilon": reason.value == "epsilon",
                    "predicted": predicted_dominant([S[0], S[2], S[4], S[6]])}
        engine.advance(ps, rng)


@pytest.fixture(scope="module")
def replays():
    man = _block(DOC)
    store = LibraryStore.open(SETTINGS.library_root, man["library_version"])
    profiles = read_dataset(ROOT / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl")
    return {name: [_replay_cycle(store, p, params, fw, man["batch_seed"]) for p in profiles] for name, (params, fw) in GRID.items()}


def test_sensitivity_file_matches_its_recorded_sha256_and_is_not_a_main_run():
    man, data = _block(DOC), json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    assert man["schema"] == "sensitivity-v1" and man["artifact"]["file"] == "backend/experiments/results/adaptation_swarm_sensitivity.json"
    assert _sha(SENSITIVITY) == man["artifact"]["sha256"], "el análisis de sensibilidad fue alterado: es evidencia congelada"
    assert man["is_main_run"] is False and "cases" not in data and "summary" not in data and "config" not in data      # no tiene forma de corrida
    assert SENSITIVITY.name != "adaptation_swarm_corrida-poc-1.json" and set(data) == {"library_version", "n", "batch_seed", "git", "results"}


def test_versions_seed_and_evaluated_parameters_are_identified():
    man, data = _block(DOC), json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    frozen = _block(FROZEN_DOC)
    assert (data["library_version"], data["n"], data["batch_seed"]) == (man["library_version"], man["n_cases"], man["batch_seed"]) == (
        "lib-v5-9ae9ffdd", 100, 20260923)
    assert _sha(ROOT / "datasets" / "adaptation_library" / man["library_version"] / "manifest.json") == man["library_manifest_sha256"]
    assert man["dataset"]["profiles_sha256"] == frozen["dataset"]["profiles_sha256"] and man["dataset"]["gold_sha256"] == frozen["dataset"]["gold_sha256"]
    assert _sha(ROOT / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl") == man["dataset"]["profiles_sha256"]
    assert data["git"] == man["executed_with"] and data["git"]["dirty"] is True                                       # se declara: árbol sucio
    assert tuple(data["results"]) == ENTRIES == tuple(man["grid"]["entries"])
    for name, (params, fw) in GRID.items():
        r = data["results"][name]
        assert r["params"] == params.to_dict() and r["weights"] == pytest.approx(fw.to_dict())
        assert abs(sum(r["weights"].values()) - 1.0) < 1e-12
    assert [GRID[n][1].alpha for n in ("alpha=0.3", "alpha=0.4(ref)", "alpha=0.5")] == man["grid"]["alpha"]
    assert [GRID[n][0].n_particles for n in ("N=10", "N=20(ref)", "N=30")] == man["grid"]["n_particles"]
    assert GRID["alpha=0.4(ref)"][1].to_dict() == pytest.approx(REFERENCE.to_dict())              # α = 0.4 reescalado = la referencia


def test_every_configuration_has_complete_and_internally_coherent_metrics():
    data = json.loads(SENSITIVITY.read_text(encoding="utf-8"))
    gold_support = {"code": 50, "diagram": 25, "text": 25, "audio": 0}
    for name, r in data["results"].items():
        assert set(r) == {"weights", "params", "f1_adapt", "accuracy", "CR", "k_stop_mean", "mean_gap", "predicted_distribution",
                          "agreement_with_reference_predictions"}, name
        dist = r["predicted_distribution"]
        assert sum(dist.values()) == 100 and dist["audio"] == 0
        assert 0.0 <= r["f1_adapt"] <= 1.0 and 0.0 <= r["CR"] <= 1.0 and r["mean_gap"] >= 0.0
        assert 1.0 <= r["k_stop_mean"] <= r["params"]["k_max"] and 0.5 <= r["agreement_with_reference_predictions"] <= 1.0
        correct = round(r["accuracy"] * 100)
        assert r["accuracy"] * 100 == pytest.approx(correct) and correct <= sum(min(dist[c], gold_support[c]) for c in gold_support)   # factible


def test_reference_entries_are_identical_and_match_the_frozen_main_run():
    data, frozen = json.loads(SENSITIVITY.read_text(encoding="utf-8"))["results"], _block(FROZEN_DOC)["runs"]["corrida-poc-1"]["metrics"]
    a, n = data["alpha=0.4(ref)"], data["N=20(ref)"]
    assert a == n and a["agreement_with_reference_predictions"] == 1.0
    assert a["f1_adapt"] == frozen["f1_adapt"] == pytest.approx(0.8031, abs=1e-4) and a["accuracy"] == frozen["accuracy"]
    assert a["CR"] == frozen["CR"] and a["k_stop_mean"] == frozen["k_stop_mean"] and a["mean_gap"] == frozen["mean_gap_to_global_optimum"]
    assert _block(DOC)["reference_entries_match_run"] == "corrida-poc-1"


def test_the_sensitivity_does_not_present_itself_as_meeting_the_target():
    """El F1 principal sigue en 0.8031 (< 0.85) y ninguna configuración del barrido llega al objetivo de la asesoría."""
    man, data = _block(DOC), json.loads(SENSITIVITY.read_text(encoding="utf-8"))["results"]
    best = max(r["f1_adapt"] for r in data.values())
    assert man["f1_target_asesoria"] == 0.85 and man["f1_max_over_grid"] == best and best < 0.85
    assert man["f1_target_met_by_any_configuration"] is (best >= 0.85) is False
    assert _block(FROZEN_DOC)["runs"]["corrida-poc-1"]["f1_target_met"] is False
    assert "no alcanza el objetivo 0.85" in DOC.read_text(encoding="utf-8")


def test_replaying_the_versioned_pso_in_process_reproduces_every_stored_metric(replays):
    """Reproducibilidad: misma semilla, dataset, gold y biblioteca ⇒ mismas métricas, con el motor PSO versionado y sin infraestructura."""
    man, data = _block(DOC), json.loads(SENSITIVITY.read_text(encoding="utf-8"))["results"]
    profiles = read_dataset(ROOT / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl")
    ref_pred = [c["predicted"] for c in replays["alpha=0.4(ref)"]]
    for name, cycles in replays.items():
        stored = data[name]
        pairs = [(gold_for(p).expected_dominant, c["predicted"]) for p, c in zip(profiles, cycles)]
        rep, dist = f1_report(pairs), [c["predicted"] for c in cycles]
        assert rep.f1_adapt == stored["f1_adapt"] and rep.accuracy == stored["accuracy"], name
        assert sum(c["epsilon"] for c in cycles) / len(cycles) == stored["CR"], name
        assert statistics.fmean(c["k"] for c in cycles) == pytest.approx(stored["k_stop_mean"]), name
        assert {m: dist.count(m) for m in ("code", "diagram", "text", "audio")} == stored["predicted_distribution"], name
        assert sum(a == b for a, b in zip(dist, ref_pred)) / len(dist) == pytest.approx(stored["agreement_with_reference_predictions"]), name
    assert man["batch_seed"] == 20260923


def test_replay_of_the_reference_configuration_matches_every_case_of_corrida_poc_1(replays):
    cases = json.loads((RESULTS / "adaptation_swarm_corrida-poc-1.json").read_text(encoding="utf-8"))["cases"]
    for c, r in zip(cases, replays["alpha=0.4(ref)"]):
        assert (r["S"], r["k"], r["predicted"]) == (c["g_best_S"], c["k_stop"], c["predicted"]) and r["F"] == c["g_best_F"]
