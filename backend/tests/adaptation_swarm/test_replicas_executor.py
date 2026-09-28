"""Ejecutor puro de réplicas (D5: K = 10 con semillas independientes) y núcleo de re-ejecución. Puras: leen el manifiesto y los artefactos NO-audio de la biblioteca; no usan
PostgreSQL, Redis, audio ni red. Comprueban independencia de semillas, la puerta de aprobación (no hay corrida oficial posible mientras la regla no esté aprobada), ausencia de
sobrescritura, determinismo, integridad por hash y compatibilidad exacta del núcleo con la corrida histórica."""

import json
from pathlib import Path

import pytest

from adaptation_swarm.analysis import replicas as rp
from adaptation_swarm.analysis.core_replay import replay_cycle
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.f1_multilabel import cases_from_records, multilabel_report
from adaptation_swarm.gold.rubric_v2 import NoRuleSelected, RuleNotApproved, official_version, get_rule
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.pso.params import PSOParams
from adaptation_swarm.schemas.ids import derive_seed
from adaptation_swarm.tools import isolated_env as iso

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "backend" / "experiments" / "results"
LIB = "lib-v5-9ae9ffdd"                                     # la biblioteca de corrida-poc-1
MASTER = 424242                                             # semilla maestra de PRUEBA (no es la de ninguna corrida oficial)
UNAPPROVED_RULE = ("gold-v2-cand-A", "incl-ge2")            # gold-v2 REGISTRADA pero ausente de APPROVED_RULE_VERSIONS: ejemplo de «regla no aprobada» para los guards (la oficial ya está registrada)


@pytest.fixture(scope="module")
def profiles():
    return read_dataset(rp.DEFAULT_PROFILES)


@pytest.fixture(scope="module")
def store():
    return LibraryStore.open(SETTINGS.library_root, LIB)


def _plan(**kw):
    base = dict(master_seed=MASTER, k=2, library_version=LIB, provisional=True, limit_profiles=3)
    return rp.build_plan(**{**base, **kw})


# ── semillas independientes ─────────────────────────────────────────────────────────────────────────────────────────
def test_batch_seeds_are_distinct_deterministic_63_bit_and_not_historical():
    s = rp.derive_batch_seeds(MASTER, rp.K_OFFICIAL)
    assert len(s) == 10 and len(set(s)) == 10 and s == rp.derive_batch_seeds(MASTER, 10)
    assert all(0 <= x < 2 ** 63 for x in s) and not set(s) & rp.HISTORICAL_BATCH_SEEDS
    other = rp.derive_batch_seeds(MASTER + 1, 10)
    assert not set(s) & set(other)                                                          # otra semilla maestra ⇒ conjunto disjunto
    assert rp.derive_batch_seeds(MASTER, 3) == s[:3]                                        # prefijo estable: añadir réplicas no cambia las anteriores
    with pytest.raises(ValueError):
        rp.derive_batch_seeds(MASTER, 0)


def test_case_seeds_are_independent_across_the_ten_replicas_and_the_hundred_profiles(profiles):
    seeds = [derive_seed(bs, p.profile_id, 0) for bs in rp.derive_batch_seeds(MASTER, 10) for p in profiles]
    assert len(seeds) == 1000 and len(set(seeds)) == 1000
    assert not {derive_seed(next(iter(rp.HISTORICAL_BATCH_SEEDS)), p.profile_id, 0) for p in profiles} & set(seeds)     # ninguna coincide con las corridas históricas


# ── puerta de aprobación: nada oficial mientras la regla no esté aprobada ───────────────────────────────────────────
def test_an_official_run_cannot_be_planned_while_no_rule_is_approved():
    with pytest.raises(NoRuleSelected):
        rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False)
    with pytest.raises(RuleNotApproved):
        rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=get_rule(*UNAPPROVED_RULE))
    assert rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=True)["status"] == "PROVISIONAL"       # lo exploratorio hay que pedirlo


def test_an_official_run_demands_an_approved_rule_k_10_and_all_profiles(monkeypatch):
    rule = get_rule("gold-v2-cand-A", "incl-ge1")
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))
    ok = rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=rule)
    assert ok["status"] == "OFICIAL" and ok["k"] == 10 and ok["dataset"]["n_used"] == 100 and ok["rule"]["status"] == "OFICIAL"
    with pytest.raises(ValueError, match="K = 10"):
        rp.build_plan(master_seed=MASTER, k=3, library_version=LIB, provisional=False, rule=rule)
    with pytest.raises(ValueError, match="100 perfiles"):
        rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=rule, limit_profiles=5)


