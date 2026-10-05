"""Revisión pre-commit de la Fase B: comprobaciones de COMPORTAMIENTO (no de cadenas) de que T_conv no se contrasta entre sistemas, de que decision_ms es exploratorio y está fuera de Holm, y de que ninguna
salida se presenta como oficial. Cada test falla si el cálculo prohibido se vuelve a invocar aunque el texto de la salida siga diciendo «blocked»."""

import csv
import json

import numpy as np
import pytest

from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import export, http_campaign as hc, oe2_confirmatory as o2, runner, stats_cli

IDS = [f"p{i}" for i in range(100)]


def _oe2_obs(systems=("swarm", "decision_table", "rules"), n_profiles=6):
    rng = np.random.default_rng(3)
    obs = []
    for s, scale in zip(systems, (200.0, 100.0, 150.0)):
        for p in range(n_profiles):
            v = scale * float(np.exp(rng.normal(0, 0.1))) * (1 + p / 10)
            obs.append({"condition": f"{s}|c1", "f_system": s, "f_concurrency": 1, "profile_id": f"p{p}", "replicate": 0, "batch": 0, "status": "completed", "package_valid": True,
                        "t_conv_ms": v if s == "swarm" else None, "decision_ms": v, "latency_ms": scale, "gap_vs_optimum": 0.0})
    return obs


@pytest.mark.requires_library_audio
@pytest.mark.parametrize("system", ["decision_table", "rules", "bruteforce"])
def test_real_conventional_adapters_never_produce_t_conv_but_do_time_their_decision(store, slice_profile, system):
    from adaptation_swarm.baselines.conventional import ConventionalAdapter
    r = ConventionalAdapter(store, system).adapt(slice_profile)                                      # ejecución REAL, no una dataclass armada a mano
    assert r.status == "completed" and r.t_conv_ms is None and 0 < r.decision_ms <= r.total_ms
    row = runner._baseline_row(r)
    assert row["t_conv_ms"] is None and row["decision_ms"] == r.decision_ms and row["k_stop"] is None


def test_legacy_oe2_analysis_never_computes_a_between_system_statistic_on_t_conv(monkeypatch):
    asked = []
    real = oea._paired
    monkeypatch.setattr(oea, "_paired", lambda a, b, m: (asked.append(m), real(a, b, m))[1])
    oea.analyze("oe2", _oe2_obs(), [])
    assert "t_conv_ms" not in asked and {"decision_ms", "latency_ms", "gap_vs_optimum"} <= set(asked)


def test_confirmatory_module_computes_only_decision_ms_and_only_as_pending(monkeypatch):
    asked = []
    real = o2.paired_log_by_profile
    monkeypatch.setattr(o2, "paired_log_by_profile", lambda a, b, m: (asked.append(m), real(a, b, m))[1])
    res = o2.analyze(_oe2_obs(), [])
    assert set(asked) == {"decision_ms"}                                                              # única métrica de tiempo calculada entre sistemas
    prim = res["families"]["primary:swarm_vs_decision_table"]
    assert prim["m"] == 0 and prim["hypotheses"] == {} and prim["pending_metric_validation"]["excluded_from_holm"] is True
    assert all(v["confirmatory"] is False and v["p_holm"] is None for v in prim["pending_metric_validation"]["hypotheses"].values())


def test_stats_cli_oe2_plan_never_asks_for_t_conv_between_systems(monkeypatch):
    rows = list(csv.DictReader(export.statistical_input_csv("s", "oe2", [{**o, "seed": 1, "t_start_utc": "t", "k_stop": 1} for o in _oe2_obs()], []).splitlines()))
    for r in rows:
        r["value"] = float(r["value"])
    meta = {f"{s}|c1": {"system": s, "concurrency": 1} for s in ("swarm", "decision_table", "rules")}
    asked = []
    monkeypatch.setattr(stats_cli, "_unit_means", lambda rows_, cond, metric: (asked.append(metric), {})[1])
    out = stats_cli.plan_oe2(rows, meta, 0.05)
    assert "t_conv_ms" not in asked and {"decision_ms", "latency_ms"} <= set(asked)
    assert out["c1|swarm_vs_decision_table"]["t_conv_ms"]["status"] == "blocked_t_conv_is_proposal_only"
    assert out["c1|swarm_vs_decision_table"]["decision_ms"]["status"] == "not_testable"                  # sin datos no se inventa nada


