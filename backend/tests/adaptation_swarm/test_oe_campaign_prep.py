"""Preparación de las campañas oficiales OE1–OE4: ANOVA factorial por corrida, ventana HTTP, indicadores OE1 y especificación interna. Sin Redis, red ni Locust."""

import itertools

import numpy as np
import pytest

from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import campaign_spec, factorial, http_window, oe1_scores
from adaptation_swarm.oe.conditions import oe3_full_factorial, oe4_grid
from adaptation_swarm.oe.oe1 import MET, NOT_MEASURED, NOT_MET


def _runs(effect_a=0.0, effect_ab=0.0, reps=6, seed=1):
    rng = np.random.default_rng(seed)
    rows = []
    for a, b in itertools.product(("x", "y"), ("u", "v")):
        for _ in range(reps):
            mu = 5 + (effect_a if a == "y" else 0) + (effect_ab if (a, b) == ("y", "v") else 0)
            rows.append({"A": a, "B": b, "t": float(np.exp(mu + rng.normal(0, 0.1)))})
    return rows


def test_factorial_anova_detects_main_effect_and_interaction_on_runs():
    res = factorial.factorial_anova(_runs(effect_a=1.0, effect_ab=1.0), ("A", "B"), "t", log=True)
    assert res["status"] == "ok" and res["unit"] == "run"
    assert res["terms"]["A"]["significant"] and res["terms"]["A:B"]["significant"]
    assert "A:B" in res["interaction_significant"] and "condicional" in res["reading_rule"]
    assert res["marginal_means"]["A"]["y"]["geometric_mean"] > res["marginal_means"]["A"]["x"]["geometric_mean"]


def test_factorial_anova_null_effect_is_not_flagged_and_is_deterministic():
    a = factorial.factorial_anova(_runs(seed=3), ("A", "B"), "t", log=True)
    assert not any(v["significant"] for v in a["terms"].values())
    assert a == factorial.factorial_anova(_runs(seed=3), ("A", "B"), "t", log=True)


def test_factorial_anova_refuses_without_replication_or_with_missing_cells():
    assert factorial.factorial_anova(_runs(reps=1), ("A", "B"), "t")["status"] == "not_testable_no_residual_df"
    assert factorial.factorial_anova(_runs()[:-6], ("A", "B"), "t")["status"] == "not_testable_rank_deficient_design"
    bad = [{**r, "t": -1.0} for r in _runs()]
    assert factorial.factorial_anova(bad, ("A", "B"), "t", log=True)["status"] == "not_testable_log_of_non_positive"


def test_permutation_p_is_reported_when_requested():
    res = factorial.factorial_anova(_runs(effect_a=1.0), ("A", "B"), "t", log=True, permutation=True, n_perm=99)
    assert res["inference"].startswith("permutation") and res["terms"]["A"]["p_permutation"] <= 0.05


def test_aggregate_runs_averages_replicates_per_profile_before_the_run():
    base = {"condition": "c", "batch": 0, "package_valid": True, "f_x": 1}
    obs = [{**base, "profile_id": "p1", "status": "completed", "t": 10.0}, {**base, "profile_id": "p1", "status": "completed", "t": 20.0},
           {**base, "profile_id": "p2", "status": "completed", "t": 30.0}, {**base, "profile_id": "p3", "status": "failed", "t": 999.0}]
    (run,) = factorial.aggregate_runs(obs, ("t",))
    assert run["t"] == pytest.approx((15.0 + 30.0) / 2) and run["n_profiles"] == 2 and run["f_x"] == 1


def _oe3_obs(reps):
    obs = []
    rng = np.random.default_rng(7)
    for cond in oe3_full_factorial():
        for b in range(reps):
            for pid in ("p1", "p2", "p3"):
                obs.append({"condition": cond.name, "batch": b, "profile_id": pid, "replicate": b, "status": "completed", "package_valid": True,
                            "t_conv_ms": float(100 + 40 * (cond.mechanism == "social") + rng.normal(0, 3)), "k_stop": 5.0, "n_messages": 10.0, "gap_vs_optimum": 0.01,
                            "latency_ms": 50.0, "F": 0.5, **{f"f_{k}": v for k, v in cond.factors().items()}})
    return obs


