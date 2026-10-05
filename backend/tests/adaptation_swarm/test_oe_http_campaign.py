"""Orquestador HTTP de campaña y análisis confirmatorio de OE2/OE4. Sin Locust, servidor, Redis ni red: la E/S se inyecta."""

import json

import numpy as np
import pytest

from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import campaign_spec, http_campaign as hc, http_window, oe2_confirmatory as o2


def _plan(**kw):
    base = dict(experiment="oe4", runs=10, base_seed=7, users=hc.OE4_USERS, particles=hc.OE4_PARTICLES, systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="C")
    return hc.plan(**{**base, **kw})


def test_oe4_plan_is_the_full_6x3_grid_with_10_runs_and_distinct_seeds_per_run():
    p = _plan()
    assert len(p) == 6 * 3 * 10 and {r["load"] for r in p} == {1, 5, 10, 25, 50, 100} and {r["swarm_N"] for r in p} == {10, 20, 30}
    cells = {}
    for r in p:
        cells.setdefault(r["cell"], []).append(r)
    assert len(cells) == 18 and all(len(v) == 10 for v in cells.values())
    assert all(len({r["seed"] for r in v}) == 10 for v in cells.values())               # nunca una copia de reloj dentro de la celda
    assert len({r["run_id"] for r in p}) == len(p)                                      # cada corrida identificable
    assert {r["seed"] for r in cells["swarm|u1|N10"]} == {r["seed"] for r in cells["swarm|u100|N30"]}      # bloqueado entre celdas
    assert p == _plan()                                                                  # determinista


def test_oe2_plan_is_proposal_plus_independent_conventional_by_default_and_rejects_unknown_or_incomplete():
    p = _plan(experiment="oe2", users=[1, 10, 25, 50])
    assert {r["system"] for r in p} == {"swarm", "decision_table"} and len(p) == 2 * 4 * 10
    assert {r["system"]: r["system_role"] for r in p} == {"swarm": "proposal", "decision_table": "conventional_independent"} and {r["persist_policy"] for r in p} == {"off"}
    assert tuple(hc.DEFAULT_OE2_SYSTEMS) == ("swarm", "decision_table")
    with pytest.raises(ValueError, match="desconocidos"):
        _plan(experiment="oe2", systems=["swarm", "decision_table", "lms"])
    for incomplete in (["swarm", "rules"], ["swarm", "rules", "bruteforce"], ["decision_table"]):
        with pytest.raises(ValueError, match="convencional independiente|faltan"):                     # rules y bruteforce no sustituyen al convencional independiente
            _plan(experiment="oe2", systems=incomplete)
    aux = _plan(experiment="oe2", users=[1], runs=1, systems=["swarm", "decision_table", "rules", "bruteforce"])
    assert {r["system"]: r["system_role"] for r in aux} == {"swarm": "proposal", "decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"}


def test_the_same_profile_sequence_hash_applies_to_every_system_of_a_run_and_changes_with_the_seed():
    systems = ["swarm", "decision_table", "rules"]
    p = _plan(experiment="oe2", users=[1, 10], systems=systems)
    by = {}
    for r in p:
        by.setdefault((r["run_index"], r["load"]), set()).add(r["profile_sequence_sha256"])
    assert all(len(v) == 1 for v in by.values())                                                    # misma secuencia para todos los sistemas de la misma corrida y carga
    assert len({next(iter(v)) for v in by.values()}) == len(by)                                     # corridas / cargas distintas => secuencias distintas
    assert [r["profile_sequence_sha256"] for r in p] == [r["profile_sequence_sha256"] for r in _plan(experiment="oe2", users=[1, 10], systems=systems)]


def test_official_is_refused_on_non_target_hardware_and_short_windows_and_open_blockers():
    refusals = hc.official_refusals({"cpu_count": 4}, runs=5, warmup=5, window=30)
    text = " | ".join(refusals)
    assert "hardware" in text and "corridas por celda" in text and "ventana" in text and "F1 v3 sin sellar" in text


def _fake_raw(rate, lat_ms, seconds=80):
    n = int(rate * seconds)
    return ([{"t_end_epoch_s": 1000 + i / rate, "response_ms": lat_ms, "ok": True, "timeout": False, "t_conv_ms": 50.0, "decision_ms": 50.0, "metrics_ok": True} for i in range(n)], [{"t_epoch_s": 1000.0 + s, "loadgen_cpu_percent": 40.0} for s in range(seconds)])


def test_execute_writes_one_record_per_run_with_the_required_fields_and_no_invented_values():
    runs = _plan(runs=2, users=[1, 25], particles=[10])
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT", "official": False, "oe2_official": False}
    started = []
    out = hc.execute(runs, prov, warmup=10, window=60, do_run=lambda r, w, win: _fake_raw(10, 120.0), ensure_server=started.append, log=lambda m: None)
    assert len(out) == len(runs) and started == [r["swarm_N"] for r in runs]
    for rec in out:
        assert set(hc.RECORD_FIELDS) <= set(rec) and rec["status"] == "ok" and rec["throughput_internal"] is None
        assert rec["campaign_spec_hash"] == campaign_spec.spec_hash() and rec["warmup_seconds"] == 10 and rec["p95_ms"] == 120.0
        assert rec["throughput_http"] == pytest.approx(10, rel=0.02) and rec["generator_cpu"] == 40.0 and rec["t_conv_ms_mean"] == 50.0
        assert rec["decision_ms_mean"] == 50.0 and rec["system_role"] == "proposal" and rec["persist_policy"] == "off" and len(rec["profile_sequence_sha256"]) == 64
        assert rec["profile_sequence_check"] == {"checked": 0, "mismatches": 0, "unindexed": len(_fake_raw(10, 120.0)[0])}      # el log simulado no trae indices: se cuenta, no se supone


