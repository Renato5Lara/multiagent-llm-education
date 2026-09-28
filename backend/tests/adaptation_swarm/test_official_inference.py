"""R1–R4, R6 y P1–P3 (respuestas del asesor, 2026-09-26): IC t de Student entre K = 10 réplicas, agregación 10 → 1 por perfil, Shapiro-Wilk sobre los 100 promedios, t/Wilcoxon, criterio conjunto (AND), gold por
arquetipo, inclusión e_m ≥ 1, conjunto vacío ⇒ F1 = 0, e = [0,0,0,0] ⇒ F1 = 0 y separación core / full-stack. Los vectores numéricos son de VERIFICACIÓN de fórmulas: no son resultados de ninguna corrida.
La única ejecución de réplicas de este archivo escribe solo en `tmp_path`, con una semilla maestra de PRUEBA y la aprobación en memoria (mismo patrón que `test_replicas_executor`): NO es la corrida oficial."""

import ast
import math
from pathlib import Path

import numpy as np
import pytest
from scipy import stats

from adaptation_swarm.analysis import inference as inf
from adaptation_swarm.analysis import replica_evaluation as ev
from adaptation_swarm.analysis import replicas as rp
from adaptation_swarm.gold import f1_multilabel as f1m
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.rubric_v2 import GOLD_RULES, INCLUSION_RULES, RuleNotApproved, get_rule, official_version
from adaptation_swarm.profiles.models import Archetype
from adaptation_swarm.pso.space import MODALITIES, Configuration

LIB = "lib-v5-9ae9ffdd"
MASTER = 424242                                        # semilla maestra de PRUEBA
RULE = ("gold-v2-cand-A", "incl-ge1")
UNAPPROVED_RULE = ("gold-v2-cand-A", "incl-ge2")     # gold-v2 REGISTRADA pero ausente de APPROVED_RULE_VERSIONS: ejemplo de «regla no aprobada» para los guards (RULE ya está registrada técnicamente)


# ── A · R1: IC95 t de Student, gl = K − 1 ─────────────────────────────────────────────────────────────────────────
def test_A_student_t_ci_matches_the_formula_and_records_every_component():
    v = [0.80, 0.82, 0.85, 0.87, 0.83, 0.86, 0.84, 0.88, 0.81, 0.85]                     # vector de verificación
    ci = inf.student_t_ci(v)
    mean, sd = float(np.mean(v)), float(np.std(v, ddof=1))
    t_crit = float(stats.t.ppf(0.975, 9))
    assert ci["method"] == "student_t_one_sample" and ci["k"] == 10 and ci["df"] == 9
    assert ci["mean"] == pytest.approx(mean) and ci["sd"] == pytest.approx(sd) and ci["se"] == pytest.approx(sd / math.sqrt(10))
    assert ci["t_critical"] == pytest.approx(t_crit) and t_crit == pytest.approx(2.262157, abs=1e-6)
    assert ci["lower"] == pytest.approx(mean - t_crit * sd / math.sqrt(10)) and ci["upper"] == pytest.approx(mean + t_crit * sd / math.sqrt(10))
    assert ci["lower"] < mean < ci["upper"] and ci["confidence"] == 0.95
    with pytest.raises(ValueError):
        inf.student_t_ci([0.9])


def test_A_the_ci_is_not_a_bootstrap():
    tree = ast.parse(Path(inf.__file__).read_text(encoding="utf-8"))
    code = "\n".join(ast.unparse(n) for n in tree.body[1:])                                            # todo salvo la docstring (que menciona que NO se usa bootstrap)
    assert "bootstrap" not in code.lower() and "rng" not in code.lower()


# ── B · C · D · E · R2: agregación 10 → 1 por perfil ────────────────────────────────────────────────────────────────
def _replica_f1(n_profiles=100, k=10, seed=7):
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.6, 1.0, n_profiles)
    return [{f"p{i:03d}": float(np.clip(base[i] + rng.normal(0, 0.05), 0, 1)) for i in range(n_profiles)} for _ in range(k)]