def test_oe3_full_factorial_run_unit_estimates_interactions_when_replicated():
    a = oea.analyze("oe3", _oe3_obs(reps=3), [])
    fr = a["factorial_run_unit"]
    assert fr["unit"] == "run" and fr["runs_per_cell"] == {"min": 3, "max": 3}
    t = fr["t_conv_ms"]
    assert t["status"] == "ok" and t["terms"]["mechanism"]["significant"] and len(t["terms"]) == 31
    assert a["design"] == "full_factorial_2x2x2x2x3" and "main_effects" in a


def test_oe3_without_replication_is_not_confirmatory():
    assert oea.analyze("oe3", _oe3_obs(reps=1), [])["factorial_run_unit"]["t_conv_ms"]["status"] == "not_testable_no_residual_df"


def test_oe4_grid_is_6x3_and_run_level_anova_runs():
    grid = oe4_grid()
    assert len(grid) == 18 and {c.concurrency for c in grid} == {1, 5, 10, 25, 50, 100}
    obs, bat = [], []
    rng = np.random.default_rng(2)
    for c in grid:
        for b in range(3):
            for pid in ("p1", "p2", "p3"):
                obs.append({"condition": c.name, "batch": b, "profile_id": pid, "replicate": 0, "status": "completed", "package_valid": True, "t_conv_ms": 100 + c.concurrency + rng.normal(0, 2),
                            "latency_ms": 200.0 + c.concurrency * 5 + rng.normal(0, 5), "k_stop": 5, **{f"f_{k}": v for k, v in c.factors().items()}})
            bat.append({"condition": c.name, "batch": b, "throughput_rps": 10.0 + rng.normal(0, 0.2)})
    out = oea.factorial_oe4(obs, bat)
    assert out["all_loads"]["latency_p95_ms"]["terms"]["concurrency"]["significant"]
    assert out["contrast_regime_le_25"]["t_conv_ms"]["levels"]["concurrency"] == ["1", "10", "25", "5"]


def _raw(duration, rate=10.0, fail_every=0, t0=1000.0):
    rows, t, i = [], t0, 0
    while t < t0 + duration:
        i += 1
        bad = bool(fail_every and i % fail_every == 0)
        rows.append({"t_end_epoch_s": t, "response_ms": 100.0 + (i % 10) * 10, "ok": not bad, "timeout": False})
        t += 1 / rate
    return rows


def test_http_window_excludes_warmup_and_requires_60s():
    ok = http_window.summarize_run(_raw(75), [], users=10, system="swarm", run_id="r1")
    assert ok["status"] == "ok" and ok["duration_s"] == pytest.approx(65, abs=0.2) and ok["throughput_rps"] == pytest.approx(10, rel=0.02)
    assert ok["rnf01_p95_below_2s"] is True and ok["rnf04_met"] is False and ok["regime"] == "contrast"
    assert http_window.summarize_run(_raw(60), [], users=10, system="swarm", run_id="r2")["status"] == "invalid_window_shorter_than_min"
    assert http_window.summarize_run(_raw(90), [], users=10, system="swarm", run_id="r3", warmup_s=5)["status"] == "invalid_warmup_below_10s"


def test_http_window_stress_regime_does_not_evaluate_the_2s_threshold_and_flags_generator_cpu():
    cpu = [{"t_epoch_s": 1000.0 + s, "loadgen_cpu_percent": 95.0} for s in range(80)]
    r = http_window.summarize_run(_raw(80, rate=30, fail_every=200), cpu, users=100, system="swarm", run_id="r")
    assert r["regime"] == "stress" and r["rnf01_p95_below_2s"] is None and r["generator_possibly_bottleneck"] is True
    assert r["rnf04_met"] is True and 0 < r["error_rate"] < 0.01
    assert http_window.summarize_runs([r])["swarm|u100"]["throughput_rps"] == [r["throughput_rps"]]