def test_short_run_is_recorded_as_invalid_not_dropped_or_padded():
    runs = _plan(runs=1, users=[1], particles=[10])
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {}, "hardware": {}, "definition_version": {}, "environment_class": "PILOT", "official": False, "oe2_official": False}
    (rec,) = hc.execute(runs, prov, warmup=10, window=60, do_run=lambda r, w, win: _fake_raw(10, 100.0, seconds=40), ensure_server=lambda n: None, log=lambda m: None)
    assert rec["status"] == "invalid_window_shorter_than_min" and rec["successful_requests"] is None and rec["p95_ms"] is None


def _records(rng, systems=("swarm", "decision_table", "rules", "bruteforce"), users=(1, 10, 25, 50), particles=(20,), runs=6, lat=None):
    lat = lat or {"swarm": 900.0, "decision_table": 200.0, "rules": 300.0, "bruteforce": 600.0}
    out = []
    for s in systems:
        for u in users:
            for n in particles:
                for i in range(runs):
                    out.append({"status": "ok", "system": s, "load": u, "swarm_N": n, "run_id": f"{s}-{u}-{n}-{i}", "p95_ms": lat[s] * (1 + 0.05 * u / 10) * float(np.exp(rng.normal(0, 0.05))),
                                "throughput_http": 12.0 * (1 if s == "swarm" else 3) + float(rng.normal(0, 0.3)), "error_rate": 0.0, "t_conv_ms_mean": 100.0 + u + float(rng.normal(0, 1))})
    return out