def test_B_ten_replicas_collapse_to_one_mean_per_profile():
    reps = _replica_f1()
    agg = inf.aggregate_by_profile(reps)
    assert set(agg) == set(reps[0]) and all(len(a["f1_by_replica"]) == 10 for a in agg.values())
    assert agg["p007"]["mean"] == pytest.approx(np.mean([r["p007"] for r in reps]))
    assert agg["p007"]["f1_by_replica"] == [r["p007"] for r in reps]                          # profile_id -> [10 F1] -> mean


def test_B_replicas_must_carry_the_same_profiles():
    reps = _replica_f1(5, 3)
    del reps[1]["p002"]
    with pytest.raises(ValueError, match="mismos perfiles"):
        inf.aggregate_by_profile(reps)


def test_C_exactly_one_hundred_statistical_units_not_a_thousand():
    reps = _replica_f1()
    agg = inf.aggregate_by_profile(reps)
    means = [agg[p]["mean"] for p in sorted(agg)]
    assert len(means) == 100 and sum(len(a["f1_by_replica"]) for a in agg.values()) == 1000
    assert inf.profile_level_test(means)["n"] == 100                                           # la prueba recibe los 100 promedios, no las 1000 observaciones


def test_D_shapiro_is_applied_to_the_hundred_profile_means():
    means = [v["mean"] for v in inf.aggregate_by_profile(_replica_f1()).values()]
    t = inf.profile_level_test(means)
    assert t["n"] == 100 and t["shapiro_p"] == pytest.approx(float(stats.shapiro(np.array(means)).pvalue)) and t["alpha"] == 0.05


def test_E_normal_data_use_the_t_test_and_non_normal_data_use_wilcoxon():
    rng = np.random.default_rng(1)
    normal = list(rng.normal(0.9, 0.03, 100))
    t = inf.profile_level_test(normal)
    assert t["normal"] is True and t["test"] == "student_t_one_sample"
    assert t["p_value"] == pytest.approx(float(stats.ttest_1samp(normal, 0.85, alternative="greater").pvalue))
    skew = list(rng.exponential(0.1, 100) + 0.7)
    w = inf.profile_level_test(skew)
    assert w["normal"] is False and w["test"] == "wilcoxon_signed_rank"
    assert w["p_value"] == pytest.approx(float(stats.wilcoxon(np.array(skew) - 0.85, alternative="greater").pvalue))
    assert inf.profile_level_test([0.9] * 100)["statistical_pass"] is None                      # muestra constante: prueba indefinida, nunca PASS


# ── F · R3: criterio conjunto, AND ───────────────────────────────────────────────────────────────────────────────
def _ci(lower):
    return {"lower": lower}


def _test(passed):
    return {"test": "student_t_one_sample", "p_value": 0.01 if passed else 0.5, "statistical_pass": passed}


@pytest.mark.parametrize("ci_pass, stat_pass, expected", [(True, True, True), (False, True, False), (True, False, False), (False, False, False)])
def test_F_combined_criterion_is_an_AND(ci_pass, stat_pass, expected):
    c = inf.combined_criterion(_ci(0.86 if ci_pass else 0.84), _test(stat_pass))
    assert c["ci_pass"] is ci_pass and c["statistical_pass"] is stat_pass and c["combined_pass"] is expected
    assert c["verdict"] == ("PASS" if expected else "FAIL") and c["rule"] == "AND"


def test_F_the_criterion_is_not_inferred_from_the_mean():
    c = inf.combined_criterion({"lower": 0.80, "mean": 0.9}, _test(True))                        # media alta pero límite inferior < 0.85
    assert c["combined_pass"] is False and inf.combined_criterion(_ci(0.85), _test(True))["ci_pass"] is True      # ≥ 0.85 incluye el borde
    assert inf.combined_criterion(_ci(0.9), _test(None))["combined_pass"] is None and inf.combined_criterion(_ci(0.9), _test(None))["verdict"] == "INDETERMINADO"


