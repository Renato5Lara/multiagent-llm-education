"""Corridas congeladas `corrida-poc-1/2`: son evidencia experimental y NO se modifican. Estas pruebas fallan si alguien altera un
artefacto, y recalculan F1, convergencia y auditorías a partir de los datos guardados. Puras: solo leen JSON/CSV y los datasets
versionados; no usan PostgreSQL, Redis, audio, red ni procesos externos. (La comprobación contra Postgres queda diferida.)"""

import ast
import csv
import hashlib
import json
import re
import statistics
from pathlib import Path

import pytest

from adaptation_swarm.analysis import compare_runs
from adaptation_swarm.gold.f1 import f1_report
from adaptation_swarm.gold.rubric import predicted_dominant
from adaptation_swarm.metrics.convergence import convergence_summary
from adaptation_swarm.metrics.cycle import CycleMetrics
from adaptation_swarm.multimodal.versioning import manifest_hash, parse_version

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "backend" / "experiments" / "results"
DOC = RESULTS / "adaptation_swarm_frozen_runs.md"
LABELS = ("corrida-poc-1", "corrida-poc-2")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest() -> dict:
    return json.loads(re.search(r"```json\n(.*?)\n```", DOC.read_text(encoding="utf-8"), re.S).group(1))


def _run(label: str) -> dict:
    return json.loads((RESULTS / f"adaptation_swarm_{label}.json").read_text(encoding="utf-8"))


def _pairs(run: dict) -> list[tuple[str, str]]:
    return [(c["expected"], c["predicted"]) for c in run["cases"]]


def test_frozen_artifacts_match_their_recorded_sha256():
    man = _manifest()
    assert man["schema"] == "frozen-runs-v1" and set(man["runs"]) == set(LABELS)
    for label, info in man["runs"].items():
        for name, sha in info["artifacts"].items():
            assert _sha(RESULTS / name) == sha, f"{name} fue alterado: es evidencia congelada"


def test_dataset_gold_and_library_versions_are_identifiable_and_hash_addressed():
    man = _manifest()
    d = man["dataset"]
    assert _sha(ROOT / d["profiles_file"]) == d["profiles_sha256"] and _sha(ROOT / d["gold_file"]) == d["gold_sha256"]
    assert d["version"] == "v1" and d["gold_rule_version"] == "gold-v1" and d["n_cases"] == 100
    versions = set()
    for label, info in man["runs"].items():
        path = ROOT / info["library_manifest"]
        assert _sha(path) == info["library_manifest_sha256"] and path.parent.name == info["library_version"]
        assert parse_version(info["library_version"])[1] == manifest_hash(json.loads(path.read_text(encoding="utf-8")))   # id = hash del manifiesto
        assert _run(label)["config"]["library_version"] == info["library_version"]
        versions.add(info["library_version"])
    assert versions == {"lib-v5-9ae9ffdd", "lib-v9-a0231e9b"}


@pytest.mark.parametrize("label", LABELS)
def test_run_configuration_matches_the_recorded_seed_pso_and_fitness_weights(label):
    man, cfg = _manifest(), _run(label)["config"]
    assert cfg["run_label"] == label and cfg["batch_seed"] == man["batch_seed"] == 20260923 and cfg["spec_version"] == man["spec_version"]
    assert cfg["pso"] == man["pso"] and cfg["fitness_weights"] == man["fitness_weights"] and cfg["dataset"] == "profiles-v1"
    assert cfg["git"] == man["runs"][label]["executed_with"] and cfg["git"]["dirty"] is True          # se declara: árbol sucio al ejecutar


