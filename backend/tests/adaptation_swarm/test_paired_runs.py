"""OE2 F.1: capacidad TÉCNICA del contraste pareado por (run_index, carga) (alternativa B). No es metodología aprobada, no sustituye a A y no está conectada al resultado confirmatorio.
El test central demuestra que preparar B no cambia nada de A."""

import copy
import hashlib
import inspect
import json
import math

import numpy as np
import pytest
from scipy import stats

from adaptation_swarm.analysis import comparison as cmp
from adaptation_swarm.oe import campaign_guards as guards
from adaptation_swarm.oe import campaign_spec, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, paired_runs as pr

CONTRAST = "swarm_vs_decision_table_contrast"


def _run(system, users, i, p95, thr, **kw):
    seq = hashlib.sha256(f"{i}|{users}".encode()).hexdigest()
    r = {"run_id": f"C-{system}|u{users}|N20-r{i:02d}", "system": system, "users": users, "load": users, "run_index": i, "batch_id": f"C-b{i:02d}", "seed": 1000 + i, "status": "ok", "comparable": True,
         "non_comparable_reason": None, "persist_policy": "off", "comparison_role": CONTRAST, "persistence_condition": "comparison_off", "profile_sequence_sha256": seq, "latency_p95_ms": p95, "throughput_rps": thr,
         "errors": 0, "timeouts": 0, "server_instance": 1, "server_restarted_before_run": i == 0, "server_runs_served_before": i, "execution_index": 2 * i + (0 if system == "swarm" else 1)}
    r.update(kw)
    return r


