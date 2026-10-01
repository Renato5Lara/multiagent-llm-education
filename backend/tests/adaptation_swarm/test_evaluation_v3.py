"""`analysis/evaluation_v3.py` — evaluación de K = 10 v3 (capa aditiva; K = 10 v2 no se toca). Pruebas PURAS y deterministas: fixtures pequeños CALCULADOS A MANO y una corrida provisional mínima de `replicas_v3`
(K ≤ 2, 4 perfiles, semilla maestra de PRUEBA, escrita solo en `tmp_path`). NO ejecutan K = 10 v3 ni generan resultados oficiales.

Fixtures (P1: e_m ≥ 1 ∧ 5·e_m ≥ Σe; P2: matriz por arquetipo):
  1 visual_dominant          e = (code 1, diagram 2, text 0, audio 0)  Σ=3 → pred {code, diagram}         gold {diagram, code}             F1 = 1
  2 logical_syntactic        e = (2, 0, 0, 1)                          Σ=3 → pred {code, audio}           gold {code, diagram}             F1 = 2·1/(2+2) = 1/2
  3 explanatory_conceptual   e = (0, 0, 2, 0)                          Σ=2 → pred {text}                  gold {text, diagram, code}       F1 = 2·1/(3+1) = 1/2
  4 balanced_multimodal      e = (2, 2, 2, 1)                          Σ=7 → pred {code, diagram, text}   gold {las cuatro}                F1 = 2·3/(4+3) = 6/7     (audio 1/7 < 0.20)
  F1_adapt (samples) = (1 + 1/2 + 1/2 + 6/7) / 4 = 5/7
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from adaptation_swarm.analysis import evaluation_v3 as ev3
from adaptation_swarm.analysis import inference as inf
from adaptation_swarm.analysis import replicas as v2rp
from adaptation_swarm.analysis import replicas_v3 as rp3
from adaptation_swarm.analysis import statistical_rule_v3 as sr3
from adaptation_swarm.gold import f1_multilabel as f1m
from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.gold.rubric_v2 import RuleNotApproved
from adaptation_swarm.pso.space import MODALITIES

BACKEND = Path(__file__).resolve().parents[2]
LIB = "lib-v5-9ae9ffdd"
MASTER = 424242
V2_OFFICIAL_VERSION = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
V2_OFFICIAL_DIR = BACKEND / "official_runs" / "k10_official_2026-09-27"
RULE = rubric_v3.get_rule(rubric_v3.GOLD_RULE_VERSION, rubric_v3.INCLUSION_RULE_ID)
SRC = (BACKEND / "adaptation_swarm" / "analysis" / "evaluation_v3.py").read_text(encoding="utf-8")


def _S(code, diagram, text, audio):
    return [code, 0, diagram, 0, text, 0, audio, 0]                    # (e_code, v_code, e_diagram, v_diagram, e_text, v_text, e_audio, v_audio)


def _case(pid, arch, diff, e, *, seed=1, concept="c1", **extra):
    return {"profile_id": pid, "archetype": arch, "difficulty": diff, "concept_id": concept, "seed": seed, "S": _S(*e), "F": 0.5, "k_stop": 1, "stop_reason": "epsilon", **extra}


def _replica0(**kw):
    return [_case("p1", "visual_dominant", "sequential", (1, 2, 0, 0), seed=11, concept="cA", **kw), _case("p2", "logical_syntactic", "conditional", (2, 0, 0, 1), seed=12, concept="cB", **kw),
            _case("p3", "explanatory_conceptual", "repetitive", (0, 0, 2, 0), seed=13, concept="cC", **kw), _case("p4", "balanced_multimodal", "functions", (2, 2, 2, 1), seed=14, concept="cD", **kw)]


def _replica1():
    cases = _replica0()
    cases[0] = _case("p1", "visual_dominant", "sequential", (0, 0, 0, 0), seed=21, concept="cA")       # Σe = 0 ⇒ conjunto vacío ⇒ F1 = 0
    for c, s in zip(cases[1:], (22, 23, 24)):
        c["seed"] = s
    return cases


def _reps(*cases_lists, seeds=(101, 202)):
    return [{"replica_index": i, "batch_seed": seeds[i], "cases": c} for i, c in enumerate(cases_lists)]


def _ev(*cases_lists, **kw):
    return ev3.evaluate_v3(_reps(*cases_lists), rule=RULE, **kw)


_TREE = ast.parse(SRC)
_CODE_NAMES = {n.id for n in ast.walk(_TREE) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(_TREE) if isinstance(n, ast.Attribute)}      # solo CÓDIGO (sin docstrings)
_CODE_NUMBERS = {n.value for n in ast.walk(_TREE) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}


def _keys(obj) -> set:
    if isinstance(obj, dict):
        return set(obj) | {k for v in obj.values() for k in _keys(v)}
    if isinstance(obj, (list, tuple)):
        return {k for v in obj for k in _keys(v)}
    return set()


def _tree(d: Path) -> dict[str, bytes]:
    d = Path(d)
    return {str(p.relative_to(d)): p.read_bytes() for p in sorted(d.rglob("*")) if p.is_file()}


# ── A · F1 por caso y P3 ─────────────────────────────────────────────────────────────────────────────────────────
def test_A_the_per_case_multilabel_f1_is_computed_by_hand():
    recs = _ev(_replica0())["cases"]
    assert [r["f1"] for r in recs] == [1.0, 0.5, 0.5, pytest.approx(6 / 7)]
    assert [r["predicted_set"] for r in recs] == [["code", "diagram"], ["code", "audio"], ["text"], ["code", "diagram", "text"]]


def test_P3_f1_adapt_is_the_mean_of_the_per_case_f1_with_the_samples_aggregation():
    e = _ev(_replica0())
    assert e["aggregation"] == "samples" == f1m.OFFICIAL_AGGREGATION
    assert e["f1_adapt_by_replica"] == [pytest.approx(5 / 7)]
    assert e["per_replica"][0]["f1_adapt"] == pytest.approx(sum(r["f1"] for r in e["cases"]) / 4)
    direct = f1m.multilabel_report(f1m.cases_from_records(_replica0(), RULE), RULE).f1("samples")             # la métrica de v2, sin cambios
    assert e["f1_adapt_by_replica"][0] == pytest.approx(direct) and e["metric_version"] == f1m.METRIC_VERSION


def test_P3_audio_is_kept_and_the_f1_is_not_replaced_by_accuracy():
    e = _ev(_replica0())
    assert "audio" in e["ovr_2x2_pooled"]["modalities"] and set(e["per_replica"][0]["ovr_2x2"]) == set(MODALITIES)
    assert e["f1_adapt_by_replica"][0] != pytest.approx(sum(1 for r in e["cases"] if r["expected_set"] == r["predicted_set"]) / 4)     # exact-match (0.25) ≠ F1 por caso


# ── B–D · gold desde rubric_v3 ───────────────────────────────────────────────────────────────────────────────────
def test_B_the_expected_set_of_each_archetype_comes_from_the_v3_matrix():
    by_arch = {r["archetype"]: r["expected_set"] for r in _ev(_replica0())["cases"]}
    assert by_arch == {"visual_dominant": ["code", "diagram"], "logical_syntactic": ["code", "diagram"], "explanatory_conceptual": ["code", "diagram", "text"],
                       "balanced_multimodal": ["code", "diagram", "text", "audio"]}


def test_C_audio_is_in_the_balanced_gold_and_D_absent_from_the_other_three():
    by_arch = {r["archetype"]: r["expected_set"] for r in _ev(_replica0())["cases"]}
    assert "audio" in by_arch["balanced_multimodal"] and len(by_arch["balanced_multimodal"]) == 4
    assert all("audio" not in by_arch[a] for a in ("visual_dominant", "logical_syntactic", "explanatory_conceptual"))


# ── E · inclusión P1 tomada de rubric_v3, no duplicada ───────────────────────────────────────────────────────────
def test_E_the_inclusion_is_consumed_from_rubric_v3_and_not_duplicated(monkeypatch):
    base = {r["profile_id"]: r["predicted_set"] for r in _ev(_replica0())["cases"]}
    assert base["p4"] == ["code", "diagram", "text"]
    monkeypatch.setattr(rubric_v3.RelativeInclusionRule, "predicted_set", lambda self, emphasis: frozenset(MODALITIES))        # cambiar P1 en rubric_v3 cambia la evaluación
    assert all(r["predicted_set"] == list(MODALITIES) for r in _ev(_replica0())["cases"])
    assert not {"share_den", "share_num", "min_emphasis", "RelativeInclusionRule"} & _CODE_NAMES and 0.2 not in _CODE_NUMBERS and 0.20 not in _CODE_NUMBERS


# ── F · G · independencia de W y de la dificultad ────────────────────────────────────────────────────────────────
def test_F_the_evaluation_does_not_depend_on_W():
    assert ev3.content_hash(_ev(_replica0())) == ev3.content_hash(_ev(_replica0(W=[0.1, 0.2, 0.3, 0.4])))              # un campo W cualquiera no interviene
    assert ev3.content_hash(_ev(_replica0(W=[0.4, 0.3, 0.2, 0.1]))) == ev3.content_hash(_ev(_replica0(W=[0.1, 0.2, 0.3, 0.4])))
    assert "w_mapping" not in SRC and "compute_weights" not in SRC and "heuristic_start" not in SRC


def test_G_the_evaluation_does_not_depend_on_the_difficulty():
    changed = _replica0()
    for c, d in zip(changed, ("functions", "arrays_vectors", "sequential", "repetitive")):
        c["difficulty"] = d
    a, b = _ev(_replica0())["cases"], _ev(changed)["cases"]
    assert [(r["f1"], r["expected_set"], r["predicted_set"]) for r in a] == [(r["f1"], r["expected_set"], r["predicted_set"]) for r in b]
    assert [r["difficulty"] for r in b] == ["functions", "arrays_vectors", "sequential", "repetitive"]                # la dificultad se CONSERVA, sin intervenir


# ── H · I · J · cuatro matrices OVR ──────────────────────────────────────────────────────────────────────────────
def test_H_there_are_four_ovr_matrices_with_counts_precision_recall_and_f1():
    ovr = _ev(_replica0())["per_replica"][0]["ovr_2x2"]
    assert list(ovr) == ["code", "diagram", "text", "audio"]
    for m in MODALITIES:
        assert set(ovr[m]) >= {"matrix", "tp", "fp", "fn", "tn", "precision", "recall", "f1"}
        assert ovr[m]["matrix"] == [[ovr[m]["tp"], ovr[m]["fn"]], [ovr[m]["fp"], ovr[m]["tn"]]] and ovr[m]["tp"] + ovr[m]["fp"] + ovr[m]["fn"] + ovr[m]["tn"] == 4


def test_I_the_audio_ovr_matrix_is_correct():
    a = _ev(_replica0())["per_replica"][0]["ovr_2x2"]["audio"]
    assert (a["tp"], a["fp"], a["fn"], a["tn"]) == (0, 1, 1, 2)                   # fp: caso 2 (audio predicho fuera del gold); fn: caso 4 (audio del gold excluido por 1/7 < 0.20)
    assert a["precision"] == 0.0 and a["recall"] == 0.0 and a["f1"] == 0.0


def test_J_tp_fp_fn_tn_are_correct_for_the_four_modalities():
    ovr = _ev(_replica0())["per_replica"][0]["ovr_2x2"]
    assert {m: (ovr[m]["tp"], ovr[m]["fp"], ovr[m]["fn"], ovr[m]["tn"]) for m in MODALITIES} == {"code": (3, 0, 1, 0), "diagram": (2, 0, 2, 0), "text": (2, 0, 0, 2), "audio": (0, 1, 1, 2)}
    assert ovr["code"]["precision"] == 1.0 and ovr["code"]["recall"] == 0.75 and ovr["code"]["f1"] == pytest.approx(6 / 7)


def test_pooled_ovr_adds_the_replicas_and_is_descriptive():
    e = _ev(_replica0(), _replica1())
    pooled = e["ovr_2x2_pooled"]["by_modality"]
    for m in MODALITIES:
        assert pooled[m]["tp"] + pooled[m]["fp"] + pooled[m]["fn"] + pooled[m]["tn"] == 8
        assert pooled[m]["tp"] == sum(r["ovr_2x2"][m]["tp"] for r in e["per_replica"])
    assert e["ovr_2x2_pooled"]["n_cases"] == 8 and e["per_replica"][1]["n_empty_predicted"] == 1


# ── K–O · preservación de la granularidad por caso ───────────────────────────────────────────────────────────────
def test_K_to_O_every_case_keeps_profile_replica_seeds_archetype_difficulty_and_concept():
    recs = _ev(_replica0(), _replica1())["cases"]
    assert len(recs) == 8
    assert [r["profile_id"] for r in recs] == ["p1", "p2", "p3", "p4"] * 2                                                                 # K
    assert [(r["replica_index"], r["batch_seed"]) for r in recs] == [(0, 101)] * 4 + [(1, 202)] * 4                                        # L
    assert [r["case_seed"] for r in recs] == [11, 12, 13, 14, 21, 22, 23, 24]
    assert [r["archetype"] for r in recs[:4]] == ["visual_dominant", "logical_syntactic", "explanatory_conceptual", "balanced_multimodal"]   # M
    assert [r["difficulty"] for r in recs[:4]] == ["sequential", "conditional", "repetitive", "functions"]                                # N
    assert [r["concept_id"] for r in recs[:4]] == ["cA", "cB", "cC", "cD"]                                                                # O
    assert recs[3]["S"] == _S(2, 2, 2, 1) and recs[3]["emphasis"] == {"code": 2, "diagram": 2, "text": 2, "audio": 1} and recs[4]["predicted_set"] == []


def test_the_profile_means_and_replica_f1_are_the_observations_for_the_inference():
    e = _ev(_replica0(), _replica1())
    assert e["profile_means"] == {"p1": 0.5, "p2": 0.5, "p3": 0.5, "p4": pytest.approx(6 / 7)}                                            # media de sus F1 en las 2 réplicas
    assert e["f1_adapt_by_replica"] == [pytest.approx(5 / 7), pytest.approx((0 + 0.5 + 0.5 + 6 / 7) / 4)]
    obs = ev3.inference_inputs(e)
    assert obs["profile_means"] == [0.5, 0.5, 0.5, pytest.approx(6 / 7)] and obs["f1_adapt_by_replica"] == e["f1_adapt_by_replica"]


# ── P · determinismo ─────────────────────────────────────────────────────────────────────────────────────────────
def test_P_the_same_input_gives_exactly_the_same_evaluation():
    a, b = _ev(_replica0(), _replica1()), _ev(_replica0(), _replica1())
    assert ev3.canonical_bytes(a) == ev3.canonical_bytes(b) and ev3.content_hash(a) == ev3.content_hash(b)
    assert "executed_at" not in json.dumps(a) and "timestamp" not in json.dumps(a)


# ── Q · integración con statistical_rule_v3 ──────────────────────────────────────────────────────────────────────
def test_Q_the_observations_feed_the_v3_statistical_rule_without_running_the_official_inference():
    e = _ev(_replica0(), _replica1())
    obs = ev3.inference_inputs(e)
    t = sr3.profile_level_test_v3(obs["profile_means"] + [0.9, 0.95, 0.4])                                        # ≥ 3 valores y no constantes
    assert t["statistical_rule_version"] == sr3.STATISTICAL_PASS_RULE_VERSION and t["statistical_pass"] in (True, False)
    ci = inf.student_t_ci(obs["f1_adapt_by_replica"])
    assert ci["k"] == 2 and e["descriptive"]["ci95_replicas"]["mean"] == pytest.approx(ci["mean"])
    assert ev3.evaluate_v3(_reps(_replica0()), rule=RULE)["descriptive"]["ci95_replicas"] is None                   # con K = 1 no hay IC
    assert not {"RNF03", "rnf03", "H1", "h1", "criterion", "combined_pass", "statistical_pass", "verdict", "ci_pass", "benchmark"} & _keys(e)            # esta fase no declara nada


def test_the_evaluation_code_does_not_run_the_inference_nor_compare_with_the_benchmark():
    assert not {"profile_level_test", "profile_level_test_v3", "combined_criterion", "BENCHMARK_F1", "ALPHA"} & _CODE_NAMES
    assert 0.85 not in _CODE_NUMBERS and "student_t_ci" in _CODE_NAMES and "aggregate_by_profile" in _CODE_NAMES        # solo utilidades descriptivas de v2


# ── R · S · puerta provisional / oficial ─────────────────────────────────────────────────────────────────────────
def test_R_a_provisional_evaluation_of_a_fixture_is_allowed():
    e = _ev(_replica0())
    assert e["status"] == "PROVISIONAL" and e["rule_version"] == "gold-v3-multimodal+incl-rel20" and e["official_version"] == rubric_v3.official_version(RULE)
    assert e["schema"] == "evaluation-v3" and e["statistical_rule_version"] == sr3.STATISTICAL_PASS_RULE_VERSION and e["source"] is None


def test_S_an_official_evaluation_is_blocked_while_the_v3_registry_is_empty():
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()
    with pytest.raises(RuleNotApproved):
        _ev(_replica0(), official=True)
    assert rubric_v3.APPROVED_RULE_VERSIONS == frozenset()                                                        # nada se rellena solo


def test_S_the_official_gate_also_requires_k10_and_the_hundred_profiles_once_approved(monkeypatch):
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({rubric_v3.official_version(RULE)}))        # registro v3 en memoria, SOLO para ejercitar las demás condiciones
    with pytest.raises(ValueError, match="K = 10"):
        _ev(_replica0(), _replica1(), official=True)


def test_a_v2_rule_or_an_altered_v3_copy_is_rejected():
    with pytest.raises(ValueError):
        ev3.evaluate_v3(_reps(_replica0()), rule=rubric_v2.get_rule("gold-v2-cand-A", "incl-ge1"))
    altered = rubric_v3.MultilabelRuleV3(rubric_v3.GoldRuleV3(RULE.gold.rule_version, "copia", dict(RULE.gold.expected_by_archetype)), RULE.inclusion)
    with pytest.raises(ValueError):
        ev3.evaluate_v3(_reps(_replica0()), rule=altered)
    with pytest.raises(ValueError):
        ev3.evaluate_v3([], rule=RULE)


def test_a_stored_f1_that_disagrees_with_the_recomputed_one_is_rejected():
    cases = _replica0()
    cases[0]["f1"] = 0.123
    with pytest.raises(ValueError, match="no coincide"):
        _ev(cases)


# ── integración con un directorio de replicas_v3 ─────────────────────────────────────────────────────────────────
def _small_run(tmp_path, name="run"):
    plan = rp3.build_plan_v3(master_seed=MASTER, k=2, library_version=LIB, rule=RULE, limit_profiles=4)
    out = tmp_path / name
    rp3.run_replicas_v3(plan, out)
    return out


def test_the_evaluation_consumes_a_replicas_v3_directory(tmp_path):
    out = _small_run(tmp_path)
    before = _tree(out)
    e = ev3.evaluate_dir_v3(out)
    assert _tree(out) == before                                                                                   # solo lee
    assert e["k"] == 2 and e["n_profiles"] == 4 and e["n_cases_total"] == 8 and e["status"] == "PROVISIONAL"
    assert e["source"]["full_rule_version"] is None and e["source"]["manifest_status"] == "PROVISIONAL" and set(e["source"]["modules_v3"]) == set(rp3.module_fingerprints_v3())
    for rep, stored in zip(e["per_replica"], range(2)):
        cases = json.loads((out / f"replica_{stored:02d}.json").read_text(encoding="utf-8"))["cases"]
        assert rep["f1_adapt"] == pytest.approx(sum(c["f1"] for c in cases) / len(cases))                          # coincide con el F1 por caso guardado por replicas_v3
    t = sr3.profile_level_test_v3(ev3.inference_inputs(e)["profile_means"])                                        # integración real: las 4 medias por perfil alimentan la regla v3
    assert t["n"] == 4 and t["statistical_pass"] in (True, False, None)


def test_the_directory_evaluation_is_deterministic(tmp_path):
    a, b = ev3.evaluate_dir_v3(_small_run(tmp_path, "a")), ev3.evaluate_dir_v3(_small_run(tmp_path, "b"))
    assert ev3.canonical_bytes(a) == ev3.canonical_bytes(b)


def test_S_the_official_directory_evaluation_is_blocked(tmp_path, monkeypatch):
    out = _small_run(tmp_path)
    with pytest.raises(RuleNotApproved):
        ev3.evaluate_dir_v3(out, official=True)
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({rubric_v3.official_version(RULE)}))        # aun aprobada, un manifiesto PROVISIONAL no sirve para una evaluación oficial
    with pytest.raises(ValueError, match="OFICIAL"):
        ev3.evaluate_dir_v3(out, official=True)


def test_a_tampered_replicas_directory_is_rejected(tmp_path):
    out = _small_run(tmp_path)
    (out / "replica_00.json").write_bytes((out / "replica_00.json").read_bytes() + b" ")
    with pytest.raises(ValueError, match="no íntegro"):
        ev3.evaluate_dir_v3(out)


# ── T · U · no regresión de v2 ───────────────────────────────────────────────────────────────────────────────────
def test_T_rubric_v2_is_not_used_and_its_registry_is_untouched():
    tree = ast.parse(SRC)
    imported = ({n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)} | {f"{n.module}.{a.name}" for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names})
    assert "adaptation_swarm.gold.rubric_v3" in imported and "adaptation_swarm.gold.rubric_v2" not in imported
    _ev(_replica0())
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({V2_OFFICIAL_VERSION})
    assert hashlib.sha256((BACKEND / "adaptation_swarm" / "gold" / "rubric_v2.py").read_bytes()).hexdigest() == "cdf55ce0b08712df162423873686e8821d3daa019926ae666bbcd1e15b29b262"


def test_U_the_historical_k10_v2_artifacts_and_fingerprints_are_untouched(tmp_path):
    if V2_OFFICIAL_DIR.exists():
        before = _tree(V2_OFFICIAL_DIR)
        ev3.evaluate_dir_v3(_small_run(tmp_path))
        assert _tree(V2_OFFICIAL_DIR) == before and v2rp.verify(V2_OFFICIAL_DIR) == []
    fp = v2rp.module_fingerprints()
    assert len(fp) == 19 and not any("v3" in k for k in fp)
    assert hashlib.sha256((BACKEND / "adaptation_swarm" / "analysis" / "inference.py").read_bytes()).hexdigest() == "d8bb538fd242eb0ab6ab206aaf02391c48d0937569cd1034d82d5963a6202d83"
    assert set(ev3._EVALUATION_MODULES) == {"analysis/evaluation_v3.py", "gold/rubric_v3.py", "analysis/statistical_rule_v3.py", "gold/f1_multilabel.py", "analysis/inference.py"}
