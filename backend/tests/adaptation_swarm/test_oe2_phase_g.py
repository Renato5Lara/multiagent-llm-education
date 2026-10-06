"""OE2 Fase G: implementación del protocolo cerrado INTERNAMENTE en F.2.3 (A primaria con Welch fijo sobre log, Mann-Whitney complementario, Holm de familia fija m = 8, errores/timeouts como indicadores,
reinicio por corrida, registro de orden, nombre de archivo seguro). Todas son decisiones internas del estudio, NO aprobadas por el asesor. Sin campañas."""

import copy
import hashlib
import inspect
import json
import math
import re

import numpy as np
import pytest
from scipy import stats

from adaptation_swarm.analysis import baseline_bruteforce as bb
from adaptation_swarm.oe import campaign_guards as guards, code_state
from adaptation_swarm.oe import campaign_spec, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, paired_runs as pr

IDS = [f"p{i}" for i in range(100)]
CONTRAST = "swarm_vs_decision_table_contrast"
SW, DT = "swarm", "decision_table"


def _run(system, users, i, p95, thr, **kw):
    r = {"status": "ok", "system": system, "users": users, "load": users, "run_id": f"{system}|u{users}|N20-r{i:02d}", "run_index": i, "batch_id": f"b{i:02d}", "seed": 100 + i, "latency_p95_ms": p95,
         "throughput_rps": thr, "comparable": True, "non_comparable_reason": None, "persist_policy": "off", "comparison_role": CONTRAST, "persistence_condition": "comparison_off",
         "requests_total": 1000, "requests_ok": 1000, "errors": 0, "timeouts": 0}
    r.update(kw)
    return r


def _data(loads=(1, 5, 10, 25), n=6, seed=0, systems=(SW, DT)):
    rng = np.random.default_rng(seed)
    out = []
    for u in loads:
        for i in range(n):
            if SW in systems:
                out.append(_run(SW, u, i, 900.0 * math.exp(rng.normal(0, 0.03)), 17.0 * math.exp(rng.normal(0, 0.02))))
            if DT in systems:
                out.append(_run(DT, u, i, 30.0 * math.exp(rng.normal(0, 0.05)), 350.0 * math.exp(rng.normal(0, 0.02))))
    return out


def _fam(res):
    return res["families"]["primary:swarm_vs_decision_table"]


# ═════════════════ A primaria: Welch t sobre log, fija ═════════════════
def test_the_primary_contrast_is_welch_on_log_for_both_metrics_with_every_requested_field():
    rng = np.random.default_rng(1)
    x, y = 900 * np.exp(rng.normal(0, 0.03, 10)), 30 * np.exp(rng.normal(0, 0.05, 10))
    r = o2.welch_log_comparison(x, y, metric="latency_p95_ms")
    ref = stats.ttest_ind(np.log(x), np.log(y), equal_var=False)
    assert r["test"] == "welch_t" and r["scale"] == "log" and r["alternative"] == "two-sided" and r["test_selection"] == "fixed" and r["unit"] == "run" and r["status"] == "ok"
    assert r["n_runs_swarm"] == r["n_runs_conventional"] == 10 and r["mean_log_swarm"] == pytest.approx(np.log(x).mean()) and r["mean_log_conventional"] == pytest.approx(np.log(y).mean())
    assert r["mean_diff_log"] == pytest.approx(np.log(x).mean() - np.log(y).mean()) and r["geometric_ratio"] == pytest.approx(math.exp(r["mean_diff_log"]))
    assert r["statistic"] == pytest.approx(ref.statistic) and r["p_value"] == pytest.approx(ref.pvalue) and r["df"] == pytest.approx(ref.df)
    lo, hi = ref.confidence_interval(0.95)
    assert r["diff_ci95_log"] == pytest.approx([lo, hi]) and r["geometric_ratio_ci95"] == pytest.approx([math.exp(lo), math.exp(hi)])
    assert r["absolute_descriptive"]["mean_diff_raw"] == pytest.approx(x.mean() - y.mean()) and "complemento DESCRIPTIVO" in r["absolute_descriptive"]["role"]      # la diferencia absoluta NO es el contraste primario
    res = o2.analyze([], _data())
    for h in _fam(res)["hypotheses"].values():
        if h["p_raw"] is not None:
            assert h["result"]["test"] == "welch_t" and h["result"]["scale"] == "log" and h["result"]["alternative"] == "two-sided" and h["p_raw"] == h["result"]["p_value"]