@pytest.mark.parametrize("label", LABELS)
def test_cases_use_the_versioned_dataset_and_gold_one_case_per_profile(label):
    man, run = _manifest(), _run(label)
    profiles = {p["profile_id"]: p for p in map(json.loads, (ROOT / man["dataset"]["profiles_file"]).read_text(encoding="utf-8").splitlines())}
    gold = {g["profile_id"]: g for g in map(json.loads, (ROOT / man["dataset"]["gold_file"]).read_text(encoding="utf-8").splitlines())}
    cases = run["cases"]
    assert len(cases) == 100 and {c["profile_id"] for c in cases} == set(profiles) == set(gold)          # 1 caso = 1 (perfil, concepto)
    for c in cases:
        p = profiles[c["profile_id"]]
        assert (c["archetype"], c["difficulty"], c["concept"]) == (p["archetype"], p["difficulty"], p["metadata"]["concept_title"])
        assert c["expected"] == gold[c["profile_id"]]["expected_dominant"]
        assert c["predicted"] == predicted_dominant([c["g_best_S"][0], c["g_best_S"][2], c["g_best_S"][4], c["g_best_S"][6]])   # etiqueta desde S


@pytest.mark.parametrize("label", LABELS)
def test_f1_is_recomputed_from_the_stored_cases_and_matches_summary_and_manifest(label):
    run, info = _run(label), _manifest()["runs"][label]
    rep, stored = f1_report(_pairs(run)), run["summary"]["f1"]
    assert stored["n_pairs"] == 100 == run["summary"]["completed"]
    assert rep.f1_adapt == stored["f1_adapt"] == stored["macro_f1_defined"] == info["metrics"]["f1_adapt"]
    assert rep.macro_f1_all4 == stored["macro_f1_all4"] == info["metrics"]["macro_f1_all4"]
    assert rep.confusion.tolist() == stored["confusion"] and rep.accuracy == stored["accuracy"] == info["metrics"]["accuracy"]
    lo, hi = stored["ci95_bootstrap"]
    assert lo <= rep.f1_adapt <= hi and [lo, hi] == info["metrics"]["f1_ci95_bootstrap"]
    assert rep.per_class["audio"].f1 is None                                          # audio nunca es gold: F1 indefinido, no 0 ni 1


@pytest.mark.parametrize("label", LABELS)
def test_the_f1_target_is_not_met_and_the_record_says_so(label):
    """El F1 observado (0.8031) está por debajo del objetivo 0.85 de la asesoría: el registro no lo oculta ni lo declara cumplido."""
    man, info = _manifest(), _manifest()["runs"][label]
    f1 = f1_report(_pairs(_run(label))).f1_adapt
    assert man["f1_target_asesoria"] == 0.85 and info["f1_target_met"] is (f1 >= 0.85) is False
    assert f1 == pytest.approx(0.8031, abs=1e-4)


@pytest.mark.parametrize("label", LABELS)
def test_convergence_and_search_quality_are_recomputed_from_the_cases(label):
    run, info = _run(label), _manifest()["runs"][label]
    cycles = [CycleMetrics(c["profile_id"], "-", c["profile_id"], c["status"], c["stop_reason"], c["k_stop"], c["t_conv_ms"],
                           c["total_ms"], c["g_best_F"]) for c in run["cases"]]
    got, stored = convergence_summary(cycles), run["summary"]["convergence"]
    assert got["CR"] == stored["CR"] == info["metrics"]["CR"] and got["stop_reasons"] == stored["stop_reasons"]
    assert got["k_stop"]["mean"] == pytest.approx(stored["k_stop"]["mean"]) == pytest.approx(info["metrics"]["k_stop_mean"])
    assert got["k_stop"]["max"] == stored["k_stop"]["max"] == info["metrics"]["k_stop_max"]
    assert got["t_conv_ms"]["mean"] == pytest.approx(stored["t_conv_ms"]["mean"], abs=0.01)     # los casos guardan t_conv_ms con 2 decimales
    gaps = [c["gap_vs_bruteforce"] for c in run["cases"]]
    assert statistics.fmean(gaps) == pytest.approx(run["summary"]["search_quality"]["mean_gap_to_global_optimum"]) == pytest.approx(
        info["metrics"]["mean_gap_to_global_optimum"])
    assert all(g >= -1e-12 for g in gaps)                                             # el PSO nunca supera el óptimo global