def test_oe2_http_confirmatory_families_use_only_contrast_loads_and_holm_per_family():
    rng = np.random.default_rng(0)
    recs = _records(rng)
    res = hc.analyze_records("oe2", recs)
    assert set(res["families"]) == {"primary:swarm_vs_decision_table", "auxiliary:swarm_vs_rules", "auxiliary:swarm_vs_bruteforce"}          # sin "secondary": rules y bruteforce son auxiliares
    prim, sec = res["families"]["primary:swarm_vs_decision_table"], res["families"]["auxiliary:swarm_vs_bruteforce"]
    assert prim["confirmatory"] is True and sec["confirmatory"] is False and res["families"]["auxiliary:swarm_vs_rules"]["confirmatory"] is False
    assert prim["method"] == "Holm-Bonferroni" and prim["alpha"] == 0.05 and prim["m"] == 6          # cargas de contraste 1, 10, 25 × {L_resp, throughput}
    assert not any(h.endswith("u50") for h in prim["hypotheses"]) and "u50" in res["stress_regime_descriptive_only"]
    h = prim["hypotheses"]["L_resp_P95_http@u10"]
    assert h["result"]["unit"] == "run" and h["result"]["scale"] == "log" and h["result"]["geometric_ratio"] > 1 and h["p_holm"] >= h["p_raw"]
    assert sec["m"] == 6 and res["comparator_primary"] == "decision_table" and res["auxiliary_contrasts"] == ["rules", "bruteforce"] and res["proposal_system"] == "swarm" and "comparator_secondary" not in res
    assert res["candidate_time_metric"] == "decision_ms" and res["time_metric_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and "time_metric" not in res
    assert res["t_conv_contrast"] == "not_performed_t_conv_is_proposal_only"


def test_paired_log_by_profile_aggregates_replicates_first_and_reports_effective_n():
    rng = np.random.default_rng(1)
    rows = []
    for sysname, scale in (("swarm", 200.0), ("rules", 100.0)):
        for p in range(12):
            for rep in range(10):
                rows.append({"profile_id": f"p{p}", "status": "completed", "package_valid": True, "t_conv_ms": scale * (1 + p / 20) * float(np.exp(rng.normal(0, 0.1))), "replicate": rep})
    a, b = [r for r in rows if r["t_conv_ms"] > 0][:120], rows[120:]
    res = o2.paired_log_by_profile(a, b, "t_conv_ms")
    assert res["n_effective"] == 12 and res["unit"] == "profile" and res["scale"] == "log"          # 120 filas por sistema, n = 12 perfiles
    assert res["geometric_ratio"] == pytest.approx(2.0, rel=0.15) and res["p_value"] < 0.001 and res["test"] in ("student_t_paired", "wilcoxon_signed_rank")
    assert o2.paired_log_by_profile(a[:20], b[:20], "t_conv_ms")["status"] == "not_testable_fewer_than_3_common_profiles"


def test_runs_comparison_never_infers_from_fewer_than_3_runs():
    assert o2.runs_comparison([1.0, 2.0], [1.0, 2.0, 3.0])["status"] == "not_testable_fewer_than_3_runs_per_group"


def test_oe4_http_analysis_separates_regimes_and_estimates_interaction():
    rng = np.random.default_rng(3)
    recs = _records(rng, systems=("swarm",), users=(1, 5, 10, 25, 50, 100), particles=(10, 20, 30), runs=4, lat={"swarm": 500.0})
    for r in recs:
        r["t_conv_ms_mean"] = 100.0 + r["swarm_N"] * 2 + float(rng.normal(0, 1))
    res = hc.analyze_records("oe4", recs)
    assert res["runs_per_cell"] == [4] and res["all_loads_including_stress"]["p95_ms"]["terms"]["load"]["significant"]
    assert "load:swarm_N" in res["contrast_regime_le_25"]["p95_ms"]["terms"]
    assert res["contrast_regime_le_25"]["t_conv_ms_mean"]["terms"]["swarm_N"]["significant"]
    assert res["spearman_load_vs_p95"]["rho"] > 0.5


def test_write_campaign_never_overwrites_and_is_reproducible(tmp_path):
    rng = np.random.default_rng(4)
    recs = _records(rng, systems=("swarm",), users=(1, 10), particles=(10, 20), runs=4)
    prov = {"campaign_id": "C", "experiment": "oe4", "campaign_spec": campaign_spec.identity(), "environment_class": "PILOT", "official": False, "oe2_official": False}
    runs = [{"run_id": r["run_id"]} for r in recs]
    out = tmp_path / "camp"
    hc.write_campaign(out, prov, runs, recs, ["log"])
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["official"] is False and set(manifest["files"]) == {"plan.json", "runs.jsonl", "provenance.json", "analysis.json", "run.log"}
    assert json.loads((out / "analysis.json").read_text()) == json.loads(json.dumps(hc.analyze_records("oe4", recs), default=str))
    with pytest.raises(FileExistsError):
        hc.write_campaign(out, prov, runs, recs, [])


def test_in_process_oe2_analysis_adds_log_paired_family_without_removing_legacy_keys():
    rng = np.random.default_rng(5)
    obs = []
    for s, scale in (("swarm", 200.0), ("decision_table", 100.0), ("rules", 150.0)):
        for p in range(6):
            for rep in range(3):
                v = scale * float(np.exp(rng.normal(0, 0.1))) * (1 + p / 10)
                obs.append({"condition": f"{s}|c1", "f_system": s, "f_concurrency": 1, "profile_id": f"p{p}", "replicate": rep, "batch": 0, "status": "completed", "package_valid": True,
                            "t_conv_ms": v if s == "swarm" else None, "decision_ms": v, "latency_ms": scale, "gap_vs_optimum": 0.0})      # T_conv solo en la propuesta; decision_ms en ambos
    a = oea.analyze("oe2", obs, [])
    assert "comparisons" in a and "oe1_per_run" in a
    fams = a["oe2_families_in_process"]["families"]
    prim = fams["primary:swarm_vs_decision_table"]
    assert prim["m"] == 0 and prim["hypotheses"] == {} and prim["confirmatory"] is True                    # sin L_resp/throughput HTTP en este análisis: la familia confirmatoria queda vacía
    pend = prim["pending_metric_validation"]
    assert pend["status"] == "PENDING_METHODOLOGICAL_VALIDATION" and pend["excluded_from_holm"] is True
    h = pend["hypotheses"]["decision_ms@c1"]
    assert h["confirmatory"] is False and h["p_holm"] is None and h["p_raw"] is not None and h["result"]["metric_validation"] == "PENDING_METHODOLOGICAL_VALIDATION"
    assert h["result"]["n_effective"] == 6 and h["result"]["metric"] == "decision_ms" and h["result"]["geometric_ratio"] > 1       # calculado, pero exploratorio
    assert not any("t_conv" in k.lower() for k in prim["hypotheses"]) and not any("t_conv" in k.lower() for k in pend["hypotheses"])     # no existe contraste de T_conv entre sistemas
    assert fams["auxiliary:swarm_vs_rules"]["confirmatory"] is False
    only_ablation = [r for r in obs if r["f_system"] != "decision_table"]                       # rules NO sustituye al convencional independiente
    fam2 = oea.analyze("oe2", only_ablation, [])["oe2_families_in_process"]["families"]
    assert "pending_metric_validation" not in fam2["primary:swarm_vs_decision_table"] and "decision_ms@c1" in fam2["auxiliary:swarm_vs_rules"]["pending_metric_validation"]["hypotheses"]
    assert "confirmatory_t_conv_log_paired" not in a                                                  # el nombre antiguo sugeria un contraste confirmatorio de T_conv
    legacy = a["comparisons"]["c1|swarm_vs_decision_table"]
    assert legacy["t_conv_ms"]["status"] == "blocked_t_conv_is_proposal_only" and "p_value" not in legacy["t_conv_ms"]       # el análisis legado tampoco contrasta T_conv
    assert legacy["decision_ms"]["metric_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and legacy["decision_ms"]["confirmatory"] is False