# ── ejecución, manifiesto, determinismo e integridad ────────────────────────────────────────────────────────────────
def test_plan_computes_nothing_and_run_writes_plan_replicas_and_manifest_with_hashes(tmp_path):
    plan = _plan()
    out = rp.write_plan(plan, tmp_path / "solo_plan")
    assert sorted(p.name for p in out.iterdir()) == ["plan.json"]                          # planificar no ejecuta nada
    m = rp.run(plan, tmp_path / "corrida")
    files = sorted(p.name for p in (tmp_path / "corrida").iterdir())
    assert files == ["manifest.json", "plan.json", "replica_00.json", "replica_01.json"] and rp.verify(tmp_path / "corrida") == []
    assert m["schema"] == rp.SCHEMA_MANIFEST and m["status"] == "PROVISIONAL" and m["k"] == 2 and len(m["batch_seeds"]) == 2 and m["master_seed"] == MASTER
    assert m["n_case_seeds"] == m["n_distinct_case_seeds"] == 6                                # 2 réplicas × 3 perfiles, todas las semillas de ciclo distintas
    assert all(len(e["sha256"]) == 64 and e["n_cases"] == 3 for e in m["replicas"])
    assert len(m["library"]["manifest_sha256"]) == 64 and len(m["dataset"]["sha256"]) == 64 and m["dataset"]["limited"] is True
    assert set(m["modules"]) >= {"pso/engine.py", "fitness/fitness.py", "analysis/core_replay.py"} and all(len(h) == 64 for h in m["modules"].values())
    case = rp.replica_cases(tmp_path / "corrida", 0)[0]
    assert set(case) == {"profile_id", "archetype", "difficulty", "concept_id", "seed", "S", "F", "k_stop", "stop_reason"} and len(case["S"]) == 8


def test_the_same_input_gives_byte_identical_replicas_and_manifest(tmp_path):
    rp.run(_plan(), tmp_path / "a")
    rp.run(_plan(), tmp_path / "b")
    for name in ("plan.json", "replica_00.json", "replica_01.json", "manifest.json"):
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes(), name
    rp.run(_plan(master_seed=MASTER + 1), tmp_path / "c")
    assert (tmp_path / "a" / "replica_00.json").read_bytes() != (tmp_path / "c" / "replica_00.json").read_bytes()      # otra semilla maestra ⇒ otras réplicas


def test_replicas_are_actually_independent_runs(tmp_path, profiles):
    rp.run(_plan(limit_profiles=12), tmp_path / "x")
    r0, r1 = rp.replica_cases(tmp_path / "x", 0), rp.replica_cases(tmp_path / "x", 1)
    assert [c["profile_id"] for c in r0] == [c["profile_id"] for c in r1]                  # mismo dataset
    assert all(a["seed"] != b["seed"] for a, b in zip(r0, r1))                             # semillas de ciclo distintas
    assert any((a["S"], a["F"], a["k_stop"]) != (b["S"], b["F"], b["k_stop"]) for a, b in zip(r0, r1))                 # y trayectorias distintas
    rep = multilabel_report(cases_from_records(r0, get_rule("gold-v2-cand-A", "incl-ge2")), get_rule("gold-v2-cand-A", "incl-ge2"))    # las réplicas alimentan la métrica
    assert rep.n_cases == 12 and rep.status == "PROVISIONAL"


def test_nothing_is_ever_overwritten_and_protected_directories_are_refused(tmp_path):
    plan = _plan()
    rp.run(plan, tmp_path / "a")
    with pytest.raises(SystemExit, match="no se sobrescriben"):
        rp.run(plan, tmp_path / "a")                                                       # el directorio existe: la guardia de isolated_env lo rechaza
    (tmp_path / "vacio").mkdir()
    with pytest.raises(FileExistsError):
        rp.write_plan(plan, tmp_path / "vacio")                                            # segunda línea de defensa: ni un directorio existente pero vacío se reutiliza
    with pytest.raises(FileExistsError):
        rp._write_new(tmp_path / "a" / "replica_00.json", b"x")                            # ni un archivo existente
    for bad in (RESULTS / "nueva", ROOT / "datasets" / "nueva", ROOT / "backend" / "experiments" / "evidence_package_2026-09-24-final" / "nueva"):
        with pytest.raises(SystemExit):
            rp.write_plan(plan, bad)
        assert not bad.exists()
    assert (RESULTS / "adaptation_swarm_corrida-poc-1.json").exists()                      # y las corridas históricas siguen ahí


def test_tampering_with_a_replica_or_the_plan_is_detected(tmp_path):
    rp.run(_plan(), tmp_path / "a")
    rep = tmp_path / "a" / "replica_01.json"
    rep.write_bytes(rep.read_bytes().replace(b'"k_stop":', b'"k_stop":9', 1))
    assert any("replica_01.json" in p for p in rp.verify(tmp_path / "a"))
    (tmp_path / "a" / "plan.json").write_bytes(b"{}\n")
    assert any("plan.json" in p for p in rp.verify(tmp_path / "a"))