def _dataset(loads=(1, 10), n=10, seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for u in loads:
        for i in range(n):
            out.append(_run("swarm", u, i, 900.0 * math.exp(rng.normal(0, 0.05)), 17.0 + rng.normal(0, 0.3)))
            out.append(_run("decision_table", u, i, 30.0 * math.exp(rng.normal(0, 0.1)), 350.0 + rng.normal(0, 5)))
    return out


# ═════════════════════ formación de pares ═════════════════════
def test_pairs_are_formed_per_run_index_and_load_with_matching_seed_batch_and_sequence_hash():
    rep = pr.build_pairs(_dataset())
    assert rep["status"] == pr.STATUS and rep["n_pairs_total"] == 20 and rep["n_complete"] == 20 and rep["n_incomplete"] == 0 and rep["n_excluded"] == 0
    assert rep["n_same_seed"] == 20 and rep["n_same_sequence_hash"] == 20 and rep["n_sequence_hash_not_checked"] == 0 and rep["loads_with_complete_pairs"] == [1, 10] and rep["by_load"] == {"1": {"complete": 10, "incomplete": 0, "excluded": 0}, "10": {"complete": 10, "incomplete": 0, "excluded": 0}}
    p = rep["pairs"][0]
    assert (p["run_index"], p["users"], p["batch_id"], p["seed"], p["same_seed"], p["same_sequence_hash"]) == (0, 1, "C-b00", 1000, True, True)
    assert set(p["run_ids"]) == {"swarm", "decision_table"} and len(p["run_ids"]["swarm"]) == len(p["run_ids"]["decision_table"]) == 1


def test_the_same_run_index_is_required_a_different_one_never_pairs():
    recs = [_run("swarm", 1, 0, 900, 17), _run("decision_table", 1, 1, 30, 350)]
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 0 and rep["n_incomplete"] == 2 and {r for p in rep["pairs"] for r in p["reasons"]} == {"missing_proposal", "missing_baseline"}


def test_the_same_load_is_required_different_loads_never_pair():
    recs = [_run("swarm", 1, 0, 900, 17), _run("decision_table", 10, 0, 30, 350)]
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 0 and rep["n_incomplete"] == 2 and rep["by_load"] == {"1": {"complete": 0, "incomplete": 1, "excluded": 0}, "10": {"complete": 0, "incomplete": 1, "excluded": 0}}


def test_a_different_seed_or_batch_or_sequence_hash_excludes_the_pair_with_a_reason():
    base = [_run("swarm", 1, 0, 900, 17), _run("decision_table", 1, 0, 30, 350)]
    for field, reason in (("seed", "seed_mismatch"), ("batch_id", "batch_id_mismatch"), ("profile_sequence_sha256", "sequence_hash_mismatch")):
        recs = copy.deepcopy(base)
        recs[1][field] = "otro" if field != "seed" else 999
        rep = pr.build_pairs(recs)
        assert rep["n_complete"] == 0 and rep["pairs"][0]["status"] == "excluded" and reason in rep["pairs"][0]["reasons"], field


def test_a_missing_seed_or_batch_cannot_be_verified_so_the_pair_is_excluded_and_a_missing_hash_is_only_noted():
    recs = [_run("swarm", 1, 0, 900, 17), _run("decision_table", 1, 0, 30, 350)]
    nohash = copy.deepcopy(recs)
    for r in nohash:
        r.pop("profile_sequence_sha256")
    rep = pr.build_pairs(nohash)
    assert rep["n_complete"] == 1 and rep["n_sequence_hash_not_checked"] == 1 and rep["pairs"][0]["sequence_hash_checked"] is False        # no se inventa el hash: se anota que no se verificó
    noseed = copy.deepcopy(recs)
    noseed[0]["seed"] = None
    assert "seed_missing" in pr.build_pairs(noseed)["pairs"][0]["reasons"]


def test_an_incomplete_pair_is_recorded_not_imputed_and_not_silently_dropped():
    recs = _dataset(loads=(1,), n=3)
    recs = [r for r in recs if not (r["system"] == "decision_table" and r["run_index"] == 1)]
    rep = pr.build_pairs(recs)
    assert rep["n_pairs_total"] == 3 and rep["n_complete"] == 2 and rep["n_incomplete"] == 1
    inc = next(p for p in rep["pairs"] if p["status"] == "incomplete")
    assert inc["run_index"] == 1 and inc["reasons"] == ["missing_baseline"] and "values" not in inc and inc["run_ids"]["decision_table"] == []
    only2 = pr.paired_run_comparison(recs, "L_resp_P95_http", scale="log", test="wilcoxon")["loads"]["1"]
    assert only2["n_pairs"] == 2 and only2["status"] == "not_testable_fewer_than_3_pairs"                      # el par incompleto no aporta valor y no se imputa


def test_a_missing_system_leaves_every_pair_of_the_load_incomplete():
    recs = [r for r in _dataset(loads=(1,), n=4) if r["system"] == "swarm"]
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 0 and rep["n_incomplete"] == 4 and rep["loads_without_complete_pairs"] == [1]
    res = pr.paired_run_comparison(recs, "throughput_http", scale="raw", test="paired_t")
    assert res["loads"] == {}                                                                                  # nada que contrastar; no se inventan valores


def test_proposal_with_persistence_on_never_enters_the_pairs_and_off_labelled_rows_are_checked():
    recs = _dataset(loads=(1,), n=3)
    recs.append(_run("swarm", 1, 0, 4000.0, 9.0, persist_policy="on", comparison_role=campaign_spec.ROLE_PROPOSAL_COST, run_id="C-swarm|u1|N20|persON-r00"))
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 3 and {i["reason"] for i in rep["rows_ignored"]} == {"proposal_persistence_on"} and rep["pairs"][0]["values"]["swarm"]["L_resp_P95_http"] != 4000.0
    ok = pr.paired_run_comparison(recs, "L_resp_P95_http", scale="raw", test="paired_t")
    clean = pr.paired_run_comparison(_dataset(loads=(1,), n=3), "L_resp_P95_http", scale="raw", test="paired_t")
    assert ok["loads"] == clean["loads"]                                                                      # la fila ON no cambia el contraste
    mislabelled = _dataset(loads=(1,), n=3) + [_run("swarm", 1, 5, 1.0, 1.0, persist_policy="on", comparison_role=CONTRAST)]
    assert [i["reason"] for i in pr.build_pairs(mislabelled)["rows_ignored"]] == ["proposal_persistence_on"] and pr.build_pairs(mislabelled)["n_complete"] == 3      # ON con rol de contraste: sigue siendo ON y no entra
    baseline_on = _dataset(loads=(1,), n=3) + [_run("decision_table", 1, 7, 1.0, 1.0, persist_policy="on")]
    assert [i["reason"] for i in pr.build_pairs(baseline_on)["rows_ignored"]] == ["not_contrast_condition"] and pr.build_pairs(baseline_on)["n_complete"] == 3        # nunca decision_table con ON
    nofields = _dataset(loads=(1,), n=2) + [{"run_id": "x", "system": "swarm", "users": 1, "run_index": 9}]
    assert any(i["reason"] == "missing_fields" and "persist_policy" in i["fields"] for i in pr.build_pairs(nofields)["rows_ignored"])        # sin condición declarada: fail-closed


def test_other_systems_are_never_paired():
    recs = _dataset(loads=(1,), n=3) + [_run("rules", 1, i, 100, 100) for i in range(3)] + [_run("bruteforce", 1, i, 5000, 1) for i in range(3)]
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 3 and sum(1 for i in rep["rows_ignored"] if i["reason"] == "other_system") == 6


def test_non_comparable_runs_exclude_their_pair_and_the_whole_load_is_generator_limited_for_both_systems_symmetrically():
    recs = _dataset(loads=(1, 10), n=4)
    for r in recs:
        if r["system"] == "decision_table" and r["users"] == 10 and r["run_index"] == 2:
            r["comparable"], r["non_comparable_reason"] = False, "generator_saturated"
    rep = pr.build_pairs(recs)
    assert rep["generator_limited_loads"] == [10] and rep["by_load"]["1"]["complete"] == 4 and rep["by_load"]["10"] == {"complete": 0, "incomplete": 0, "excluded": 4}
    reasons = {tuple(sorted(p["reasons"])) for p in rep["pairs"] if p["users"] == 10}
    assert ("generator_limited_level",) in reasons and any("not_comparable:decision_table:generator_saturated" in r for p in rep["pairs"] for r in p["reasons"])
    assert all(len(p["run_ids"]["swarm"]) == 1 for p in rep["pairs"] if p["users"] == 10)                  # los datos de la propuesta se conservan (registrados), no se borran
    same = pr.build_pairs([{**r, **({"comparable": False, "non_comparable_reason": "generator_saturated"} if r["system"] == "swarm" and r["users"] == 10 and r["run_index"] == 2 else {})} for r in _dataset(loads=(1, 10), n=4)])
    assert same["generator_limited_loads"] == [10] and same["by_load"]["10"]["complete"] == 0                  # la misma carga sale aunque el saturado sea la propuesta
    assert hw.GENERATOR_POLICY["id"] == "generator-saturation-v1" and hw.GENERATOR_POLICY["threshold_percent"] == 90.0


def test_a_run_that_is_not_ok_excludes_its_pair_and_stress_loads_stay_outside_the_contrast():
    recs = _dataset(loads=(1, 50), n=3)
    recs[0]["status"] = "invalid_window_shorter_than_min"
    rep = pr.build_pairs(recs)
    assert any(r.startswith("run_status_not_ok:swarm") for p in rep["pairs"] for r in p["reasons"])
    stress = [p for p in rep["pairs"] if p["users"] == 50]
    assert stress and all(p["status"] == "excluded" and "stress_regime_outside_contrast" in p["reasons"] for p in stress) and rep["loads_with_complete_pairs"] == [1]


def test_duplicate_runs_and_duplicate_pairs_are_flagged_and_never_resolved_silently():
    recs = _dataset(loads=(1,), n=2)
    recs.append(_run("swarm", 1, 0, 111.0, 11.0, run_id="C-swarm|u1|N20-r00-DUP"))
    rep = pr.build_pairs(recs)
    dup = next(p for p in rep["pairs"] if p["run_index"] == 0)
    assert dup["status"] == "excluded" and dup["reasons"] == ["duplicate_run"] and len(dup["run_ids"]["swarm"]) == 2 and "values" not in dup and rep["n_complete"] == 1        # no se elige entre duplicados
    twice = _dataset(loads=(1,), n=1) * 2
    assert pr.build_pairs(twice)["pairs"][0]["reasons"] == ["duplicate_run"]


def test_errors_and_timeouts_are_recorded_per_pair_but_no_validity_rule_is_invented():
    recs = _dataset(loads=(1,), n=3)
    recs[0]["errors"], recs[0]["timeouts"] = 5, 2
    rep = pr.build_pairs(recs)
    assert rep["n_complete"] == 3 and rep["n_pairs_with_errors_or_timeouts"] == 1 and rep["error_timeout_rule"].startswith("PENDING")                  # no se excluye por errores
    flagged = next(p for p in rep["pairs"] if p["run_index"] == 0)
    assert flagged["has_errors_or_timeouts"] == {"swarm": True, "decision_table": False}


def test_cold_warm_metadata_travels_with_each_pair_without_being_interpreted():
    rep = pr.build_pairs(_dataset(loads=(1,), n=2))
    c = rep["pairs"][0]["carried"]
    assert set(c) == {"swarm", "decision_table"} and set(c["swarm"]) == {"server_instance", "server_restarted_before_run", "server_runs_served_before", "execution_index"} and c["swarm"]["server_restarted_before_run"] is True
    assert "cold" not in json.dumps(pr.PENDING).lower()                                                       # no hay política cold/warm en el módulo


# ═════════════════════ estimando y pruebas ═════════════════════
def test_estimand_and_test_must_be_requested_explicitly_there_is_no_default_and_no_normality_driven_selection():
    recs = _dataset()
    sig = inspect.signature(pr.paired_run_comparison)
    assert sig.parameters["scale"].default is inspect.Parameter.empty and sig.parameters["test"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        pr.paired_run_comparison(recs, "L_resp_P95_http")
    for kw in (dict(scale="auto", test="paired_t"), dict(scale="log", test="auto"), dict(scale="log", test=None)):
        with pytest.raises(ValueError, match="explícit"):
            pr.paired_run_comparison(recs, "L_resp_P95_http", **kw)
    with pytest.raises(ValueError, match="métrica desconocida"):
        pr.paired_run_comparison(recs, "decision_ms", scale="log", test="wilcoxon")
    res = pr.paired_run_comparison(recs, "L_resp_P95_http", scale="log", test="wilcoxon")["loads"]["1"]
    assert res["test"] == "wilcoxon" and res["normality_used_for_selection"] is False and "shapiro_p_diagnostic" in res                           # se informa; no decide


def test_paired_t_matches_scipy_on_raw_and_on_log_differences_and_reports_the_estimand():
    recs = _dataset(n=10, seed=3)
    res = pr.paired_run_comparison(recs, "L_resp_P95_http", scale="raw", test="paired_t")["loads"]["10"]
    sw = np.array([r["latency_p95_ms"] for r in sorted(recs, key=lambda r: r["run_index"]) if r["system"] == "swarm" and r["users"] == 10])
    bl = np.array([r["latency_p95_ms"] for r in sorted(recs, key=lambda r: r["run_index"]) if r["system"] == "decision_table" and r["users"] == 10])
    ref = stats.ttest_rel(sw, bl)
    assert res["p_value"] == pytest.approx(ref.pvalue) and res["statistic"] == pytest.approx(ref.statistic) and res["mean_diff"] == pytest.approx((sw - bl).mean()) and res["n_pairs"] == 10 and res["status"] == "ok"
    assert res["estimand"].startswith("mean of d_i = swarm_i") and res["delta"] == "swarm - decision_table" and "geometric_ratio" not in res
    lg = pr.paired_run_comparison(recs, "L_resp_P95_http", scale="log", test="paired_t")["loads"]["10"]
    ref_log = stats.ttest_rel(np.log(sw), np.log(bl))
    assert lg["p_value"] == pytest.approx(ref_log.pvalue) and lg["mean_diff"] == pytest.approx((np.log(sw) - np.log(bl)).mean()) and lg["geometric_ratio"] == pytest.approx(math.exp(lg["mean_diff"]))
    assert lg["estimand"].startswith("mean of log(swarm_i)") and len(lg["diff_ci95_bootstrap"]) == 2


def test_wilcoxon_matches_scipy_and_log_differences_are_the_log_ratio_of_each_pair():
    recs = _dataset(n=10, seed=4)
    res = pr.paired_run_comparison(recs, "throughput_http", scale="raw", test="wilcoxon")["loads"]["1"]
    sw = np.array([r["throughput_rps"] for r in sorted(recs, key=lambda r: r["run_index"]) if r["system"] == "swarm" and r["users"] == 1])
    bl = np.array([r["throughput_rps"] for r in sorted(recs, key=lambda r: r["run_index"]) if r["system"] == "decision_table" and r["users"] == 1])
    assert res["p_value"] == pytest.approx(stats.wilcoxon(sw - bl).pvalue) and res["median_diff"] == pytest.approx(np.median(sw - bl)) and res["test"] == "wilcoxon"
    lg = pr.paired_run_comparison(recs, "throughput_http", scale="log", test="wilcoxon")["loads"]["1"]
    assert lg["p_value"] == pytest.approx(stats.wilcoxon(np.log(sw) - np.log(bl)).pvalue) and lg["median_diff"] == pytest.approx(np.median(np.log(sw) - np.log(bl)))
    d = pr.build_pairs(recs)["pairs"][0]
    assert math.log(d["values"]["swarm"]["throughput_http"]) - math.log(d["values"]["decision_table"]["throughput_http"]) == pytest.approx(math.log(sw[0] / bl[0]))


def test_degenerate_inputs_are_reported_as_not_testable_never_as_a_result():
    two = pr.paired_run_comparison(_dataset(loads=(1,), n=2), "L_resp_P95_http", scale="log", test="paired_t")["loads"]["1"]
    assert two["status"] == "not_testable_fewer_than_3_pairs" and two["p_value"] is None
    const = [r for i in range(4) for r in (_run("swarm", 1, i, 100.0, 10.0), _run("decision_table", 1, i, 50.0, 5.0))]
    assert pr.paired_run_comparison(const, "L_resp_P95_http", scale="raw", test="paired_t")["loads"]["1"]["status"] == "undefined_constant_differences"
    nonpos = _dataset(loads=(1,), n=4)
    nonpos[0]["latency_p95_ms"] = 0.0
    assert pr.paired_run_comparison(nonpos, "L_resp_P95_http", scale="log", test="paired_t")["loads"]["1"]["status"] == "not_testable_non_positive_values"
    nan = _dataset(loads=(1,), n=4)
    nan[0]["latency_p95_ms"] = None
    assert pr.paired_run_comparison(nan, "L_resp_P95_http", scale="raw", test="paired_t")["loads"]["1"]["status"] == "not_testable_missing_or_non_finite_values"


def test_both_metrics_use_the_same_pairs_scale_and_test():
    out = pr.paired_contrast(_dataset(), scale="log", test="wilcoxon")
    assert set(out) == {"L_resp_P95_http", "throughput_http"} and all(v["scale"] == "log" and v["test"] == "wilcoxon" for v in out.values())
    assert out["L_resp_P95_http"]["pairing"]["n_complete"] == out["throughput_http"]["pairing"]["n_complete"] == 20


# ═════════════════════ Holm, estado y no alteración de A ═════════════════════
def test_the_b_output_has_the_format_the_existing_holm_mechanism_accepts_without_connecting_or_fixing_m():
    contrast = pr.paired_contrast(_dataset(loads=(1, 10), n=10, seed=7), scale="log", test="wilcoxon")
    hyps = pr.hypotheses_for_holm(contrast)
    assert sorted(hyps) == ["L_resp_P95_http@u1", "L_resp_P95_http@u10", "throughput_http@u1", "throughput_http@u10"]            # mismos nombres que la familia de A
    fam = o2.holm_family("paired:swarm_vs_decision_table", hyps, confirmatory=False)
    assert fam["confirmatory"] is False and fam["m"] == 4 and all(h["p_holm"] is not None and h["p_holm"] >= h["p_raw"] for h in fam["hypotheses"].values())
    assert "m" not in inspect.signature(pr.hypotheses_for_holm).parameters and contrast["L_resp_P95_http"]["alpha_not_applied"] is True and "significant" not in contrast["L_resp_P95_http"]["loads"]["1"]


def test_b_is_flagged_as_implemented_technically_not_approved_and_never_as_the_primary_analysis():
    res = pr.paired_run_comparison(_dataset(loads=(1,), n=5), "L_resp_P95_http", scale="log", test="paired_t")
    assert res["status"] == "IMPLEMENTED_TECHNICALLY_NOT_METHODOLOGICALLY_APPROVED" == pr.STATUS
    assert (res["confirmatory"], res["selected_as_primary"], res["approved_by_advisor"]) == (False, False, False) and res["pending"]["primary_analysis"].startswith("NO") and res["pending"]["advisor_approval"] == "NO"
    cap = campaign_spec.SPEC["oe2"]["methodological_decisions"]["http_pairing"]
    assert cap["status"] == "DECIDED" and cap["chosen"] == "independent_runs" and cap["advisor_approved"] is False and cap["decision_level"] == "INTERNAL_STUDY_DECISION" and cap["implemented_today"] == "independent_runs"      # F.2.3: A primaria; B NO
    tc = cap["technical_capability"]["paired_by_run_index_and_load"]
    assert tc["status"] == pr.STATUS and tc["selected_as_primary"] is False and tc["approved_by_advisor"] is False and tc["connected_to_confirmatory_output"] is False
    assert tc["role"] == "descriptive_sensitivity_outside_holm" and any(b.id == "PEND" for b in guards.evaluate(None))                    # B es sensibilidad; el guard PEND sigue en pie (quedan decisiones del asesor)


# SHA-256 del código fuente. `F1_*`: bloques de la ruta A que NO cambiaron desde el checkpoint 51d2c7e (siguen siendo los mismos). `G_*`: las dos funciones que la Fase G (F.2.3) cambió A PROPÓSITO
# (contraste primario Welch sobre log, familia de Holm fija, informe de errores): se fijan en su versión de G para que cualquier cambio posterior sea visible.
F1_UNCHANGED_SHA256 = {
    "o2.runs_comparison": "e2013c0e8f18e47184ec37e17f3f9c9d70d975d3a9253e929aa7424c3ae85cee", "o2.holm_family": "bf924c7fb90de569e096b8c5d0836bd85a7076ee3e5e61854e0358567a333a21",
    "o2.paired_log_by_profile": "641bb73bf1a55e1ffe8d30e7b34c4f7e6e52a75b5f939f05ef22bc0280b3f889", "hw.summarize_run": "82ef1dfdfb89977e74b94ccced08843b44de0e0b6097e19bb0896f9a543e136a",
    "cmp.independent_comparison": "3b595917a23a812fec5b98826e40773746c1bfde7fc1c58426d24c3ab8136cd7", "cmp.holm": "5137a813652a3953c03fcb72d279e2b9413523f57cde667a6e55cb49d92b9379",
    "cmp._bootstrap_mean_ci": "172f5df702f0af51f731a8fa3a7f6ede21724cc2a068eb5c5728098af6092899",
}
G_CHANGED_SHA256 = {
    "o2.analyze": "8a1db79f3121d6658312b997a4468b7515f2fe2d8dfc0c320f782dc5c4ff79cb", "hc.analyze_records": "9e2981c9e7cf98b8792e9c96bd7d1b57cdf173a538c7c31da214e3494169513c",
}


def _sha(fn):
    return hashlib.sha256(inspect.getsource(fn).rstrip(chr(10)).encode()).hexdigest()


def test_the_unchanged_blocks_of_analysis_a_and_holm_are_exactly_what_they_were_and_the_changed_ones_are_pinned():
    fns = {"o2.runs_comparison": o2.runs_comparison, "o2.holm_family": o2.holm_family, "o2.paired_log_by_profile": o2.paired_log_by_profile, "hw.summarize_run": hw.summarize_run,
           "cmp.independent_comparison": cmp.independent_comparison, "cmp.holm": cmp.holm, "cmp._bootstrap_mean_ci": cmp._bootstrap_mean_ci}
    for name, fn in fns.items():
        assert _sha(fn) == F1_UNCHANGED_SHA256[name], name
    assert _sha(o2.analyze) == G_CHANGED_SHA256["o2.analyze"] and _sha(hc.analyze_records) == G_CHANGED_SHA256["hc.analyze_records"]
    import ast
    for mod in (o2, hc):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(mod))):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names |= {node.module or ""} | {f"{node.module}.{a.name}" for a in node.names}
        assert not any("paired_runs" in n for n in names)                                                    # A no depende de B ni la llama


