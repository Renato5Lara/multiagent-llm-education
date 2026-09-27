"""Línea base fuerza bruta frente a PSO (D11c) e informe comparativo de alternativas de Balanced (D1, D2). Puras: leen el manifiesto y los artefactos NO-audio de la biblioteca y
los JSON congelados; no usan PostgreSQL, Redis, audio ni red. Comprueban que la fuerza bruta coincide con el óptimo histórico, que el PSO nunca supera al óptimo global, que NO se
afirma reducción de latencia sin hardware/datos/repeticiones válidos, y que todo resultado sobre Balanced es PROVISIONAL, no excluye a Balanced y no toca la evidencia congelada."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from adaptation_swarm.analysis import balanced_alternatives as ba
from adaptation_swarm.analysis import baseline_bruteforce as bb
from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold import f1 as f1_hist
from adaptation_swarm.metrics.search_quality import brute_force_optimum
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.space import SPACE_SIZE
from adaptation_swarm.tools import isolated_env as iso

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "backend" / "experiments" / "results"
LIB = "lib-v5-9ae9ffdd"
HW_OK = {"vcpu": 8, "ram_gib": 32.0, "cpu_model": "x", "python": "3.x", "numpy": "x", "platform": "x"}


@pytest.fixture(scope="module")
def store():
    return LibraryStore.open(SETTINGS.library_root, LIB)


@pytest.fixture(scope="module")
def profiles():
    return read_dataset(bb.DEFAULT_PROFILES)


# ── línea base ──────────────────────────────────────────────────────────────────────────────────────────────────────
def test_bruteforce_matches_the_historical_global_optimum(store, profiles):
    fw = FitnessWeights()
    for p in profiles[:3]:
        W = compute_weights(p)
        mine = bb.bruteforce_search(store, p.concept_id, W, fw, memo={})
        ref = brute_force_optimum(store, p.concept_id, W, fw)
        assert (tuple(mine["S"]), mine["F"], mine["n_optimal"]) == (ref.S, ref.F, ref.n_optimal) and mine["evals"] == SPACE_SIZE == 6561


def test_baseline_compares_the_same_profile_library_and_fitness(store, profiles):
    rep = bb.run_baseline(store, profiles[:2], PSOParams(), FitnessWeights(), 20260923, repeats=1, warmup=0, hardware=HW_OK)
    assert rep["report_version"] == bb.REPORT_VERSION and rep["n_profiles"] == 2 and rep["space_size"] == 6561 and rep["library_version"] == LIB
    for c in rep["cases"]:
        assert c["gap_F"] >= -1e-12 and c["bruteforce"]["F"] >= c["pso"]["F"] - 1e-12          # el PSO nunca supera el óptimo global
        assert c["pso_at_global_optimum"] == (c["gap_F"] <= 1e-12) and c["bruteforce"]["evals"] == 6561
        assert c["pso"]["evals"] == 20 * (c["pso"]["k_stop"] + 1) and c["pso"]["evals"] < c["bruteforce"]["evals"]
        assert set(c["timing_ms"]) == {"cold", "warm"} and all(t["pso_ms"] > 0 and t["bruteforce_ms"] > 0 for t in c["timing_ms"].values())
    same = replay_cycle(store, profiles[0], PSOParams(), FitnessWeights(), 20260923)             # la solución del PSO es la del núcleo de las corridas históricas
    assert rep["cases"][0]["pso"]["S"] == same["S"] and rep["cases"][0]["pso"]["F"] == same["F"]
    assert set(rep["timing_summary_ms"]) == {"cold", "warm"} and 0 <= rep["search_quality"]["share_pso_at_global_optimum"] <= 1


def test_no_latency_claim_without_valid_hardware_dataset_and_repetitions():
    ok = bb.claim_conditions(HW_OK, 100, 5)
    assert ok["claim_allowed"] is True and "NO CONCLUYENTE" not in ok["verdict"] and "no equivale a L_resp" in ok["verdict"]
    local = {"vcpu": 8, "ram_gib": 7.53}                                                       # la máquina de las mediciones históricas (7.5 GiB)
    for hw, n, r, why in ((local, 100, 5, "hardware"), ({"vcpu": 4, "ram_gib": 32.0}, 100, 5, "hardware"), (HW_OK, 2, 5, "solo 2 perfiles"), (HW_OK, 100, 1, "repeticiones")):
        c = bb.claim_conditions(hw, n, r)
        assert c["claim_allowed"] is False and c["verdict"].startswith("NO CONCLUYENTE") and "No se afirma reducción de latencia ni de carga" in c["verdict"] and why in c["verdict"]
    assert bb.meets_target(HW_OK) and not bb.meets_target(local) and bb.meets_target({"vcpu": 8, "ram_gib": 29.0}) and not bb.meets_target({"vcpu": 8, "ram_gib": 28.0})


def test_the_report_of_a_small_local_measurement_is_not_conclusive(store, profiles):
    rep = bb.run_baseline(store, profiles[:1], PSOParams(), FitnessWeights(), 20260923, repeats=1, warmup=0)         # hardware real de esta máquina
    assert rep["claim"]["claim_allowed"] is False and rep["claim"]["verdict"].startswith("NO CONCLUYENTE")
    assert "BÚSQUEDA" in bb.to_markdown(rep) and "no `L_resp`" in bb.to_markdown(rep)
    hw = bb.hardware_profile()
    assert hw["vcpu"] and hw["python"] and set(hw) >= {"vcpu", "cpu_model", "ram_gib", "python", "numpy", "platform"}


def test_baseline_report_is_written_to_a_new_directory_only(tmp_path, store, profiles):
    rep = bb.run_baseline(store, profiles[:1], PSOParams(), FitnessWeights(), 20260923, repeats=1, warmup=0, hardware=HW_OK)
    out = bb.write_report(rep, tmp_path / "nuevo")
    assert sorted(p.name for p in out.iterdir()) == ["baseline.json", "baseline.md"] and json.loads((out / "baseline.json").read_text())["claim"]["claim_allowed"] is False
    with pytest.raises(SystemExit):
        bb.write_report(rep, tmp_path / "nuevo")                                                # no se sobrescribe
    with pytest.raises(SystemExit):
        bb.write_report(rep, RESULTS / "baseline_no")                                           # ni dentro de resultados congelados


# ── alternativas de Balanced ────────────────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def report():
    return ba.build_report()


def test_every_result_is_provisional_and_balanced_is_never_excluded(report):
    assert report["status"] == "PROVISIONAL" and report["official"] is False and report["banner"].startswith("PROVISIONAL")
    assert all(a["status"] == "PROVISIONAL" and a["official"] is False for a in report["alternatives"])
    md = ba.to_markdown(report)
    assert md.splitlines()[0].endswith("PROVISIONAL") and "PROVISIONAL" in md.splitlines()[2] and "no se excluye" in md
    for a in report["alternatives"]:
        for m in a["per_run"].values():
            if "n_cases" in m:
                assert m["n_cases"] == 100                                                     # los 100 perfiles, Balanced incluido: ningún arquetipo se descarta
    assert "0.854" not in md and "0.854" not in json.dumps(report)                            # este informe no contiene el análisis que excluye a Balanced


def test_the_four_families_and_the_historical_reference_are_present(report):
    ids = [a["id"] for a in report["alternatives"]]
    assert ids[0] == "gold-v1+dominant-compat" and "five-class-balanced" in ids and len(ids) == 1 + 3 * 4 + 1
    assert {a["family"].split(" ×")[0] for a in report["alternatives"] if a["id"].startswith("gold-v2")} == {
        "conjunto de modalidades esperadas", "tolerancia de empate (0.05)", "tolerancia de empate (0.35)"}
    assert {i for i in ids if "+incl-" in i and i.startswith("gold-v2-cand-A")} == {f"gold-v2-cand-A+incl-{x}" for x in ("ge1", "ge2", "top-tol0", "top-tol1")}
    five = next(a for a in report["alternatives"] if a["id"] == "five-class-balanced")["per_run"]["corrida-poc-1"]
    assert len(five["matrix_5x5"]) == 5 and sum(map(sum, five["matrix_5x5"])) == 100 and five["classes"][-1] == "balanced"


def test_the_historical_reference_reproduces_the_frozen_f1(report):
    hist = next(a for a in report["alternatives"] if a["id"] == "gold-v1+dominant-compat")
    for label in ("corrida-poc-1", "corrida-poc-2"):
        cases = [c for c in json.loads((RESULTS / f"adaptation_swarm_{label}.json").read_text(encoding="utf-8"))["cases"] if c["status"] == "completed"]
        h = f1_hist.f1_report([(c["expected"], c["predicted"]) for c in cases])
        m = hist["per_run"][label]
        assert m["macro_defined"] == h.f1_adapt and m["micro_f1"] == h.accuracy and m["n_gold_differs_from_v1"] == 0


def test_equivalent_alternatives_are_flagged_and_the_gold_change_is_confined_to_balanced(report):
    by_id = {a["id"]: a for a in report["alternatives"]}
    for inc in ("ge1", "ge2", "top-tol0", "top-tol1"):
        assert by_id[f"gold-v2-cand-B-tol0.05+incl-{inc}"]["equivalent_to"] == f"gold-v2-cand-A+incl-{inc}"       # con centroids-v1 la tolerancia 0.05 equivale a A
    m = by_id["gold-v2-cand-A+incl-ge2"]["per_run"]["corrida-poc-1"]
    assert m["gold_differs_from_v1_by_archetype"] == {"balanced_multimodal": 25} and m["n_gold_differs_from_v1"] == 25        # A solo cambia el gold de Balanced
    assert by_id["gold-v2-cand-B-tol0.35+incl-ge1"]["per_run"]["corrida-poc-1"]["n_gold_differs_from_v1"] == 75


def test_the_report_never_touches_the_frozen_sources_and_records_their_hashes(report, tmp_path):
    doc = (RESULTS / "adaptation_swarm_frozen_runs.md").read_text(encoding="utf-8")
    manifest = json.loads(re.search(r"```json\n(.*?)\n```", doc, re.S).group(1))["runs"]
    for label, src in report["source"].items():
        f = RESULTS / src["file"]
        assert src["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest() == manifest[label]["artifacts"][src["file"]]
    out = ba.write_report(report, tmp_path / "nuevo")
    assert sorted(p.name for p in out.iterdir()) == ["balanced_alternatives_PROVISIONAL.json", "balanced_alternatives_PROVISIONAL.md"]
    with pytest.raises(SystemExit):
        ba.write_report(report, tmp_path / "nuevo")
    for bad in (RESULTS / "nuevo", ROOT / "datasets" / "nuevo", ROOT / "backend" / "experiments" / "evidence_package_2026-09-24-final" / "nuevo"):
        with pytest.raises(SystemExit):
            ba.write_report(report, bad)


def test_the_report_is_deterministic():
    assert json.dumps(ba.build_report(), sort_keys=True) == json.dumps(ba.build_report(), sort_keys=True)
