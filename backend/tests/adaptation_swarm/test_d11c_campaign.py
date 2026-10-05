"""Campaña D11C-EMPIRICAL-BASELINE (PSO vs fuerza bruta). Puras: biblioteca no-audio, sin Redis, PostgreSQL ni red. Comprueban mismo espacio/caso/criterio, reproducibilidad del PSO, óptimo de la fuerza bruta,
ΔF, que D11C NO publica T_conv (`t_conv_ms`) y que la provenance registra valores reales con identidad NO oficial. No pretenden demostrar equivalencia con el T_conv de AG0 (no la hay)."""

import hashlib
import json
import re
import subprocess
from pathlib import Path

import pytest

from adaptation_swarm.analysis import baseline_bruteforce as bb
from adaptation_swarm.analysis import d11c_campaign as d11c
from adaptation_swarm.analysis.core_replay import variant_terms
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights, evaluate
from adaptation_swarm.metrics.search_quality import brute_force_optimum
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.profiles.w_mapping import compute_weights
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.pso.space import SPACE_SIZE, Configuration, all_configurations

LIB = "lib-v5-9ae9ffdd"
HW_OK = {"vcpu": 8, "ram_gib": 32.0, "cpu_model": "x", "python": "3.x", "numpy": "x", "platform": "x"}
SHA256 = re.compile(r"[0-9a-f]{64}")
REPLICATES = 2


@pytest.fixture(scope="module")
def store():
    return LibraryStore.open(SETTINGS.library_root, LIB)


@pytest.fixture(scope="module")
def profiles():
    return read_dataset(bb.DEFAULT_PROFILES)[:2]


@pytest.fixture(scope="module")
def rows(store, profiles):
    return d11c.run_cases(store, profiles, PSOParams(), FitnessWeights(), 777, campaign_id="T", replicates=REPLICATES, repeats=1, warmup=0)


def test_both_methods_search_the_same_space_for_the_same_case_with_the_same_criterion(store, profiles, rows):
    vectors = {c.vector for c in all_configurations()}
    assert len(vectors) == SPACE_SIZE == 6561
    fw = FitnessWeights()
    for r in rows:
        assert tuple(r["S"]) in vectors and r["space_size"] == SPACE_SIZE
        prof = next(p for p in profiles if p.profile_id == r["profile_id"])
        cfg = Configuration(tuple(r["S"]))
        f = evaluate(cfg, compute_weights(prof).by_modality(), *variant_terms(store, prof.concept_id, cfg.variants, {}), fw).F    # el MISMO 𝓕 y W reproducen el F de cada método
        assert f == pytest.approx(r["F"], abs=1e-12)
    assert all(r["n_evaluations"] == SPACE_SIZE for r in rows if r["method"] == "bruteforce")
    assert all(r["n_evaluations"] == 20 * (r["k_stop"] + 1) < SPACE_SIZE for r in rows if r["method"] == "pso")


def test_bruteforce_finds_the_known_global_optimum(store, profiles, rows):
    for p in profiles:
        ref = brute_force_optimum(store, p.concept_id, compute_weights(p), FitnessWeights())
        bf = [r for r in rows if r["profile_id"] == p.profile_id and r["method"] == "bruteforce"]
        assert len(bf) == 2 and all((tuple(r["S"]), r["F"]) == (ref.S, ref.F) for r in bf)
        assert all(r["F"] <= ref.F + 1e-12 for r in rows if r["profile_id"] == p.profile_id)         # nadie supera el óptimo global


def test_pso_is_reproducible_and_seed_is_derived_per_replicate(store, profiles, rows):
    again = d11c.run_cases(store, profiles, PSOParams(), FitnessWeights(), 777, campaign_id="T", replicates=REPLICATES, repeats=1, warmup=0)
    key = lambda rs: [(r["run_id"], r["seed"], tuple(r["S"]), r["F"], r["k_stop"], r["delta_F"]) for r in rs]
    assert key(rows) == key(again)
    pso = [r for r in rows if r["method"] == "pso"]
    assert len({r["seed"] for r in pso}) == len({(r["profile_id"], r["replicate"]) for r in pso}) == 2 * REPLICATES          # una semilla por (perfil, réplica); cold y warm la comparten
    assert len({r["run_id"] for r in rows}) == len(rows)