def test_shapiro_is_only_a_diagnostic_and_never_selects_the_test(monkeypatch):
    rng = np.random.default_rng(2)
    x, y = 900 * np.exp(rng.normal(0, 0.03, 10)), 30 * np.exp(rng.normal(0, 0.05, 10))
    results = []
    for p_shapiro in (0.0, 1.0):                                                                             # «muy no normal» y «perfectamente normal»
        monkeypatch.setattr(stats, "shapiro", lambda v, p=p_shapiro: type("S", (), {"pvalue": p, "statistic": 1.0})())
        results.append(o2.welch_log_comparison(x, y))
    assert results[0]["test"] == results[1]["test"] == "welch_t" and results[0]["p_value"] == results[1]["p_value"]
    assert results[0]["normality_diagnostic"]["used_for_selection"] is False and results[0]["normality_diagnostic"]["shapiro_p_swarm"] == 0.0 and results[1]["normality_diagnostic"]["shapiro_p_swarm"] == 1.0
    skewed = np.concatenate([np.full(9, 100.0), [10_000.0]])                                                # distribución claramente asimétrica: tampoco cambia la prueba
    assert o2.welch_log_comparison(skewed, np.full(10, 5.0) * (1 + 0.01 * np.arange(10)))["test"] == "welch_t"
    src = inspect.getsource(o2.welch_log_comparison) + inspect.getsource(o2.primary_hypothesis) + inspect.getsource(o2.holm_fixed_family)
    assert "mannwhitneyu" not in src.split("normality_diagnostic")[0] and "if diag" not in src


def test_degenerate_inputs_of_the_primary_contrast_are_not_testable_never_a_p_value():
    assert o2.welch_log_comparison([1.0, 2.0], [1.0, 2.0, 3.0])["status"] == "not_testable_fewer_than_3_runs_per_group"
    assert o2.welch_log_comparison([1.0, 0.0, 2.0], [1.0, 2.0, 3.0])["status"] == "not_testable_non_positive_values"
    assert o2.welch_log_comparison([5.0, 5.0, 5.0], [7.0, 7.0, 7.0])["status"] == "undefined_zero_variance"
    assert all(o2.welch_log_comparison(a, b)["p_value"] is None for a, b in (([1.0, 2.0], [1.0, 2.0, 3.0]), ([5.0] * 3, [7.0] * 3)))


# ═════════════════ Mann-Whitney complementario ═════════════════
def test_mann_whitney_is_a_complementary_analysis_outside_holm_that_never_changes_the_primary_result(monkeypatch):
    res = o2.analyze([], _data(seed=3))
    h = _fam(res)["hypotheses"]["L_resp_P95_http@u10"]
    comp = h["result"]["mann_whitney_companion"]
    assert comp["test"] == "mann_whitney_u" and comp["role"] == "complementary_predeclared" and comp["in_holm"] is False and comp["selects_primary"] is False and comp["status"] == "ok"
    assert h["p_raw"] == h["result"]["p_value"] and h["p_raw"] != comp["p_value"]                         # el p de Holm es el de Welch, no el del complemento
    base = {k: (v["p_raw"], v["p_holm"]) for k, v in _fam(res)["hypotheses"].items()}
    monkeypatch.setattr(o2, "mann_whitney_companion", lambda a, b: {"p_value": 0.5, "status": "ok", "in_holm": False})
    again = {k: (v["p_raw"], v["p_holm"]) for k, v in _fam(o2.analyze([], _data(seed=3)))["hypotheses"].items()}
    assert again == base                                                                                  # cambiar el complemento no mueve ningún resultado primario ni de Holm
    monkeypatch.undo()
    monkeypatch.setattr(stats, "shapiro", lambda v: (_ for _ in ()).throw(RuntimeError("Shapiro no debe ser necesario")))
    assert o2.mann_whitney_companion([1.0, 2.0, 3.0, 4.0], [10.0, 11.0, 12.0, 13.0])["status"] == "ok"      # se ejecuta SIN Shapiro