def test_wilson_and_reliability_use_valid_outputs_not_cr():
    lo, hi = oe1_scores.wilson_interval(95, 100)
    assert lo == pytest.approx(0.8882, abs=1e-3) and hi == pytest.approx(0.9785, abs=1e-3)
    obs = [{"status": "completed", "package_valid": True}] * 8 + [{"status": "completed", "package_valid": False}, {"status": "failed", "package_valid": False}, {"status": "completed"}]
    rel = oe1_scores.reliability_oe1(obs)
    assert rel["valid"] == 8 and rel["n"] == 11 and rel["wilson_ci95"][0] < 8 / 11 < rel["wilson_ci95"][1]


def test_compliance_score_excludes_unmeasured_and_the_circular_requirement():
    table = [{"id": "RF01", "dimension": "funcionalidad", "status": MET}, {"id": "RF02", "dimension": "funcionalidad", "status": NOT_MET},
             {"id": "REL-C", "dimension": "confiabilidad", "status": MET}, {"id": "RNF01", "dimension": "eficiencia", "status": NOT_MEASURED},
             {"id": "RNF03", "dimension": "calidad", "status": MET}]
    s = oe1_scores.compliance_score_oe1(table, exclude_ids=("RNF03",))
    assert s["dimensions"]["funcionalidad"]["score"] == 0.5 and s["dimensions"]["eficiencia"]["score"] is None and s["dimensions"]["calidad"]["score"] is None
    assert s["global"] == pytest.approx((0.5 + 1.0) / 2) and s["failed"] == ["RF02"] and s["not_evaluated"] == ["RNF01"] and s["critical_failed"] is None


def test_campaign_spec_is_hashed_internal_and_never_claims_advisor_approval():
    spec = campaign_spec.SPEC
    assert spec["advisor_approved"] is False and campaign_spec.STATUS.startswith("TECHNICAL_INTERNAL")
    oe2 = spec["oe2"]
    assert oe2["proposal_system"] == "swarm" and oe2["conventional_system"] == "decision_table" and oe2["comparator_primary"] == "decision_table" and oe2["comparator_fixed_before_data"] is True
    assert oe2["system_roles"] == {"swarm": "proposal", "decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"}
    assert oe2["auxiliary_contrasts"] == ["rules", "bruteforce"] and oe2["design"]["systems"] == ["swarm", "decision_table"] and "comparator_secondary" not in oe2
    assert oe2["persist_policy"]["campaign"] == "off" and oe2["persist_policy"]["on_supported_for_comparison"] is False and oe2["profile_sequence"]["same_sequence_for_all_systems"] is True
    assert oe2["time_contract"]["candidate_common_metric"] == "time_to_final_config_ms" and oe2["time_contract"]["validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and oe2["time_contract"]["t_conv_equivalence"] == "NOT_ESTABLISHED"
    assert "FUERA de Holm" in oe2["holm_family"] and "{L_resp P95 HTTP, throughput HTTP}" in oe2["holm_family"]
    assert spec["h1"]["conjunctive"] is True and spec["oe5"]["sus"]["rule"].startswith("media > 75 NO basta")
    assert len(campaign_spec.spec_hash()) == 64 and campaign_spec.spec_hash() == campaign_spec.identity()["sha256"]
    blockers = " | ".join(campaign_spec.open_blockers())
    assert "F1 v3" not in blockers and "LMS" in blockers and "t_conv_baselines" not in blockers and "common_time_indicator_oe2" in blockers       # F1 v3 es dependencia de OE5, no de OE2
    assert "contrato de tiempo oe2-time-contract-v2 sin validar" in blockers and "decisión del asesor" not in blockers          # GAP tecnico concreto, no una consulta al asesor
