"""`analysis/replicas_v3.py` — ejecutor de réplicas de K = 10 v3 (capa aditiva; K = 10 v2 no se toca). Pruebas PURAS (sin Redis, PostgreSQL, LLM, audio ni red): leen el manifiesto y los artefactos NO-audio de la
biblioteca y escriben SOLO en `tmp_path`. NO ejecutan K = 10 v3: las corridas de estas pruebas son provisionales, con una semilla maestra de PRUEBA y un subconjunto mínimo de perfiles.

Fijan: uso de `rubric_v3` y `statistical_rule_v3` (no de la regla v2), K y semilla configurables con la semilla de K = 10, la MISMA derivación de semillas que v2 (comparabilidad), determinismo por bytes,
identidad de dataset y biblioteca, regla v3 explícita, bloqueo de la ejecución oficial mientras la regla no esté aprobada, separación de salidas v2/v3 y no modificación de los registros de aprobación ni de los
artefactos históricos de v2.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from adaptation_swarm.analysis import replicas as v2rp
from adaptation_swarm.analysis import replicas_v3 as rp3
from adaptation_swarm.analysis import statistical_rule_v3 as sr3
from adaptation_swarm.config import SETTINGS
from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.gold.rubric_v2 import NoRuleSelected, RuleNotApproved
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.profiles.generator import read_dataset

BACKEND = Path(__file__).resolve().parents[2]
LIB = "lib-v5-9ae9ffdd"                                     # biblioteca de las corridas históricas (NO es la de K = 10); solo para corridas provisionales de prueba
MASTER = 424242                                             # semilla maestra de PRUEBA
V2_OFFICIAL_VERSION = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
V2_OFFICIAL_DIR = BACKEND / "official_runs" / "k10_official_2026-09-27"
RULE = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)
FULL = RULE.rule_version + "+samples+panel-PRUEBA"          # versión completa ficticia: SOLO para ejercitar la puerta (no es la del pre-registro v3)


def _plan(**kw):
    base = dict(master_seed=MASTER, k=2, library_version=LIB, rule=RULE, limit_profiles=3)
    return rp3.build_plan_v3(**{**base, **kw})


def _tree_bytes(d: Path) -> dict[str, bytes]:
    d = Path(d)
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


# ── A–D · uso de la regla v3, no de v2 ───────────────────────────────────────────────────────────────────────────
def test_A_the_module_imports_and_exposes_the_v3_api():
    assert rp3.SCHEMA_PLAN == "replicas-plan-v3" and rp3.SCHEMA_MANIFEST == "replicas-manifest-v3" and rp3.SCHEMA_REPLICA == "replica-v3"
    assert callable(rp3.build_plan_v3) and callable(rp3.run_replicas_v3) and callable(rp3.revalidate_plan) and callable(rp3.verify)


def test_B_and_C_the_plan_uses_rubric_v3_and_identifies_the_v3_statistical_rule():
    p = _plan()
    assert p["rule"]["rule_version"] == rubric_v3.RULE_VERSION and p["rule"]["gold"]["family"] == "gold-v3"
    assert p["rule"]["inclusion"]["rule_id"] == "incl-rel20" and p["rule"]["gold_fingerprint"] == RULE.gold.fingerprint()
    assert p["protocol"]["inference"]["statistical_pass_rule"] == sr3.STATISTICAL_PASS_RULE_VERSION
    assert p["protocol"]["aggregation"] == "samples" and p["protocol"]["metric_version"]


def test_D_v2_is_not_the_active_evaluation_rule():
    src = (BACKEND / "adaptation_swarm" / "analysis" / "replicas_v3.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    imported = ({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names}
                | {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names})
    assert "adaptation_swarm.gold.rubric_v3" in imported and "adaptation_swarm.analysis.statistical_rule_v3" in imported
    assert "adaptation_swarm.gold.rubric_v2" not in imported                                        # ninguna regla/aprobación de v2 en el camino de evaluación v3
    with pytest.raises(ValueError):                                                                  # una regla v2 NO es aceptada
        _plan(rule=rubric_v2.get_rule("gold-v2-cand-A", "incl-ge1"))
    altered = rubric_v3.MultilabelRuleV3(rubric_v3.GoldRuleV3(RULE.gold.rule_version, "copia", dict(RULE.gold.expected_by_archetype)), RULE.inclusion)
    with pytest.raises(ValueError):                                                                  # ni una copia alterada de la v3
        _plan(rule=altered)


# ── E–G · K, semilla maestra y derivación de semillas ────────────────────────────────────────────────────────────
def test_E_k_is_configurable_for_provisional_runs_and_fixed_at_ten_for_official_ones():
    assert _plan(k=2)["k"] == 2 and len(_plan(k=2)["batch_seeds"]) == 2 and len(_plan(k=10)["batch_seeds"]) == 10
    assert rp3.K_OFFICIAL == v2rp.K_OFFICIAL == 10
    with pytest.raises(RuleNotApproved):                                                              # la regla no está aprobada: la puerta cierra antes de mirar K
        _plan(k=3, official=True, full_rule_version=FULL, limit_profiles=None)


def test_F_the_k10_master_seed_is_the_one_of_k10_v2():
    assert rp3.K10_MASTER_SEED == 26092601
    manifest = json.loads((V2_OFFICIAL_DIR / "manifest.json").read_text(encoding="utf-8")) if V2_OFFICIAL_DIR.exists() else None
    if manifest is not None:
        assert manifest["master_seed"] == rp3.K10_MASTER_SEED


def test_G_batch_seeds_are_deterministic_and_identical_to_those_of_k10_v2():
    s = rp3.build_plan_v3(master_seed=rp3.K10_MASTER_SEED, k=10, library_version=LIB, rule=RULE, limit_profiles=3)["batch_seeds"]
    assert s == v2rp.derive_batch_seeds(rp3.K10_MASTER_SEED, 10) == _plan(master_seed=rp3.K10_MASTER_SEED, k=10)["batch_seeds"]
    assert len(set(s)) == 10 and not set(s) & v2rp.HISTORICAL_BATCH_SEEDS
    if V2_OFFICIAL_DIR.exists():                                                                      # lectura: las semillas registradas en la corrida oficial K = 10 v2
        assert s == json.loads((V2_OFFICIAL_DIR / "manifest.json").read_text(encoding="utf-8"))["batch_seeds"]


# ── H · determinismo y comparabilidad con v2 ─────────────────────────────────────────────────────────────────────
def test_H_a_small_fixture_is_deterministic_byte_for_byte(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    rp3.run_replicas_v3(_plan(), a)
    rp3.run_replicas_v3(_plan(), b)
    ta, tb = _tree_bytes(a), _tree_bytes(b)
    assert set(ta) == set(tb) == {"plan.json", "manifest.json", "replica_00.json", "replica_01.json", "execution_metadata.json"}
    for name in ta:
        if name != "execution_metadata.json":                                                         # la marca de tiempo va aparte
            assert ta[name] == tb[name], name
    assert rp3.verify(a) == [] and rp3.verify(b) == []


def test_H_the_v3_trajectory_equals_the_v2_one_for_the_same_inputs(tmp_path):
    v3_out, v2_out = tmp_path / "v3", tmp_path / "v2"
    rp3.run_replicas_v3(_plan(), v3_out)
    v2rp.run(v2rp.build_plan(master_seed=MASTER, k=2, library_version=LIB, provisional=True, limit_profiles=3), v2_out)      # v2 PROVISIONAL sin regla, en tmp_path (no toca nada oficial)
    for i in range(2):
        c3, c2 = v2rp.replica_cases(v3_out, i), v2rp.replica_cases(v2_out, i)
        assert [{k: c[k] for k in ("profile_id", "seed", "S", "F", "k_stop", "stop_reason")} for c in c3] == [{k: c[k] for k in ("profile_id", "seed", "S", "F", "k_stop", "stop_reason")} for c in c2]
        assert all(c["f1"] is not None and 0.0 <= c["f1"] <= 1.0 for c in c3)                          # F1 por caso con la regla v3


def test_the_per_case_f1_is_computed_with_the_v3_rule(tmp_path):
    out = tmp_path / "f1"
    rp3.run_replicas_v3(_plan(k=1, limit_profiles=4), out)
    from adaptation_swarm.gold.f1_multilabel import case_f1
    from adaptation_swarm.profiles.models import Archetype
    for c in v2rp.replica_cases(out, 0):
        e = [c["S"][0], c["S"][2], c["S"][4], c["S"][6]]                                              # e_code, e_diagram, e_text, e_audio
        assert c["f1"] == case_f1(RULE.expected_set(Archetype(c["archetype"])), RULE.predicted_set(e))


# ── I · separación de salidas ────────────────────────────────────────────────────────────────────────────────────
def test_I_outputs_are_new_directories_never_inside_the_frozen_v2_artifacts(tmp_path):
    for frozen in rp3._V2_FROZEN_DIRS:
        with pytest.raises(ValueError, match="K = 10 v2"):
            rp3.write_plan(_plan(), frozen / "nuevo_v3")
    rp3.run_replicas_v3(_plan(), tmp_path / "ok")
    with pytest.raises(SystemExit, match="no se sobrescriben"):                                       # nunca se reutiliza un directorio (guardia de la infraestructura de v2, reutilizada)
        rp3.run_replicas_v3(_plan(), tmp_path / "ok")
    assert rp3.V3_OUTPUT_ROOT != V2_OFFICIAL_DIR and "k10_v3" in str(rp3.V3_OUTPUT_ROOT) and not rp3.V3_OUTPUT_ROOT.exists()


def test_I_an_official_output_is_only_allowed_under_the_v3_root(tmp_path, monkeypatch):
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({rubric_v3.official_version(RULE)}))        # registro v3 en memoria, SOLO para probar el destino
    plan = _plan(master_seed=rp3.K10_MASTER_SEED, k=10, official=True, full_rule_version=FULL, limit_profiles=None)
    assert plan["status"] == "OFICIAL"
    with pytest.raises(ValueError, match="solo escribe bajo"):
        rp3.write_plan(plan, tmp_path / "fuera")
    assert not (tmp_path / "fuera").exists()


# ── J–L · identidad de dataset, biblioteca y regla ───────────────────────────────────────────────────────────────
def test_J_the_dataset_identity_is_recorded():
    p = _plan()
    assert p["dataset"]["sha256"] == hashlib.sha256(rp3.DEFAULT_PROFILES.read_bytes()).hexdigest() and p["dataset"]["n_profiles"] == len(read_dataset(rp3.DEFAULT_PROFILES)) == 100
    assert p["dataset"]["n_used"] == 3 and p["dataset"]["limited"] is True and p["dataset"]["manifest_sha256"]


def test_K_the_library_identity_is_recorded_and_never_assumed():
    p = _plan()
    assert p["library"]["version"] == LIB and p["library"]["manifest_sha256"] == hashlib.sha256((Path(SETTINGS.library_root) / LIB / "manifest.json").read_bytes()).hexdigest()
    with pytest.raises(TypeError):                                                                    # la versión de biblioteca es obligatoria: sin valor por defecto
        rp3.build_plan_v3(master_seed=MASTER, k=2, rule=RULE, limit_profiles=3)
    assert LibraryStore.open(SETTINGS.library_root, LIB).version == LIB


def test_L_the_rule_version_and_the_full_version_are_explicit():
    with pytest.raises(TypeError):                                                                    # la regla es obligatoria: sin valor por defecto
        rp3.build_plan_v3(master_seed=MASTER, k=2, library_version=LIB, limit_profiles=3)
    p = _plan()
    assert p["rule"]["rule_version"] == "gold-v3-multimodal+incl-rel20" and p["rule"]["full_rule_version"] is None and p["status"] == "PROVISIONAL"
    assert _plan(full_rule_version=FULL)["rule"]["full_rule_version"] == FULL                          # se registra tal cual; este módulo no la inventa


def test_the_plan_records_what_the_future_preregistration_needs():
    p = _plan()
    for key in ("master_seed", "batch_seeds", "k", "dataset", "library", "rule", "config", "scope", "code_version", "environment", "modules", "modules_v3", "protocol"):
        assert key in p, key
    assert set(p["config"]["pso"]) >= {"n_particles", "w", "c1", "c2", "k_max", "epsilon"} and p["code_version"]["commit"]
    assert set(p["modules_v3"]) == {"analysis/statistical_rule_v3.py", "gold/rubric_v3.py", "analysis/replicas_v3.py"}
    assert p["scope"]["experiment"] == "core_replay_k10" and "RNF-01" in p["scope"]["does_not_support"]


def test_the_execution_metadata_carries_the_timestamp_and_commit(tmp_path):
    out = tmp_path / "meta"
    m = rp3.run_replicas_v3(_plan(k=1, limit_profiles=2), out)
    meta = json.loads((out / "execution_metadata.json").read_text(encoding="utf-8"))
    assert meta["executed_at_utc"] and meta["commit"] == m["code_version"]["commit"] and meta["plan_sha256"] == m["plan_sha256"]
    assert meta["manifest_sha256"] == hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest()


# ── M · bloqueo de la ejecución oficial ──────────────────────────────────────────────────────────────────────────
def test_M_an_official_plan_is_blocked_while_the_v3_rule_is_not_approved():
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()
    with pytest.raises(RuleNotApproved):
        _plan(master_seed=rp3.K10_MASTER_SEED, k=10, official=True, full_rule_version=FULL, limit_profiles=None)


def test_M_a_forged_official_plan_is_rejected_before_any_file_is_created(tmp_path):
    forged = _plan()
    forged["status"] = "OFICIAL"
    out = tmp_path / "forjado"
    with pytest.raises((RuleNotApproved, ValueError)):
        rp3.run_replicas_v3(forged, out)
    assert not out.exists()
    plain = _plan()
    plain["master_seed"] = 1
    with pytest.raises(ValueError):
        rp3.run_replicas_v3(plain, tmp_path / "manipulado")
    assert not (tmp_path / "manipulado").exists()


def test_the_official_gate_requires_every_condition_once_the_rule_is_approved(monkeypatch):
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({rubric_v3.official_version(RULE)}))        # registro v3 en memoria, SOLO para ejercitar las demás condiciones
    ok = dict(master_seed=rp3.K10_MASTER_SEED, k=10, official=True, full_rule_version=FULL, limit_profiles=None)
    assert _plan(**ok)["status"] == "OFICIAL"
    with pytest.raises(NoRuleSelected):
        _plan(**{**ok, "full_rule_version": None})                                                     # la versión completa no se infiere
    with pytest.raises(ValueError, match="no corresponde"):
        _plan(**{**ok, "full_rule_version": "otra-regla+samples"})
    with pytest.raises(ValueError, match="K = 10"):
        _plan(**{**ok, "k": 9})
    with pytest.raises(ValueError, match="seed fishing"):
        _plan(**{**ok, "master_seed": 12345})
    with pytest.raises(ValueError, match="100 perfiles"):
        _plan(**{**ok, "limit_profiles": 10})


# ── N · O · P · no modificación de registros ni artefactos históricos ────────────────────────────────────────────
def test_N_and_O_the_approval_registries_are_untouched_after_planning_and_running(tmp_path):
    rp3.run_replicas_v3(_plan(), tmp_path / "r")
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({V2_OFFICIAL_VERSION})
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()


def test_P_the_historical_k10_v2_artifacts_and_fingerprints_are_untouched(tmp_path):
    if V2_OFFICIAL_DIR.exists():
        before = _tree_bytes(V2_OFFICIAL_DIR)
        rp3.run_replicas_v3(_plan(), tmp_path / "p")
        assert _tree_bytes(V2_OFFICIAL_DIR) == before and v2rp.verify(V2_OFFICIAL_DIR) == []
    fp = v2rp.module_fingerprints()
    assert len(fp) == 19 and not any("v3" in k for k in fp)                                            # las huellas de v2 no incorporan archivos v3
    assert hashlib.sha256((BACKEND / "adaptation_swarm" / "analysis" / "inference.py").read_bytes()).hexdigest() == "d8bb538fd242eb0ab6ab206aaf02391c48d0937569cd1034d82d5963a6202d83"


def test_the_v3_layer_fingerprints_are_separate_and_cover_the_three_v3_modules():
    f = rp3.module_fingerprints_v3()
    assert set(f) == {"analysis/statistical_rule_v3.py", "gold/rubric_v3.py", "analysis/replicas_v3.py"} and all(len(h) == 64 for h in f.values())


def test_an_official_execution_is_refused_on_non_target_hardware_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({rubric_v3.official_version(RULE)}))        # registro en memoria, SOLO para llegar a la puerta de hardware
    monkeypatch.setattr(rp3, "hardware_profile", lambda: {"vcpu": 8, "ram_gib": 7.5})
    plan = _plan(master_seed=rp3.K10_MASTER_SEED, k=10, official=True, full_rule_version=FULL, limit_profiles=None)
    out = tmp_path / "k10_v3_no"
    with pytest.raises(rp3.HardwareNotTarget):
        rp3.run_replicas_v3(plan, out)
    assert not out.exists()