# ═════════════════ Holm: familia fija m = 8 ═════════════════
def test_holm_uses_a_fixed_m_of_eight_and_never_the_number_of_observed_p_values():
    assert campaign_spec.HOLM_M == 8 and campaign_spec.HOLM_LOADS == (1, 5, 10, 25) and len(campaign_spec.HOLM_HYPOTHESES) == 8
    h = {n: {"p_value": p} for n, p in zip(campaign_spec.HOLM_HYPOTHESES, (0.001, 0.01, 0.02))}
    fam = o2.holm_fixed_family("t", h, m=8, expected=campaign_spec.HOLM_HYPOTHESES)
    adj = sorted(v["p_holm"] for v in fam["hypotheses"].values() if v["p_holm"] is not None)
    assert fam["m"] == 8 and fam["m_fixed"] is True and fam["n_tested"] == 3 and adj == pytest.approx([0.008, 0.07, 0.12])                  # factores 8, 7, 6 (no 3, 2, 1)
    dyn = o2.holm_family("d", {n: {"p_value": p} for n, p in zip(campaign_spec.HOLM_HYPOTHESES, (0.001, 0.01, 0.02))})
    assert sorted(v["p_holm"] for v in dyn["hypotheses"].values() if v["p_holm"] is not None) == pytest.approx([0.003, 0.02, 0.02]) and dyn["m"] == 3   # el modo dinámico daría otra cosa
    with pytest.raises(ValueError, match="la familia es fija"):
        o2.holm_fixed_family("t", h, m=5, expected=campaign_spec.HOLM_HYPOTHESES)
    for subset in ((1,), (1, 10), (1, 5, 10, 25)):
        assert _fam(o2.analyze([], _data(loads=subset)))["m"] == 8                                       # con cualquier subconjunto de cargas con datos, m = 8


def test_untested_hypotheses_are_recorded_with_their_reason_and_still_count_in_m():
    res = o2.analyze([], _data(loads=(1, 10, 25)))                                                       # la carga 5 no tiene datos
    fam = _fam(res)
    assert fam["n_tested"] == 6 and fam["not_tested"] == ["L_resp_P95_http@u5", "throughput_http@u5"] and fam["m"] == 8
    r = fam["hypotheses"]["throughput_http@u5"]
    assert r["p_raw"] is None and r["p_holm"] is None and r["significant_holm"] is None and r["result"]["status"] == "not_tested"       # no se inventa un p-valor
    recs = _data(loads=(1, 5, 10, 25))
    for r_ in recs:
        if r_["users"] == 10 and r_["system"] == DT and r_["run_index"] == 0:
            r_["comparable"], r_["non_comparable_reason"] = False, "generator_saturated"
    lim = _fam(o2.analyze([], recs))
    assert lim["m"] == 8 and lim["n_tested"] == 6 and all(lim["hypotheses"][f"{m}@u10"]["result"]["reason"].startswith("generator_limited_level") for m in campaign_spec.HOLM_METRICS)


def test_the_holm_family_excludes_ttfc_t_conv_the_on_condition_loads_50_100_and_the_auxiliary_systems():
    recs = _data(loads=(1, 5, 10, 25, 50, 100), n=4)
    recs += [_run(SW, 10, i, 4000.0, 9.0, persist_policy="on", comparison_role=campaign_spec.ROLE_PROPOSAL_COST, run_id=f"on{i}") for i in range(4)]
    recs += [_run("rules", 10, i, 100.0, 100.0, comparison_role=campaign_spec.ROLE_AUXILIARY, run_id=f"rules{i}") for i in range(4)]
    res = o2.analyze([], recs)
    fam = _fam(res)
    assert set(fam["hypotheses"]) == set(campaign_spec.HOLM_HYPOTHESES) and fam["outside_fixed_family"] == []                  # exactamente las 8
    assert "u50" in res["stress_regime_descriptive_only"] and "u100" in res["stress_regime_descriptive_only"] and not any(h.endswith(("u50", "u100")) for h in fam["hypotheses"])
    assert res["n_http_runs_proposal_cost"] == 4 and all("persON" not in k and "on" not in k.split("@")[0] for k in fam["hypotheses"])
    assert not any("time_to_final" in k or "t_conv" in k.lower() or "decision_ms" in k for k in fam["hypotheses"]) and res["t_conv_contrast"] == "not_performed_t_conv_is_proposal_only"
    assert res["families"]["auxiliary:swarm_vs_rules"]["confirmatory"] is False and set(res["families"]) == {"primary:swarm_vs_decision_table", "auxiliary:swarm_vs_rules", "auxiliary:swarm_vs_bruteforce"}
    odd = o2.analyze([], _data(loads=(1, 3), n=4))                                                       # una carga fuera de la familia fija se lista aparte y no cuenta
    assert _fam(odd)["outside_fixed_family"] == ["L_resp_P95_http@u3", "throughput_http@u3"] and _fam(odd)["m"] == 8
    assert campaign_spec.SPEC["oe2"]["holm_design"]["advisor_backing"] == "NONE" and campaign_spec.SPEC["oe2"]["holm_design"]["source"] == "internal_decision_F2.3"