def test_preparing_and_running_b_does_not_change_the_results_of_a_nor_mutate_the_records():
    recs = _dataset(loads=(1, 10, 25), n=6, seed=11)
    summaries = [{**r, "latency_p95_ms": r["latency_p95_ms"], "throughput_rps": r["throughput_rps"]} for r in recs]
    before_a = json.dumps(o2.analyze([], copy.deepcopy(summaries)), sort_keys=True, default=str)
    before_records = copy.deepcopy(recs)
    for scale in pr.SCALES:
        for test in pr.TESTS:
            pr.paired_contrast(recs, scale=scale, test=test)
    pr.build_pairs(recs)
    after_a = json.dumps(o2.analyze([], copy.deepcopy(summaries)), sort_keys=True, default=str)
    assert after_a == before_a and recs == before_records                                                    # A idéntica y los datos de entrada intactos
    a = json.loads(after_a)
    fam = a["families"]["primary:swarm_vs_decision_table"]
    assert a["official"] is False and a["oe2_official"] is False and fam["confirmatory"] is True and "paired" not in json.dumps(a["families"]) and fam["m"] == 8 and fam["n_tested"] == 6      # m FIJO (F.2.3): 6 testadas de 8
    assert sorted(h.split("@")[0] for h, v in fam["hypotheses"].items() if v["p_raw"] is not None) == sorted(["L_resp_P95_http"] * 3 + ["throughput_http"] * 3)
    ra = hc.analyze_records("oe2", [{**s, "p95_ms": s["latency_p95_ms"], "throughput_http": s["throughput_rps"]} for s in summaries])
    assert json.dumps(ra, sort_keys=True, default=str) == json.dumps(hc.analyze_records("oe2", [{**s, "p95_ms": s["latency_p95_ms"], "throughput_http": s["throughput_rps"]} for s in summaries]), sort_keys=True, default=str)


def test_a_is_independent_runs_with_a_fixed_family_and_never_the_paired_path():
    assert "independent_comparison" in inspect.getsource(o2.runs_comparison) and "holm_fixed_family" in inspect.getsource(o2.analyze) and "welch_log_comparison" in inspect.getsource(o2.primary_hypothesis)
    assert campaign_spec.SPEC["alpha"] == 0.05 and o2.ALPHA == 0.05 and o2.CONTRAST_MAX_USERS == hw.CONTRAST_MAX_USERS == 25