def test_run_refuses_a_plan_whose_inputs_changed(tmp_path):
    plan = _plan()
    plan["library"]["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="manifiesto de la biblioteca"):
        rp.run(plan, tmp_path / "a")
    assert not (tmp_path / "a").exists()                                                   # falla ANTES de crear nada


# ── el núcleo reproduce la evidencia histórica ──────────────────────────────────────────────────────────────────────
def test_the_core_replay_matches_corrida_poc_1_case_by_case(store, profiles):
    d = json.loads((RESULTS / "adaptation_swarm_corrida-poc-1.json").read_text(encoding="utf-8"))
    cases = {c["profile_id"]: c for c in d["cases"]}
    for p in profiles[:12]:
        r = replay_cycle(store, p, PSOParams(), FitnessWeights(), d["config"]["batch_seed"])
        c = cases[p.profile_id]
        assert (r["S"], r["k"], r["F"]) == (c["g_best_S"], c["k_stop"], c["g_best_F"]) and r["stop_reason"] == c["stop_reason"]


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def test_cli_requires_explicit_seed_and_provisional_flag_and_never_runs_officially(tmp_path, capsys):
    with pytest.raises(SystemExit):
        rp.main(["plan", "--library-version", LIB, "--out-dir", str(tmp_path / "x")])          # --master-seed obligatorio: sin semilla por defecto
    with pytest.raises(NoRuleSelected):
        rp.main(["run", "--master-seed", str(MASTER), "--library-version", LIB, "--out-dir", str(tmp_path / "y")])            # oficial sin regla
    with pytest.raises(RuleNotApproved):
        rp.main(["run", "--master-seed", str(MASTER), "--library-version", LIB, "--out-dir", str(tmp_path / "z"),
                 "--gold-rule", UNAPPROVED_RULE[0], "--inclusion-rule", UNAPPROVED_RULE[1]])                                   # regla sin aprobar
    assert not any((tmp_path / n).exists() for n in ("y", "z"))
    rp.main(["run", "--master-seed", str(MASTER), "--library-version", LIB, "--out-dir", str(tmp_path / "w"), "--provisional", "--limit-profiles", "2", "--k", "2"])
    assert "PROVISIONAL" in capsys.readouterr().out and rp.verify(tmp_path / "w") == []
    with pytest.raises(SystemExit):
        rp.main(["plan", "--master-seed", "1", "--library-version", LIB, "--provisional"])                                       # --out-dir obligatorio


# ── A: run() no confía en el plan: revalida la puerta oficial dentro de la propia ejecución ─────────────────────────
import copy

from adaptation_swarm.gold.rubric_v2 import LegacyDominantRule

OFFICIAL_RULE = ("gold-v2-cand-A", "incl-ge1")


def _official_plan(monkeypatch):
    rule = get_rule(*OFFICIAL_RULE)
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))              # aprobación SOLO en memoria y solo durante la prueba
    return rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=rule)


def _rewrite(plan, path, value):
    p = copy.deepcopy(plan)
    node = p
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return p


def test_run_ignores_a_forged_official_status_when_no_rule_is_approved(tmp_path):
    rule = get_rule(*UNAPPROVED_RULE)
    forged_no_rule = _rewrite(_plan(k=10, limit_profiles=None), ["status"], "OFICIAL")                     # plan PROVISIONAL al que se le cambia el estado
    with pytest.raises(NoRuleSelected):
        rp.run(forged_no_rule, tmp_path / "a")
    forged_rule = _rewrite(forged_no_rule, ["rule"], {**rule.to_dict(), "status": "OFICIAL"})              # además se incrusta una regla que dice estar OFICIAL
    with pytest.raises(RuleNotApproved):
        rp.run(forged_rule, tmp_path / "b")
    unknown = _rewrite(forged_rule, ["rule", "gold", "rule_version"], "gold-v2-inventada")
    with pytest.raises(ValueError, match="plan incompleto o manipulado"):
        rp.run(unknown, tmp_path / "c")
    assert list(tmp_path.iterdir()) == []                                                                   # ninguna salida creada: ni plan, ni réplicas, ni manifiesto


def test_run_rejects_the_legacy_rule_even_if_someone_approved_its_version(tmp_path, monkeypatch):
    legacy = LegacyDominantRule()
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({legacy.rule_version}))
    with pytest.raises(RuleNotApproved):
        rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=legacy)
    forged = _rewrite(_plan(k=10, limit_profiles=None), ["status"], "OFICIAL")
    forged["rule"] = {**legacy.to_dict(), "status": "OFICIAL"}
    with pytest.raises(ValueError, match="plan incompleto o manipulado"):                                   # no es una regla gold-v2 registrada
        rp.run(forged, tmp_path / "a")
    assert not (tmp_path / "a").exists()