# ═════════════════ errores y timeouts ═════════════════
def test_errors_and_timeouts_are_counted_and_reported_but_never_invalidate_a_run():
    recs = _data(loads=(10,), n=6)
    for r in recs:
        if r["system"] == SW and r["run_index"] in (0, 1):
            r.update(requests_total=1000, requests_ok=950, errors=50, timeouts=20)                       # `errors` cuenta TODOS los fallos (incluye timeouts), como en `summarize_run`
    res = o2.analyze([], recs)
    assert _fam(res)["hypotheses"]["L_resp_P95_http@u10"]["result"]["n_runs_swarm"] == 6                  # ninguna corrida se descarta por tasa de error
    cell = res["error_report"]["cells"]["swarm|u10"]
    assert cell["n_runs"] == 6 and cell["total_requests"] == 6000 and cell["successful_requests"] == 5900 and cell["timeouts"] == 40 and cell["errors"] == 60
    assert cell["error_rate"] == pytest.approx(60 / 6000) and cell["timeout_rate"] == pytest.approx(40 / 6000) and cell["total_failure_rate"] == pytest.approx(100 / 6000)
    assert len(cell["latency_p95_successful_ms"]) == 6 and len(cell["throughput_successful_rps"]) == 6 and res["error_report"]["cells"]["decision_table|u10"]["total_failure_rate"] == 0
    assert res["error_report"]["warnings"] and res["error_report"]["warnings"][0]["users"] == 10 and "DIFIEREN" in res["error_report"]["warnings"][0]["message"]
    assert res["error_report"]["validity_threshold"] == "NONE" and res["n_http_runs_not_comparable"] == 0 and res["runs_not_analyzable"] == []
    clean = o2.analyze([], _data(loads=(10,), n=6))
    assert clean["error_report"]["warnings"] == []                                                       # sin diferencias no hay advertencia
    src = inspect.getsource(o2.failure_report)
    assert not re.search(r"0\.01\b|1 ?%|RNF04", src.split('"definition"')[0]) and campaign_spec.SPEC["oe2"]["error_reporting"]["validity_threshold"].startswith("NONE")      # sin umbral numérico nuevo


def test_a_run_without_successful_responses_is_not_analyzable_not_imputed_and_listed():
    recs = _data(loads=(10,), n=6)
    victim = next(r for r in recs if r["system"] == SW and r["run_index"] == 2)
    victim.update(requests_ok=0, latency_p95_ms=None, throughput_rps=0.0, errors=1000)
    res = o2.analyze([], recs)
    assert [x["run_id"] for x in res["runs_not_analyzable"]] == [victim["run_id"]] and _fam(res)["hypotheses"]["L_resp_P95_http@u10"]["result"]["n_runs_swarm"] == 5      # sale del contraste, sin imputar
    assert res["error_report"]["cells"]["swarm|u10"]["total_failure_rate"] > 0.15 and res["error_report"]["cells"]["swarm|u10"]["per_run"][2]["analyzable"] is False
    allbad = _data(loads=(10,), n=6)
    for r in allbad:
        if r["system"] == SW:
            r.update(requests_ok=0, latency_p95_ms=None, throughput_rps=0.0, errors=1000)
    f2 = _fam(o2.analyze([], allbad))
    assert f2["hypotheses"]["L_resp_P95_http@u10"]["p_raw"] is None and f2["m"] == 8 and f2["n_tested"] == 0                  # nada que comparar: no testada, no inventada


def test_per_run_records_keep_the_failure_indicators_and_the_legacy_error_rate_means_total_failures():
    summary = {"status": "ok", "requests_total": 1000, "requests_ok": 940, "errors": 60, "timeouts": 10, "errors_non_timeout": 50, "latency_p95_ms": 321.0, "throughput_rps": 12.0, "error_rate": 0.06}
    run = {"run_id": "s", "batch_id": "b", "run_index": 0, "seed": 1, "system": "swarm", "load": 1, "swarm_N": 20, "system_role": "proposal", "persist_policy": "off", "profile_sequence_sha256": "x",
           "persistence_condition": "comparison_off", "comparison_role": CONTRAST, "confirmatory_role": "x"}
    prov = {"campaign_id": "s", "campaign_spec": {"sha256": "x"}, "code": {}, "hardware": {}, "definition_version": {}, "environment_class": "PILOT", "official": False, "oe2_official": False, "client_timeout_s": 30.0}
    r = hc.record(run, summary, prov)
    assert (r["total_requests"], r["successful_requests"], r["errors"], r["timeouts"], r["non_timeout_errors"]) == (1000, 940, 60, 10, 50)
    assert r["timeout_rate"] == 0.01 and r["total_failure_rate"] == 0.06 and r["non_timeout_error_rate"] == 0.05 and r["error_rate"] == 0.06                  # `error_rate` heredado = fallos totales / peticiones
    assert r["latency_p95_successful_ms"] == 321.0 and r["throughput_successful_rps"] == 12.0 and not hc.missing_run_fields()