# ── G · H · I · J · K · R6: gold, inclusión y F1 ───────────────────────────────────────────────────────────────────
def test_G_expected_sets_depend_only_on_the_archetype_and_match_the_approved_table():
    g = GOLD_RULES["gold-v2-cand-A"]
    assert {a.value: sorted(g.expected_by_archetype[a]) for a in Archetype} == {
        "visual_dominant": ["diagram"], "logical_syntactic": ["code"], "explanatory_conceptual": ["text"], "balanced_multimodal": ["audio", "code", "diagram", "text"]}
    assert not g.cell_overrides                                                                     # sin dependencia de la dificultad
    from adaptation_swarm.profiles.models import Difficulty
    for a in Archetype:
        assert len({g.expected_set(a, d) for d in Difficulty}) == 1                                 # la dificultad no cambia el gold
    assert g.expected_by_archetype is rubric_v2._A                                                  # tabla fija por arquetipo: no se deriva de centroides ni de W


def test_H_audio_is_expected_only_for_balanced():
    g = GOLD_RULES["gold-v2-cand-A"]
    assert [a.value for a in Archetype if "audio" in g.expected_by_archetype[a]] == ["balanced_multimodal"]


def test_I_inclusion_is_e_ge_1_and_role_zero_is_exclusion():
    rule = INCLUSION_RULES["incl-ge1"]
    assert (rule.kind, rule.parameter) == ("threshold", 1)
    assert rule.predicted_set((0, 1, 2, 0)) == frozenset({"diagram", "text"})                       # 0 = apoyo/exclusión · 1 = estándar · 2 = principal
    assert rule.predicted_set((2, 2, 2, 2)) == frozenset(MODALITIES) and rule.predicted_set((1, 0, 0, 1)) == frozenset({"code", "audio"})


def test_J_an_empty_predicted_set_scores_zero_and_the_case_is_not_excluded():
    rule = get_rule(*RULE)
    rec = [{"profile_id": "a", "archetype": "visual_dominant", "difficulty": "repetitive", "S": [0, 0, 0, 0, 0, 0, 0, 0]},
           {"profile_id": "b", "archetype": "visual_dominant", "difficulty": "repetitive", "S": [0, 0, 2, 0, 0, 0, 0, 0]}]
    rep = f1m.multilabel_report(f1m.cases_from_records(rec, rule), rule)
    assert rep.n_cases == 2 and rep.n_empty_predicted == 1
    assert [d["f1"] for d in rep.per_case] == [0.0, 1.0] and rep.samples["f1"] == 0.5             # entra en la media con 0
    assert f1m.case_f1(frozenset({"diagram"}), frozenset()) == 0.0


def test_K_r6_all_zero_emphasis_is_a_valid_search_point_and_scores_zero():
    cfg = Configuration((0,) * 8)                                                                   # el espacio de búsqueda NO se restringe: e = [0,0,0,0] es una configuración válida
    assert cfg.emphasis == (0, 0, 0, 0)
    rule = get_rule(*RULE)
    for arch in Archetype:
        rec = [{"profile_id": "z", "archetype": arch.value, "difficulty": "repetitive", "S": list(cfg.vector)}]
        c = f1m.cases_from_records(rec, rule)[0]
        assert c.predicted == frozenset() and f1m.case_f1(c.gold, c.predicted) == 0.0
    src = (Path(rubric_v2.__file__).parent.parent / "pso" / "engine.py").read_text(encoding="utf-8")
    assert "emphasis" not in src and "feasib" not in src.lower()                                   # el motor PSO no introduce ninguna restricción de factibilidad sobre los énfasis


def test_official_f1_is_the_samples_mean_and_needs_an_official_report(monkeypatch):
    rule = get_rule(*UNAPPROVED_RULE)
    rec = [{"profile_id": "a", "archetype": "balanced_multimodal", "difficulty": "repetitive", "S": [0, 1, 0, 1, 2, 1, 2, 1]}]   # e = (0,0,2,2): P = {text, audio}, G = 4
    cases = f1m.cases_from_records(rec, rule)
    with pytest.raises(RuleNotApproved):
        f1m.official_report(cases, rule)
    prov = f1m.multilabel_report(cases, rule)
    with pytest.raises(RuleNotApproved):
        f1m.official_f1_adapt(prov)
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))
    rep = f1m.official_report(cases, rule)
    assert rep.status == "OFICIAL" and f1m.official_f1_adapt(rep) == pytest.approx(2 * 2 / (4 + 2)) and f1m.OFFICIAL_AGGREGATION == "samples"
    monkeypatch.undo()
    registered = get_rule(*RULE)                                                                     # la regla registrada técnicamente no necesita parche para dar un informe OFICIAL
    assert f1m.official_report(f1m.cases_from_records(rec, registered), registered).status == "OFICIAL"