@pytest.mark.parametrize("path,value,why", [
    (["k"], 3, "K distinto de 10"), (["batch_seeds"], None, "semillas truncadas"), (["dataset", "n_used"], 50, "menos de 100 perfiles"),
    (["dataset", "limited"], True, "dataset marcado como limitado"), (["dataset", "n_profiles"], 99, "n_profiles falso"), (["master_seed"], 1, "semilla maestra distinta"),
    (["config", "replicate_index"], 5, "configuración alterada"), (["modules"], {}, "módulos borrados"), (["independence"], {}, "independencia borrada"),
    (["extra"], 1, "clave añadida"), (["status"], "OFICIAL ", "estado no reconocido"), (["status"], None, "estado nulo"),
    (["rule", "gold", "description"], "alterada", "regla con contenido alterado"), (["rule", "status"], "PROVISIONAL", "estado de la regla alterado")])
def test_run_rejects_any_tampered_or_incomplete_official_plan(tmp_path, monkeypatch, path, value, why):
    plan = _official_plan(monkeypatch)
    assert rp.revalidate_plan(plan) == "OFICIAL"                                                            # el plan legítimo sí pasa
    if path == ["batch_seeds"]:
        value = plan["batch_seeds"][:5]
    bad = _rewrite(plan, path, value) if path != ["extra"] else {**plan, "extra": 1}
    with pytest.raises((ValueError, RuleNotApproved, NoRuleSelected)):
        rp.run(bad, tmp_path / "a")
    assert not (tmp_path / "a").exists(), why


def test_run_rejects_plans_with_missing_fields_or_wrong_schema(tmp_path, monkeypatch):
    plan = _official_plan(monkeypatch)
    for key in ("status", "rule", "k", "batch_seeds", "dataset", "library", "config", "master_seed"):
        bad = {k: v for k, v in plan.items() if k != key}
        with pytest.raises(ValueError):
            rp.run(bad, tmp_path / f"m_{key}")
    for bad in ({}, {"schema": "otro"}, None, []):
        with pytest.raises(ValueError):
            rp.run(bad, tmp_path / "s")
    assert list(tmp_path.iterdir()) == []


def test_official_plan_with_a_shortened_dataset_is_rejected_before_creating_anything(tmp_path, monkeypatch):
    plan = _official_plan(monkeypatch)
    short = tmp_path / "profiles_99.jsonl"
    short.write_bytes(b"".join(rp.DEFAULT_PROFILES.read_bytes().splitlines(keepends=True)[:99]))
    forged = _rewrite(plan, ["dataset"], {"file": short.name, "sha256": rp._sha_file(short), "n_profiles": 99, "n_used": 99, "limited": False})     # plan COHERENTE con 99 perfiles
    with pytest.raises(ValueError, match="100 perfiles"):                                                    # lo rechaza la puerta oficial, no una simple discrepancia
        rp.run(forged, tmp_path / "a", profiles_path=short)
    assert not (tmp_path / "a").exists()


def test_a_legitimate_official_shaped_plan_runs_and_the_manifest_status_comes_from_revalidation(tmp_path, monkeypatch):
    plan = _official_plan(monkeypatch)                                                                       # aprobación en memoria; solo escribe en tmp_path; NO es una corrida oficial
    m = rp.run(plan, tmp_path / "a")
    assert m["status"] == "OFICIAL" and m["k"] == 10 and m["dataset"]["n_used"] == 100 and m["n_case_seeds"] == m["n_distinct_case_seeds"] == 1000
    assert m["rule"]["rule_version"] == "gold-v2-cand-A+incl-ge1" and m["rule"]["status"] == "OFICIAL" and rp.verify(tmp_path / "a") == []
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == ["manifest.json", "plan.json"] + [f"replica_{i:02d}.json" for i in range(10)]


def test_without_approval_no_plan_can_produce_an_official_manifest(tmp_path):
    plan = _plan(k=10, limit_profiles=None)                                                                  # PROVISIONAL legítimo (sin regla aprobada)
    assert rp.revalidate_plan(plan) == "PROVISIONAL"
    m = rp.run(plan, tmp_path / "a")
    assert m["status"] == "PROVISIONAL" and m["rule"] is None                                                # nunca OFICIAL por sí solo


def test_downgrading_an_official_plan_to_provisional_is_safe_and_never_yields_an_official_manifest(tmp_path, monkeypatch):
    plan = _official_plan(monkeypatch)
    downgraded = _rewrite(plan, ["status"], "PROVISIONAL")                                                   # es exactamente un plan PROVISIONAL legítimo con la misma regla
    assert rp.revalidate_plan(downgraded) == "PROVISIONAL"
    assert rp.run(downgraded, tmp_path / "a")["status"] == "PROVISIONAL"