# ═════════════════ cold_per_run ═════════════════
class _FakeProc:
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        pass


def _fake_http(monkeypatch):
    import urllib.request

    class Resp:
        def __init__(self, b):
            self.b = b

        def read(self):
            return self.b
    state = {"policy": "off"}
    monkeypatch.setattr(hc.subprocess, "Popen", lambda cmd, env=None, **kw: (state.update(policy="off" if env["SWARM_API_PERSIST"] == "0" else "on"), _FakeProc())[1])
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: Resp(json.dumps({"persist_policy": state["policy"], "baseline_quality_in_request": False, "library_version": "v"}).encode()))
    monkeypatch.setattr(hc, "_port_free", lambda port: True)


def test_cold_per_run_restarts_the_server_before_every_run_and_verifies_zero_runs_served(monkeypatch):
    _fake_http(monkeypatch)
    server = hc.ServerPerN("python", 8999, "k")
    ensure = hc.make_ensure_server(server, "cold_per_run")
    seq = [ensure(20, "off") for _ in range(5)]
    assert [(h["server_instance"], h["server_restarted_before_run"], h["server_runs_served_before"]) for h in seq] == [(i, True, 0) for i in range(1, 6)]            # 5 corridas = 5 servidores nuevos
    reuse = hc.make_ensure_server(hc.ServerPerN("python", 8998, "k"), "reuse")
    r = [reuse(20, "off") for _ in range(3)]
    assert [(h["server_instance"], h["server_restarted_before_run"], h["server_runs_served_before"]) for h in r] == [(1, True, 0), (1, False, 1), (1, False, 2)]    # la política reuse no reinicia
    with pytest.raises(ValueError, match="política de servidor desconocida"):
        hc.make_ensure_server(server, "warm")


def test_cold_per_run_cleans_the_campaign_state_between_termination_and_start_and_fails_closed(monkeypatch):
    _fake_http(monkeypatch)
    order = []

    class Spy(hc.ServerPerN):
        def stop(self):
            order.append("stop")
            super().stop()

        def ensure(self, n, persist="off"):
            order.append("ensure")
            return super().ensure(n, persist)
    server = Spy("python", 8999, "k")
    health = hc.make_ensure_server(server, "cold_per_run", clean=lambda: (order.append("clean"), {"per_cycle_keys_deleted": 7})[1])(20, "off")
    assert order.index("stop") < order.index("clean") < order.index("ensure") and health["pre_restart_clean"] == {"per_cycle_keys_deleted": 7}      # detener → limpiar → iniciar
    monkeypatch.setattr(hc, "_port_free", lambda port: False)                                              # el servidor anterior no terminó
    with pytest.raises(RuntimeError, match="sigue escuchando"):
        hc.make_ensure_server(Spy("python", 8999, "k"), "cold_per_run", wait_s=0.4)(20, "off")

    class Liar:                                                                                           # un servidor que dice no haberse reiniciado
        port, proc = 1, None

        def stop(self):
            pass

        def ensure(self, n, persist):
            return {"server_restarted_before_run": False, "server_runs_served_before": 3}
    monkeypatch.setattr(hc, "_port_free", lambda port: True)
    with pytest.raises(RuntimeError, match="cold_per_run no se cumplió"):
        hc.make_ensure_server(Liar(), "cold_per_run")(20, "off")


def test_oe2_defaults_to_cold_per_run_planned_starts_equal_runs_and_a_reused_server_is_not_official():
    assert hc.default_server_policy("oe2") == "cold_per_run" and hc.default_server_policy("oe4") == "reuse"
    runs = hc.plan("oe2", runs=3, base_seed=1, users=[1, 10], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="C", profile_ids=IDS)
    assert hc.planned_server_starts(runs, "cold_per_run") == len(runs) == 12 and hc.planned_server_starts(runs) < 12
    import argparse
    mk = lambda **kw: hc.provenance(argparse.Namespace(**{**dict(experiment="oe2", campaign_id="C", runs=3, users=[1, 10], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1,
                                                                 order="randomized-blocks", persist_policy="off", official=False), **kw}), runs)
    cold, reuse = mk(), mk(server_policy="reuse")
    assert cold["cold_warm"]["policy"] == "cold_per_run" and cold["cold_warm"]["planned_server_starts"] == 12 and cold["cold_warm"]["statement"] == campaign_spec.COLD_PER_RUN_STATEMENT and cold["cold_warm"]["universal_claim"] is False
    assert reuse["cold_warm"]["policy"] == "reuse" and not any("cold_per_run" in r and "servidor:" in r for r in cold["official_refusals"]) and any("servidor:" in r and "cold_per_run" in r for r in reuse["official_refusals"])
    assert "más representativo" not in json.dumps(campaign_spec.SPEC["oe2"]["server_policy"]) and campaign_spec.SPEC["oe2"]["server_policy"]["universal_claim"] is False