def test_ovr_2x2_matrices_are_four_independent_matrices_and_the_4x4_does_not_enter_any_aggregation():
    rule = get_rule(*RULE)
    rec = [{"profile_id": "a", "archetype": "balanced_multimodal", "difficulty": "repetitive", "S": [1, 0, 1, 0, 0, 0, 1, 0]},        # e = (1, 1, 0, 1)
           {"profile_id": "b", "archetype": "visual_dominant", "difficulty": "repetitive", "S": [0, 0, 1, 0, 0, 0, 0, 0]}]
    rep = f1m.multilabel_report(f1m.cases_from_records(rec, rule), rule)
    assert list(rep.ovr_2x2) == list(MODALITIES)
    for m in MODALITIES:
        d = rep.ovr_2x2[m]
        assert d["matrix"] == [[d["tp"], d["fn"]], [d["fp"], d["tn"]]] and d["tp"] + d["fn"] + d["fp"] + d["tn"] == 2
        assert {"precision", "recall", "f1"} <= set(d)
    assert len(rep.matrix_4x4) == 4 and rep.to_dict()["official_aggregation"] == "samples"
    src = Path(f1m.__file__).read_text(encoding="utf-8")
    assert "matrix" not in src.split("def _prf")[1].split("def case_f1")[0]                          # la matriz de co-ocurrencia no interviene en el cálculo de P/R/F1


def test_the_official_path_never_uses_the_legacy_dominant_modality_rule():
    for mod in (inf, ev, rp, f1m):
        src = Path(mod.__file__).read_text(encoding="utf-8")
        tree = ast.parse(src)
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert not names & {"predicted_dominant", "expected_dominant", "LegacyDominantRule", "gold_for", "dominant_modality"}, mod.__name__
    with pytest.raises(KeyError):
        get_rule("gold-v1", "incl-ge1")                                                              # la regla histórica no se puede construir como regla oficial


def test_the_official_version_covers_inclusion_gold_aggregation_and_panel():
    rule = get_rule(*RULE)
    v = official_version(rule)
    assert v == "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2" and len(v) == 57
    assert rule.gold.rule_version in v and rule.inclusion.rule_id in v and rubric_v2.OFFICIAL_AGGREGATION in v and rubric_v2.PANEL_PROTOCOL_VERSION in v
    assert rubric_v2.APPROVED_RULE_VERSIONS == frozenset({v})                                        # exactamente la regla aprobada y registrada técnicamente, y solo esa


# ── R4 y evaluación de extremo a extremo (solo tmp_path, semilla y aprobación de PRUEBA) ───────────────────────────
@pytest.fixture(scope="module")
def evaluated(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    try:
        rule = get_rule(*RULE)
        mp.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))             # explícita para no depender del registro técnico; solo en memoria y durante este fixture
        plan = rp.build_plan(master_seed=MASTER, k=10, library_version=LIB, provisional=False, rule=rule)
        out = tmp_path_factory.mktemp("k10") / "r"
        manifest = rp.run(plan, out)
        return {"dir": out, "manifest": manifest, "official": ev.evaluate(out, official=True), "provisional": ev.evaluate(out, official=False)}
    finally:
        mp.undo()