def test_delta_f_is_f_star_of_bruteforce_minus_pso_f(rows):
    pso = [r for r in rows if r["method"] == "pso"]
    assert len(pso) == 2 * 2 * REPLICATES                                              # 2 perfiles × 2 modos × réplicas
    for r in pso:
        bf = next(x for x in rows if x["method"] == "bruteforce" and x["profile_id"] == r["profile_id"] and x["timing_mode"] == r["timing_mode"])
        assert r["F_star"] == bf["F"] and r["delta_F"] == pytest.approx(bf["F"] - r["F"], abs=1e-15) and r["delta_F"] >= -1e-12
        assert r["pso_at_global_optimum"] == (r["delta_F"] <= 1e-12)


def test_d11c_never_publishes_t_conv_and_pso_search_ms_is_the_measured_search_time(rows):
    for r in rows:
        assert "t_conv_ms" not in r and "T_conv" not in r and r["elapsed_search_ms"] > 0
        if r["method"] == "bruteforce":
            assert r["pso_search_ms"] is None and r["seed"] is None and r["k_stop"] is None
        else:
            assert r["pso_search_ms"] > 0 and r["pso_search_ms"] == r["elapsed_search_ms"] and r["seed"] is not None
    d = d11c.describe(rows)
    assert "t_conv_reported" not in d and "t_conv_ms_pso" not in d and not [k for k in d if k.startswith("t_conv")]            # el resumen no genera ninguna métrica t_conv*
    assert d["reserved_metrics"] == {"T_conv": "T_conv oficial no es producido por D11C"} and d["pso_search_ms"]["cold"]["n"] == 2 * REPLICATES
    assert "T_conv" in d11c.TIME_METRICS and "NO es T_conv" in d11c.TIME_METRICS["pso_search_ms"] and "no T_conv oficial" in d11c.SCOPE and "L_resp HTTP" in d11c.SCOPE


def test_summary_counts_are_the_real_executions_of_each_method(rows):
    d = d11c.describe(rows)
    assert d["n_runs"] == {"pso": 2 * 2 * REPLICATES, "bruteforce": 2 * 2}               # fuerza bruta: una ejecución por (perfil, modo), sin copias por réplica
    assert d["elapsed_search_ms"]["cold"]["bruteforce"]["n"] == 2 and d["elapsed_search_ms"]["cold"]["pso"]["n"] == 2 * REPLICATES
    assert d["delta_F"]["n"] == 2 * REPLICATES and "NO definida" in d["inference"] and d["delta_F"]["min"] >= -1e-12


def test_campaign_identity_cannot_be_changed_or_made_to_look_official(store, profiles, rows):
    for bad in ("OE2-OFFICIAL", "x-oe2-run", "run-Official", "corrida-oficial"):
        with pytest.raises(SystemExit, match="OE2|oficial"):
            d11c.validate_campaign_id(bad)
    assert d11c.validate_campaign_id("smoke-2026-10-05") == "smoke-2026-10-05"
    prov = d11c.provenance(store, bb.DEFAULT_PROFILES, profiles, PSOParams(), FitnessWeights(), campaign_id="T", batch_seed=777, replicates=REPLICATES, repeats=1, warmup=0, hardware=HW_OK)
    assert (prov["campaign"], prov["official"], prov["oe2_official"]) == ("D11C-EMPIRICAL-BASELINE", False, False)
    assert all(r["campaign"] == "D11C-EMPIRICAL-BASELINE" and r["official"] is False and r["run_id"].startswith("D11C-EMPIRICAL-BASELINE|T|") for r in rows)
    with pytest.raises(ValueError):
        d11c.write_campaign(Path("unused"), {**prov, "official": True}, rows)
    with pytest.raises(ValueError):
        d11c.write_campaign(Path("unused"), prov, [{**rows[0], "t_conv_ms": 1.0}])