def test_the_cli_accepts_the_server_policy_and_the_dry_run_shows_it(capsys, tmp_path):
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(tmp_path / "x"), "--runs", "2", "--users", "1", "--dry-run"])
    d = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert d["cold_warm"]["policy"] == "cold_per_run" and d["cold_warm"]["planned_server_starts"] == 4
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(tmp_path / "y"), "--runs", "2", "--users", "1", "--server-policy", "reuse", "--dry-run"])
    d2 = json.loads(capsys.readouterr().out.split("\n", 1)[1])
    assert d2["cold_warm"]["policy"] == "reuse" and d2["cold_warm"]["planned_server_starts"] == 1 and any("servidor:" in r for r in d2["official_refusals"]) and not (tmp_path / "x").exists()


# ═════════════════ randomized-blocks y registro del orden ═════════════════
def test_randomized_blocks_keeps_the_same_seed_and_sequence_per_round_and_load_while_randomizing_the_order():
    runs = hc.plan("oe2", runs=10, base_seed=26100501, users=[10, 25], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="C", profile_ids=IDS)
    for i in range(10):
        for u in (10, 25):
            pair = [r for r in runs if r["run_index"] == i and r["load"] == u]
            assert len(pair) == 2 and len({r["seed"] for r in pair}) == 1 and len({r["profile_sequence_sha256"] for r in pair}) == 1 and len({r["batch_id"] for r in pair}) == 1
    firsts = {(r["run_index"], r["load"]): r["system"] for r in reversed(runs)}
    assert set(firsts.values()) == {"swarm", "decision_table"}                                              # el orden dentro de los pares no es siempre el mismo
    again = hc.plan("oe2", runs=10, base_seed=26100501, users=[10, 25], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="C", profile_ids=IDS)
    assert [r["run_id"] for r in runs] == [r["run_id"] for r in again]                                      # determinista


def test_execute_records_execution_index_started_utc_first_system_and_the_restart_per_run(monkeypatch):
    runs = hc.plan("oe2", runs=3, base_seed=5, users=[10], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="C", profile_ids=IDS)
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT", "official": False, "oe2_official": False}
    raw = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])
    _fake_http(monkeypatch)
    server = hc.ServerPerN("python", 8999, "k")
    recs = hc.execute(runs, prov, warmup=10, window=60, log=lambda m: None, profile_ids=IDS, do_run=lambda r, w, win: raw, ensure_server=hc.make_ensure_server(server, "cold_per_run"))
    assert [r["execution_index"] for r in recs] == [1, 2, 3, 4, 5, 6] and all(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00", r["started_utc"]) for r in recs)
    assert all(r["server_restarted_before_run"] is True and r["server_runs_served_before"] == 0 for r in recs) and len({r["server_instance"] for r in recs}) == 6
    for r in recs:
        pair = [x for x in recs if x["run_index"] == r["run_index"]]
        assert r["pair_first_system"] == min(pair, key=lambda x: x["execution_index"])["system"]
    assert not hc.missing_run_fields() and {"started_utc", "pair_first_system"} <= set(guards.REQUIRED_RUN_FIELDS)


# ═════════════════ A y B ═════════════════
def test_a_neither_imports_nor_activates_b_and_b_does_not_change_a():
    import ast
    for mod in (o2, hc):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(mod))):
            if isinstance(node, ast.Import):
                names |= {a_.name for a_ in node.names}
            elif isinstance(node, ast.ImportFrom):
                names |= {node.module or ""} | {f"{node.module}.{a_.name}" for a_ in node.names}
        assert not any("paired_runs" in n for n in names), mod.__name__                                    # A no importa B (la docstring puede mencionarla)
    recs = _data(loads=(1, 10), n=8, seed=5)
    before = json.dumps(o2.analyze([], copy.deepcopy(recs)), sort_keys=True, default=str)
    full = [{**r, "batch_id": f"b{r['run_index']}", "seed": 7, "profile_sequence_sha256": f"h{r['run_index']}{r['users']}"} for r in recs]
    pr.paired_contrast(full, scale="log", test="wilcoxon")
    assert json.dumps(o2.analyze([], copy.deepcopy(recs)), sort_keys=True, default=str) == before
    assert pr.STATUS == "IMPLEMENTED_TECHNICALLY_NOT_METHODOLOGICALLY_APPROVED" and "paired" not in json.dumps(_fam(o2.analyze([], recs))["hypotheses"])