def test_replicas_store_f1_convergence_and_full_provenance(evaluated):
    out, m = evaluated["dir"], evaluated["manifest"]
    rep0 = rp.replica_cases(out, 0)
    assert {"profile_id", "f1", "k_stop", "stop_reason", "seed", "S"} <= set(rep0[0]) and len(rep0) == 100
    import json
    body = json.loads((out / "replica_03.json").read_text(encoding="utf-8"))
    assert body["replica_id"] == 3 and body["batch_seed"] == m["batch_seeds"][3]
    prov = body["provenance"]
    assert prov["rule_version"] == "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2" and prov["gold_fingerprint"] == GOLD_RULES["gold-v2-cand-A"].fingerprint()
    assert prov["dataset_sha256"] == m["dataset"]["sha256"] and prov["library_manifest_sha256"] == m["library"]["manifest_sha256"] and "commit" in prov["code_version"]
    assert prov["config"]["pso"] == m["config"]["pso"] and "gold/rubric_v2.py" in m["modules"] and "gold/f1_multilabel.py" in m["modules"]
    assert m["protocol"]["aggregation"] == "samples" and m["protocol"]["inference"]["alternative"] == "greater"


def test_evaluation_uses_hundred_profile_units_and_the_t_ci_over_ten_replicas(evaluated):
    e = evaluated["official"]
    assert e["status"] == "OFICIAL" and e["k"] == 10 and e["n_profiles"] == 100 and e["statistical_unit"] == "profile_mean_over_replicas"
    assert len(e["f1_adapt_by_replica"]) == 10 and e["ci95"]["df"] == 9 and e["ci95"]["method"] == "student_t_one_sample"
    assert e["inference"]["n"] == 100 and len(e["profile_means"]["per_profile"]) == 100
    assert all(len(p["f1_by_replica"]) == 10 for p in e["profile_means"]["per_profile"].values())
    assert e["consistency"]["equal"] is True and e["criterion"]["rule"] == "AND"
    assert e["criterion"]["combined_pass"] == (e["criterion"]["ci_pass"] and e["criterion"]["statistical_pass"] if e["criterion"]["statistical_pass"] is not None else None)


def test_evaluation_reports_modality_archetype_and_convergence_variability(evaluated):
    e = evaluated["official"]
    assert set(e["by_modality"]) == set(MODALITIES) and all(len(v["ovr_2x2_by_replica"]) == 10 for v in e["by_modality"].values())
    assert set(e["by_archetype"]) == {a.value for a in Archetype}
    conv = e["convergence"]
    assert len(conv["per_replica"]) == 10 and set(conv["across_replicas"]) == {"CR", "k_stop_mean", "k_stop_max"}
    assert e["computational_cost"]["status"] == "no medido"


def test_an_unapproved_directory_cannot_be_evaluated_officially(evaluated, monkeypatch):
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset())                            # la regla del directorio deja de estar registrada: el guard de evaluación sigue cerrado
    with pytest.raises(RuleNotApproved):
        ev.evaluate(evaluated["dir"], official=True)
    assert evaluated["provisional"]["status"] == "PROVISIONAL"


# ── R · separación core / full-stack ───────────────────────────────────────────────────────────────────────────────
def test_R_the_core_experiment_cannot_claim_rnf01_or_rnf04(evaluated):
    e = evaluated["official"]
    assert e["scope"]["experiment"] == "core_replay_k10" and set(e["scope"]["supports"]) == {"F1_adapt", "convergence"}
    for claim in ("RNF-01", "RNF-04", "L_resp", "throughput"):
        with pytest.raises(ev.ClaimNotSupported):
            ev.assert_claim_allowed(e, claim)
    ev.assert_claim_allowed(e, "F1_adapt")
    ev.assert_claim_allowed(e, "convergence")
    with pytest.raises(ev.ClaimNotSupported):
        ev.assert_claim_allowed(e, "cualquier_otra_cosa")                                            # lo no declarado tampoco se sustenta


def test_R_the_evaluation_can_be_written_only_to_a_new_directory(evaluated, tmp_path):
    out = ev.write_evaluation(evaluated["official"], tmp_path / "eval")
    assert (out / "evaluation.json").exists()
    with pytest.raises(SystemExit, match="no se sobrescriben"):                                      # la guardia de `isolated_env` impide sobrescribir
        ev.write_evaluation(evaluated["official"], tmp_path / "eval")