def test_d11c_conditions_are_technical_and_never_an_authorization():
    met = d11c.d11c_conditions({"vcpu": 20, "ram_gib": 31.75}, 100, 5)
    assert met["d11c_technical_conditions_met"] is True and "claim_allowed" not in met
    assert {"OE2", "benchmark §2.1", "resultado oficial"} <= set(met["not_authorization_of"]) and "NO autorizan OE2" in met["verdict"]
    assert d11c.d11c_conditions({"vcpu": 20, "ram_gib": 31.75}, 3, 1)["d11c_technical_conditions_met"] is False


def test_provenance_records_real_values_and_honest_code_state(store, profiles):
    prov = d11c.provenance(store, bb.DEFAULT_PROFILES, profiles, PSOParams(), FitnessWeights(), campaign_id="T", batch_seed=777, replicates=REPLICATES, repeats=1, warmup=0, hardware=HW_OK)
    assert re.fullmatch(r"[0-9a-f]{40}", prov["code"]["commit"]) and prov["code"]["dirty"] is None            # code_version() no determina el árbol; no se inventa
    assert prov["code_state"]["dirty"] in (True, False, None) and prov["code_state"]["method"] == "git status --porcelain"
    fp = prov["campaign_module_fingerprints"]
    root = Path(d11c.__file__).resolve().parents[1]
    assert set(fp) == {"analysis/d11c_campaign.py", "analysis/baseline_bruteforce.py"}
    for name, h in fp.items():
        assert SHA256.fullmatch(h) and h == hashlib.sha256((root / name).read_bytes()).hexdigest()            # corresponde al código real
    assert len(prov["module_fingerprints"]) == 19 and all(SHA256.fullmatch(h) for h in prov["module_fingerprints"].values())
    assert prov["library_version"] == LIB and prov["dataset"]["version"] == "v1" and SHA256.fullmatch(prov["dataset"]["manifest_sha256"]) and prov["dataset"]["n_profiles"] == 2
    assert prov["pso"]["config_hash"] == PSOParams().config_hash() and prov["objective"]["weights"] == FitnessWeights().to_dict() and prov["hardware"] == HW_OK
    assert prov["design"]["space_size"] == 6561 and prov["time_metrics"] == d11c.TIME_METRICS and prov["scope"] == d11c.SCOPE
    assert prov["definitions"]["t_conv"] == d11c.oe_defs.DEFINITIONS["t_conv"] and "reemplaza o complementa" in prov["open_question"]
    assert "rules (sin aprobación como línea base oficial)" in prov["not_included"]


@pytest.mark.parametrize("stdout, dirty, n", [("", False, 0), (" M a.py\n?? b.py\n", True, 2)])
def test_git_state_reports_the_real_tree_state(monkeypatch, stdout, dirty, n):
    monkeypatch.setattr(d11c.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=stdout, stderr=""))
    s = d11c.git_state()
    assert s["dirty"] is dirty and s["n_modified_or_untracked"] == n and (s["modified_paths"] == (["a.py", "b.py"] if dirty else []))


def test_git_state_is_unknown_not_clean_when_git_is_unavailable(monkeypatch):
    def boom(*a, **k):
        raise OSError("sin git")
    monkeypatch.setattr(d11c.subprocess, "run", boom)
    assert d11c.git_state()["dirty"] is None


def test_artifacts_are_written_unofficial_and_never_overwritten(store, profiles, rows, tmp_path):
    prov = d11c.provenance(store, bb.DEFAULT_PROFILES, profiles, PSOParams(), FitnessWeights(), campaign_id="T", batch_seed=777, replicates=REPLICATES, repeats=1, warmup=0, hardware=HW_OK)
    out = d11c.write_campaign(tmp_path / "d11c", prov, rows)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["official"] is False and set(manifest["files"]) == {"d11c_runs.jsonl", "provenance.json", "summary.json"}
    assert all(manifest["files"][n] == hashlib.sha256((out / n).read_bytes()).hexdigest() for n in manifest["files"])
    saved = [json.loads(l) for l in (out / "d11c_runs.jsonl").read_text().splitlines()]
    assert saved == json.loads(json.dumps(rows)) and not any("t_conv_ms" in r for r in saved)
    with pytest.raises(SystemExit, match="ya existe"):                                  # contrato real de `isolated_env.check_output_targets`
        d11c.write_campaign(tmp_path / "d11c", prov, rows)