# ═════════════════ decisiones internas ≠ aprobadas por el asesor; guards ═════════════════
def test_internal_decisions_are_differentiated_from_advisor_approved_ones_and_recorded_in_the_provenance():
    dec = campaign_spec.SPEC["oe2"]["methodological_decisions"]
    internal = sorted(k for k, d in dec.items() if d["status"] == "DECIDED")
    assert internal == ["cold_warm_policy", "common_indicator_asymmetry", "errors_timeouts_in_l_resp", "execution_order", "holm_family_size", "http_pairing"]
    assert {dec[k]["chosen"] for k in internal} == {"cold_per_run", "keep_documented", "separate_indicators", "randomized_blocks", "fixed_m_declared_before_data", "independent_runs"}
    for k, d in dec.items():
        assert d["advisor_approved"] is False and d["question_source"]                                      # ninguna está aprobada por el asesor; el origen de la pregunta se conserva
        assert d["decision_level"] == ("INTERNAL_STUDY_DECISION" if k in internal else "REQUIERE_RESPALDO_DEL_ASESOR")
        assert (d["source"] == "internal_decision_F2.3") == (k in internal)
    for k in ("latency_statistic", "l_resp_literal_hypothesis_h1"):
        assert dec[k]["status"] == "PENDING" and dec[k]["chosen"] is None
    assert "ADVISOR_APPROVED" not in {d["status"] for d in dec.values()} and campaign_spec.SPEC["advisor_approved"] is False
    import argparse
    runs = hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="C", profile_ids=IDS)
    prov = hc.provenance(argparse.Namespace(experiment="oe2", campaign_id="C", runs=1, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                                            persist_policy="off", official=False), runs)
    assert prov["internal_decisions_not_advisor_approved"] == internal and prov["analysis_primary"]["status"] == "INTERNAL_STUDY_DECISION_NOT_ADVISOR_APPROVED" and prov["holm_design"]["m_fixed"] == 8
    ap = campaign_spec.SPEC["oe2"]["analysis_primary"]
    assert ap["test"] == "welch_t" and ap["scale"] == "log" and "NUNCA selecciona" in ap["test_selection"] and "advisor" not in ap["status"].lower().replace("not_advisor", "")


def test_b1_b5_b13_and_p6_remain_blocked_and_pend_keeps_blocking_while_advisor_decisions_exist():
    crit = {b.id: b for b in guards.evaluate(None) if b.critical}
    assert {"B1", "B5", "B13", "PEND", "DEF"} <= set(crit) and all(crit[k].frozen for k in ("B1", "B5", "B13", "PEND"))
    assert guards.pending_methodological_decisions() == ["l_resp_literal_hypothesis_h1", "latency_statistic"]
    refusals = " | ".join(hc.official_refusals({"vcpu": 20, "ram_gib": 31.75}, 10, 10.0, 60.0, None))
    assert all(f"[{k}]" in refusals for k in ("B1", "B5", "B13", "PEND", "DEF"))
    assert bb.TARGET_HARDWARE == {"vcpu": 8, "ram_gib": 32.0} and bb.TARGET_RAM_FRACTION == 0.9 and bb.meets_target({"vcpu": 20, "ram_gib": 31.75}) is True              # P6: la condición técnica no se reinterpretó ni se resolvió
    assert campaign_spec.SPEC["oe2"]["comparator_scope_validation"]["status"] != "VALIDATED" and campaign_spec.SPEC["oe2"]["persist_policy"]["status"].startswith("FROZEN_PROVISIONAL")


# ═════════════════ bug de Windows: `|` en el nombre del archivo crudo ═════════════════
_FORBIDDEN = set('<>:"/\\|?*')


def test_raw_filenames_are_windows_safe_injective_and_the_logical_run_id_is_recoverable(tmp_path):
    ids = ["swarm|u10|N20-r00", "decision_table|u25|N20|persON-r09", "a%7Cb", "a|b", "a_b", "a:b", 'q"x', "ñandú|u1", "x%", "x%25", "a b", "C-swarm|u1|N20-r00", "C-swarm_u1_N20-r00"]
    names = [hc.raw_filename(i) for i in ids]
    assert len(set(names)) == len(ids)                                                                      # sin colisiones entre run_id distintos (también `a|b` vs `a_b` y `%`)
    for i, n in zip(ids, names):
        assert not (set(n) & _FORBIDDEN) and n.endswith(".csv") and hc.run_id_from_filename(n) == i
        (tmp_path / n).write_text("x", encoding="utf-8")                                                  # el sistema de archivos lo acepta (en Windows también)
    assert hc.raw_filename("swarm|u10|N20-r00") == "swarm%7Cu10%7CN20-r00.csv" and hc.raw_filename("plain-run.01_ok") == "plain-run.01_ok.csv"
    assert len(list(tmp_path.iterdir())) == len(ids)