@pytest.mark.parametrize("label", LABELS)
def test_cases_csv_matches_the_run_json(label):
    rows = list(csv.DictReader((RESULTS / f"adaptation_swarm_{label}_cases.csv").open(encoding="utf-8", newline="")))
    cases = _run(label)["cases"]
    assert len(rows) == len(cases) == 100
    for r, c in zip(rows, cases):
        assert (r["profile_id"], r["expected"], r["predicted"], r["stop_reason"], int(r["k_stop"])) == (
            c["profile_id"], c["expected"], c["predicted"], c["stop_reason"], c["k_stop"])
        assert float(r["g_best_F"]) == pytest.approx(c["g_best_F"]) and json.loads(r["g_best_S"]) == c["g_best_S"]


@pytest.mark.parametrize("label", LABELS)
def test_f1_audit_agrees_with_the_run_and_finds_no_implementation_discrepancy(label):
    run = _run(label)
    audit = json.loads((RESULTS / f"adaptation_swarm_{label}_f1_audit.json").read_text(encoding="utf-8"))
    rep, chk = f1_report(_pairs(run)), audit["implementation_checks"]
    assert audit["run_label"] == label and audit["library_version"] == run["config"]["library_version"] and audit["n"] == 100
    assert chk["prediction_recompute_mismatches"] == [] and chk["gold_table_mismatches"] == [] and chk["confusion_matrix_recompute_equal"] is True
    assert chk["stored_f1_recomputed"] == rep.f1_adapt and audit["f1"]["confusion"] == rep.confusion.tolist()
    for i, m in enumerate(("code", "diagram", "text", "audio")):
        tp = int(rep.confusion[i, i])
        assert audit["tp_fp_fn_by_class"][m] == {"TP": tp, "FP": int(rep.confusion[:, i].sum()) - tp, "FN": int(rep.confusion[i, :].sum()) - tp}
    errors = sum(1 for e, p in _pairs(run) if e != p)
    assert sum(audit["error_causes"].values()) - audit["error_causes"].get("acierto", 0) == errors == len(audit["error_cases"])


def test_pso_audit_of_poc_1_agrees_with_the_run():
    run = _run("corrida-poc-1")
    audit = json.loads((RESULTS / "adaptation_swarm_corrida-poc-1_pso_audit.json").read_text(encoding="utf-8"))
    ks = [c["k_stop"] for c in run["cases"]]
    assert audit["run_label"] == "corrida-poc-1" and audit["n_cycles"] == len(ks) == 100
    assert audit["k_stop"] == {"mean": statistics.fmean(ks), "median": statistics.median(ks), "min": min(ks), "max": max(ks)}
    assert audit["gbest_never_changed_after_init"] + audit["cases_where_search_improved_on_initialization"] == 100


def test_compare_runs_reads_only_json_and_shows_library_version_as_the_only_difference():
    before = {p.name: _sha(p) for p in RESULTS.glob("adaptation_swarm_corrida-poc-*")}
    c = compare_runs.compare(*LABELS)
    assert {p.name: _sha(p) for p in RESULTS.glob("adaptation_swarm_corrida-poc-*")} == before            # no modifica nada
    assert c["config_diff"] == {"library_version": ["lib-v5-9ae9ffdd", "lib-v9-a0231e9b"]}
    assert c["cases"] == 100 and c["predicted_label_changed"] == 0 and c["f1_adapt"][0] == c["f1_adapt"][1]
    assert "Ninguna corrida se modificó" in compare_runs.to_md(c)


def test_compare_runs_has_no_database_network_or_process_dependencies():
    tree = ast.parse(Path(compare_runs.__file__).read_text(encoding="utf-8"))
    imported = {(n.module or "").split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {
        a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    assert imported <= {"argparse", "json", "pathlib", "adaptation_swarm", "__future__"}, imported