def test_stats_cli_keeps_t_conv_for_within_proposal_comparisons():
    """OE3/OE4 comparan T_conv DENTRO de la propuesta: ese uso se conserva."""
    import inspect
    assert '"t_conv_ms"' in inspect.getsource(stats_cli.plan_oe3) and '"t_conv_ms"' in inspect.getsource(stats_cli.plan_oe4)


def test_legacy_headline_exposes_no_decision_ms_p_value_as_if_it_were_confirmatory():
    a = oea.analyze("oe2", _oe2_obs(), [])
    assert all(set(v) == {"latency_ms"} for v in a["headline"].values())                              # decision_ms y t_conv_ms fuera del headline
    ex = a["headline_exploratory_pending_metric_validation"]["c1|swarm_vs_decision_table"]["decision_ms"]
    assert ex["confirmatory"] is False and ex["metric_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and ex["p_value"] is not None
    assert a["t_conv_contrast_between_systems"] == "blocked_t_conv_is_proposal_only" and "confirmatory_t_conv_log_paired" not in a


def test_primary_confirmatory_family_contains_only_http_l_resp_and_throughput_and_the_output_is_not_official():
    rng = np.random.default_rng(1)
    recs = [{"status": "ok", "system": s, "load": u, "run_id": f"{s}{u}{i}", "p95_ms": lat * float(np.exp(rng.normal(0, 0.05))), "throughput_http": thr + float(rng.normal(0, 0.3))}
            for s, lat, thr in (("swarm", 900.0, 12.0), ("decision_table", 200.0, 300.0)) for u in (1, 10) for i in range(5)]
    for r in recs:
        r["comparable"] = True
    res = hc.analyze_records("oe2", recs)
    prim = res["families"]["primary:swarm_vs_decision_table"]
    assert {h.split("@")[0] for h in prim["hypotheses"]} == {"L_resp_P95_http", "throughput_http"} and prim["m"] == 4
    assert res["official"] is False and res["oe2_official"] is False and any("contrato de tiempo" in b for b in res["official_blocked_by"])
    assert [f for f in res["families"] if f.startswith("secondary")] == []


def _args(**kw):
    import argparse
    base = dict(experiment="oe2", campaign_id="dry", runs=1, users=[1], particles=[20], systems=list(hc.DEFAULT_OE2_SYSTEMS), warmup=10.0, window=60.0, base_seed=26100501,
                order="randomized-blocks", persist_policy="off", official=False)
    return argparse.Namespace(**{**base, **kw})


def test_every_http_record_and_manifest_declares_oe2_not_official_and_decision_ms_pending(tmp_path):
    runs = hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=list(hc.DEFAULT_OE2_SYSTEMS), order="sequential", campaign_id="R", profile_ids=IDS)
    prov = hc.provenance(_args(), runs)
    assert prov["official"] is False and prov["oe2_official"] is False and prov["time_contract"]["t_conv_equivalence"] == "NOT_ESTABLISHED"
    raw = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])
    recs = hc.execute(runs, prov, warmup=10, window=60, do_run=lambda r, w, win: raw, ensure_server=lambda n: None, log=lambda m: None, profile_ids=IDS)
    assert {r["system"] for r in recs} == {"swarm", "decision_table"}
    for r in recs:
        assert r["official"] is False and r["oe2_official"] is False and r["decision_ms_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and r["persist_policy"] == "off"
        assert r["t_conv_ms_mean"] is None and r["decision_ms_mean"] == pytest.approx(0.1)           # decision_ms no se convierte en t_conv_ms_mean
    out = tmp_path / "c"
    hc.write_campaign(out, prov, runs, recs, [])
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["official"] is False and manifest["oe2_official"] is False