def test_the_locust_runner_writes_the_raw_log_under_the_safe_name_and_the_record_keeps_the_logical_run_id(monkeypatch, tmp_path):
    seen = {}

    def fake_run(cmd, env=None, **kw):
        path = env["SWARM_LOAD_RAW_CSV"]
        seen["path"] = path
        with open(path, "w", encoding="utf-8", newline="") as fh:                                           # crea de verdad el archivo con el nombre que el runner eligió
            fh.write("t_end_epoch_s,response_ms,ok,timeout,t_conv_ms,k_stop,metrics_ok,decision_ms,profile_id,user_index,seq_pos,error_kind\n1000.0,5.0,1,0,,,1,0.1,p1,0,0,\n")
        with open(path + ".cpu.csv", "w", encoding="utf-8", newline="") as fh:
            fh.write("t_epoch_s,loadgen_cpu_percent\n1000.0,10.0\n")
    with monkeypatch.context() as m:
        m.setattr(hc.subprocess, "run", fake_run)
        run = hc.locust_runner("http://localhost:1", tmp_path / "locustfile.py", tmp_path / "plugin.py", tmp_path, "python")
        raw, cpu = run({"run_id": "swarm|u10|N20-r00", "seed": 1, "system": "swarm", "load": 10}, 10.0, 60.0)
    name = seen["path"].replace("\\", "/").rsplit("/", 1)[-1]
    assert name == "swarm%7Cu10%7CN20-r00.csv" and not (set(name) & _FORBIDDEN) and len(raw) == 1 and raw[0]["profile_id"] == "p1" and len(cpu) == 1
    runs = hc.plan("oe2", runs=1, base_seed=1, users=[10], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="C", profile_ids=IDS)
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT", "official": False, "oe2_official": False}
    rawrows = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])
    recs = hc.execute(runs, prov, warmup=10, window=60, log=lambda m: None, profile_ids=IDS, do_run=lambda r, w, win: rawrows, ensure_server=lambda n, p: None)
    assert [r["run_id"] for r in recs] == [r["run_id"] for r in runs] and all("|" in r["run_id"] for r in recs)                  # el run_id lógico conserva el `|`


# ═════════════════ verificación final de Git: la salida de la propia campaña no cuenta como cambio de código ═════════════════
def test_the_final_git_check_ignores_only_the_campaign_own_output_and_still_detects_any_other_change(tmp_path):
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    git = lambda *a: subprocess.run(["git", *a], cwd=repo, check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    git("add", "a.py")
    git("commit", "-q", "-m", "init")
    start = code_state.git_state(repo)
    assert start["dirty"] is False and start["files_sha256"] is not None
    fp = code_state.source_fingerprints()
    out, raw = repo / "experiments" / "camp", repo / "experiments" / "camp.tmp-raw"
    raw.mkdir(parents=True)
    (raw / "r.csv").write_text("1", encoding="utf-8")
    out.mkdir()
    (out / "runs.jsonl").write_text("{}", encoding="utf-8")                                                # lo que escribe la campaña
    prov = {"code_state": start, "campaign_source_fingerprints": fp}
    code_state.final_code_state(prov, repo, ignore_paths=(out, raw))
    assert prov["code_state_final"]["unchanged_since_start"] is True and code_state.completion_gaps(prov) == []
    prov_no_ignore = {"code_state": start, "campaign_source_fingerprints": fp}
    code_state.final_code_state(prov_no_ignore, repo)
    assert prov_no_ignore["code_state_final"]["unchanged_since_start"] is False                            # sin excluirla, su propia salida parecería un cambio
    (repo / "a.py").write_text("x = 2\n", encoding="utf-8")                                                  # un cambio de código SÍ cuenta
    prov_changed = {"code_state": start, "campaign_source_fingerprints": fp}
    code_state.final_code_state(prov_changed, repo, ignore_paths=(out, raw))
    assert prov_changed["code_state_final"]["unchanged_since_start"] is False
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "otro.txt").write_text("nuevo", encoding="utf-8")                                              # un archivo ajeno nuevo también
    prov_extra = {"code_state": start, "campaign_source_fingerprints": fp}
    code_state.final_code_state(prov_extra, repo, ignore_paths=(out, raw))
    assert prov_extra["code_state_final"]["unchanged_since_start"] is False
