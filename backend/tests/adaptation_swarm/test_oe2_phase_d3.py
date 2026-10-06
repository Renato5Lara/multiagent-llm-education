"""OE2 Fase D.3: infraestructura de las decisiones congeladas B1-B (indicador común `time_to_final_config_ms`), B5-C (persistencia OFF común + ON de la propuesta), B13-A (alcance = decision_table) y la
dependencia por objetivo del guard DEF. Todas las decisiones son PROVISIONALES (no aprobadas por el asesor): no se redefine T_conv, ni L_resp, ni OE2. Sin campañas."""

import hashlib
import inspect
import uuid

import numpy as np
import pytest

from adaptation_swarm.agents.ag0_swarm_orchestrator import CycleResult, SwarmOrchestrator
from adaptation_swarm.baselines import conventional
from adaptation_swarm.baselines.conventional import ConventionalAdapter
from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import campaign_guards as guards
from adaptation_swarm.oe import campaign_spec, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, runner, time_contract
from adaptation_swarm.oe import definitions as defs
from adaptation_swarm.stack import SwarmStack

IDS = [f"p{i}" for i in range(100)]
TTFC = "time_to_final_config_ms"
CONTRAST = "swarm_vs_decision_table_contrast"


# ═════════════════════════ P1 — AG0: observabilidad ADITIVA, T_conv intacto ═════════════════════════
# SHA-256 del código fuente de los pasos de AG0 en HEAD (d2c094a) —verificado idéntico al de este árbol—: cualquier cambio de un paso (PSO, convergencia, T_conv, bus, broadcast) rompe este test.
AG0_STEP_SHA256 = {
    "step_receive": "4c2f48e7e27343444de48fd0f65ab0f94848d79d1d5d02702fda3e8133479357", "step_profile": "c8ea95af854c9066d55891c7aa08b3f34ebe30a192164d3460ff3e3bf0d9a196",
    "step_seed": "810755d083be58c99caba2c5c68e28d3ac97c813519b9dab9e21b2f3e601ccbc", "_realize": "1768389556ab4e00bff39fe0057537b078a045d2a220aeb0d7b8d613c415d0ab",
    "_scores": "3dc5641572b15084d40dda8eeb0a30e7732dbe7614ad1056abe345eee3792566", "step_evaluate": "4b6f379bc09d1c764523517bb5d51a51bd0df4915188401bddb3600e9fd36398",
    "route_after_evaluate": "5fbe095342def1889badcaebcb2a0fa0368f25585ed04dd4a8bd8d82a8cc23f2", "step_advance": "e80a18c8007c58946b2a0baef40537701d12fd15f238519d9a229208834fc0e2",
    "step_finalize": "908001a66e309647fe07f6abd3530ca5e720889d505f5bcdcb465a345b0ed8a7", "step_fail": "503451c44c7fd4cb87150e82cf1026ca2cce2a42ea3b52c7cc8a550472de68df",
    "step_persist": "8e9f53d6f02110128585d93725f16d172c66da058c502bea1ce4a0d487b73689",
}


@pytest.mark.parametrize("step", sorted(AG0_STEP_SHA256))
def test_no_ag0_step_changed_so_t_conv_pso_convergence_bus_and_broadcast_are_untouched(step):
    src = inspect.getsource(getattr(SwarmOrchestrator, step)).rstrip("\n")
    assert hashlib.sha256(src.encode("utf-8")).hexdigest() == AG0_STEP_SHA256[step]


def test_t_conv_ms_is_still_computed_exactly_as_before_and_total_ms_is_independent():
    fin = inspect.getsource(SwarmOrchestrator.step_finalize)
    assert 't_conv_ms = (time.perf_counter_ns() - st["t_search_ns"]) / 1e6' in fin                       # misma frontera: reloj desde el final de step_seed hasta la entrada de step_finalize
    assert 'st["t_search_ns"]' in inspect.getsource(SwarmOrchestrator.step_seed) or '"t_search_ns": time.perf_counter_ns()' in inspect.getsource(SwarmOrchestrator.step_seed)
    run = inspect.getsource(SwarmOrchestrator.run_cycle)
    assert "total_ms = (time.perf_counter() - t0) * 1000.0" in run and run.count("t_conv_ms=final.get(\"t_conv_ms\")") == 2          # lo que AG0 mide se propaga sin recalcular


def test_cycle_result_exposes_the_two_existing_timestamps_additively():
    fields = {f.name: f for f in CycleResult.__dataclass_fields__.values()}
    assert fields["t_start_ns"].default is None and fields["t_search_ns"].default is None               # aditivo: opcionales, no rompen constructores existentes
    r = CycleResult(cycle_id="c", correlation_id="x", profile_id="p", concept_id="k", status="completed", stop_reason="epsilon", k_stop=1, t_conv_ms=5.0, total_ms=9.0, seed=1, config_hash="h", library_version="v",
                    t_start_ns=100, t_search_ns=2_000_100)
    d = r.to_dict()
    assert d["t_start_ns"] == 100 and d["t_search_ns"] == 2_000_100 and d["t_conv_ms"] == 5.0 and d["total_ms"] == 9.0


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_real_cycle_exposes_ordered_timestamps_and_the_new_indicator_rebuilds_from_them_without_touching_t_conv(store, slice_profile):
    async with SwarmStack(library_version=store.version, prefix=f"swarm-test-{uuid.uuid4().hex[:8]}:") as st:
        try:
            a = await st.orchestrator.run_cycle(slice_profile, batch_seed=20261005)
            b = await st.orchestrator.run_cycle(slice_profile, batch_seed=20261005)
        finally:
            await st.bus.purge_prefix()
    assert a.status == "completed" and isinstance(a.t_start_ns, int) and isinstance(a.t_search_ns, int) and a.t_search_ns >= a.t_start_ns
    ttfc = time_contract.ttfc_swarm_ms(a.t_start_ns, a.t_search_ns, a.t_conv_ms)
    assert ttfc == pytest.approx((a.t_search_ns - a.t_start_ns) / 1e6 + a.t_conv_ms) and ttfc > a.t_conv_ms          # incluye AG1 e inicialización, que T_conv deja fuera
    assert ttfc < a.total_ms and a.t_conv_ms > 0                                                      # no incluye ensamblado/validación: total_ms es independiente y mayor
    assert (a.k_stop, a.g_best_S, a.g_best_F, a.stop_reason) == (b.k_stop, b.g_best_S, b.g_best_F, b.stop_reason)       # PSO determinista: las marcas no alteran k_stop ni el resultado
    assert a.to_dict()["t_start_ns"] == a.t_start_ns and a.to_dict()["t_search_ns"] == a.t_search_ns


# ═════════════════════════ P1 — contrato del indicador común ═════════════════════════
def test_ttfc_swarm_formula_none_without_marks_and_value_error_on_inconsistent_marks():
    assert time_contract.ttfc_swarm_ms(10, 2_000_010, 3.0) == pytest.approx(5.0)
    assert time_contract.ttfc_swarm_ms(None, 5, 1.0) is None and time_contract.ttfc_swarm_ms(5, None, 1.0) is None and time_contract.ttfc_swarm_ms(5, 6, None) is None
    with pytest.raises(ValueError, match="incoherentes"):
        time_contract.ttfc_swarm_ms(10, 5, 1.0)


def test_the_new_indicator_is_named_defined_and_never_labelled_t_conv():
    c = time_contract.TTFC_CONTRACT
    assert c["name"] == TTFC == time_contract.COMMON_METRIC and c["unit"] == "ms" and c["is_t_conv"] is False and c["t_conv_equivalence_claimed"] is False
    assert "conv" not in TTFC and TTFC not in ("t_conv_ms", "t_conv_baselines", "decision_ms", "total_ms", "latency_ms")
    for key in ("start", "stop", "condition", "experimental_unit", "statistical_treatment", "provenance", "excludes", "separate_from", "swarm_formula"):
        assert c[key]
    assert c["condition"] == {"id": "isolated_inprocess", "concurrency": 1, "http": False, "note": c["condition"]["note"]}
    assert c["statistical_treatment"]["confirmatory"] is False and c["status"] == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"
    assert set(c["separate_from"]) == {"t_conv_ms", "decision_ms", "total_ms", "L_resp"}
    assert time_contract.LEGACY_METRIC == "decision_ms" and time_contract.LEGACY_STATUS == "LEGACY_EXPLORATORY"
    assert "NO es T_conv" in time_contract.DEFINITIONS[TTFC] and "NO es T_conv" in time_contract.DEFINITIONS["decision_ms"]
    assert campaign_spec.SPEC["oe2"]["time_contract"]["common_indicator"]["name"] == TTFC and campaign_spec.SPEC["oe2"]["time_contract"]["legacy_metric"]["status"] == "LEGACY_EXPLORATORY"


def test_decision_ms_is_legacy_and_is_not_silently_reused_as_the_common_indicator():
    class M:
        n_messages, comm_overhead_ms, inflight_overlap = 3, 1.0, True

    class R:
        status, stop_reason, k_stop, t_conv_ms, total_ms, g_best_F, g_best_S, predicted_dominant, metrics = "completed", "epsilon", 4, 100.0, 300.0, 0.5, [1] * 8, "code", M()
        package, W, iterations, error = None, None, [], None
        t_start_ns, t_search_ns = 0, 40_000_000                                                          # 40 ms antes de la búsqueda (AG1 + inicialización)
    row = runner._swarm_row(R())
    assert row["decision_ms"] == row["t_conv_ms"] == 100.0                                              # legacy: la copia histórica no cambia
    assert row[TTFC] == pytest.approx(140.0) and row[TTFC] != row["decision_ms"] and row["total_ms"] == 300.0 and row[TTFC] != row["total_ms"]      # indicador nuevo: campo aparte


@pytest.mark.parametrize("system", ["decision_table", "rules", "bruteforce"])
def test_both_kinds_of_system_produce_the_indicator_with_the_same_conceptual_boundary(store, slice_profile, system):
    r = ConventionalAdapter(store, system).adapt(slice_profile, report_quality=False)
    assert r.status == "completed" and r.t_conv_ms is None                                              # T_conv sigue siendo solo de la propuesta
    assert 0 < r.decision_ms <= r.time_to_final_config_ms <= r.total_ms                                  # decisión ⊆ hasta-configuración-final ⊆ perfil→paquete
    row = runner._baseline_row(r)
    assert row[TTFC] == r.time_to_final_config_ms and row["t_conv_ms"] is None and row["decision_ms"] == r.decision_ms


def test_conventional_boundary_includes_w_only_for_systems_that_use_it_to_decide(store, slice_profile, monkeypatch):
    calls = []
    real = conventional.compute_weights

    def slow(prof):
        import time
        calls.append(1)
        time.sleep(0.02)
        return real(prof)
    monkeypatch.setattr(conventional, "compute_weights", slow)
    dt = ConventionalAdapter(store, "decision_table").adapt(slice_profile, report_quality=False)
    assert calls == [] and dt.time_to_final_config_ms - dt.decision_ms < 5.0                            # decision_table decide solo con el perfil: ningún W dentro de su indicador
    rl = ConventionalAdapter(store, "rules").adapt(slice_profile, report_quality=False)
    assert len(calls) == 1 and rl.time_to_final_config_ms - rl.decision_ms >= 20.0                      # rules necesita W para decidir: queda DENTRO del indicador (y fuera del legacy decision_ms)


def test_the_indicator_has_no_http_or_concurrency_in_it_and_never_reaches_the_http_campaign_schema():
    assert hw.extract_cycle_metrics({"t_conv_ms": 1.0, "decision_ms": 1.0, "k_stop": 1, "profile_id": "p", TTFC: 9.0}) == {"shape": "swarm", "t_conv_ms": 1.0, "decision_ms": 1.0, "k_stop": 1, "profile_id": "p"}
    assert not any("time_to_final" in f for f in guards.REQUIRED_RUN_FIELDS) and not any("time_to_final" in k for k in hc.record_stub())      # no se mide bajo carga HTTP
    assert "isolated_inprocess" == time_contract.TTFC_CONTRACT["condition"]["id"] and time_contract.TTFC_CONTRACT["condition"]["http"] is False
    src = inspect.getsource(time_contract.ttfc_swarm_ms)
    assert "http" not in src.lower() and "locust" not in src.lower()


def _obs(isolated: bool, n_profiles=6):
    rng = np.random.default_rng(3)
    obs = []
    for s, scale in (("swarm", 200.0), ("decision_table", 2.0)):
        for p in range(n_profiles):
            for rep in range(3):
                v = scale * float(np.exp(rng.normal(0, 0.1))) * (1 + p / 10)
                obs.append({"condition": f"{s}|c{1 if isolated else 10}", "f_system": s, "f_concurrency": 1 if isolated else 10, "profile_id": f"p{p}", "replicate": rep, "batch": 0, "status": "completed", "package_valid": True,
                            "t_conv_ms": v - 5 if s == "swarm" else None, "decision_ms": v - 5, TTFC: v, "ttfc_isolated": isolated, "latency_ms": scale, "gap_vs_optimum": 0.0})
    return obs


def test_the_indicator_is_only_contrasted_under_isolated_conditions_and_always_as_exploratory():
    iso = oea.analyze("oe2", _obs(True), [])
    res = iso["comparisons"]["c1|swarm_vs_decision_table"][TTFC]
    assert res["confirmatory"] is False and res["is_t_conv"] is False and res["metric_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and res["n"] >= 3
    busy = oea.analyze("oe2", _obs(False), [])
    assert busy["comparisons"]["c10|swarm_vs_decision_table"][TTFC]["status"] == "not_applicable_non_isolated_condition"            # con concurrencia no es este indicador
    fam = o2.analyze(_obs(True), [])["families"]["primary:swarm_vs_decision_table"]
    h = fam["pending_metric_validation"]["hypotheses"][f"{TTFC}@c1"]
    assert h["confirmatory"] is False and h["p_holm"] is None and h["result"]["isolated_condition_only"] is True and fam["m"] == 8 and fam["n_tested"] == 0           # fuera de Holm
    assert f"{TTFC}@c1" not in fam["hypotheses"] and not any("t_conv" in k.lower() for k in fam["pending_metric_validation"]["hypotheses"])
    busy_h = o2.analyze(_obs(False), [])["families"]["primary:swarm_vs_decision_table"]["pending_metric_validation"]["hypotheses"]
    assert f"{TTFC}@c10" in busy_h and busy_h[f"{TTFC}@c10"]["result"]["status"].startswith("not_testable")            # sin observaciones aisladas no se calcula nada


def test_run_condition_marks_observations_isolated_only_when_concurrency_is_one():
    src = inspect.getsource(runner.run_condition)
    assert "ttfc_isolated=cond.concurrency == 1" in src


# ═════════════════════════ P2 — persistencia: comparación OFF común + ON de la propuesta aparte ═════════════════════════
def _plan(**kw):
    base = dict(experiment="oe2", runs=2, base_seed=7, users=[1, 10], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="D3", profile_ids=IDS)
    return hc.plan(**{**base, **kw})


def test_default_plan_has_no_on_runs_and_every_run_declares_condition_and_roles():
    p = _plan()
    assert {r["persist_policy"] for r in p} == {"off"} and {r["persistence_condition"] for r in p} == {"comparison_off"} and {r["comparison_role"] for r in p} == {CONTRAST}
    assert {(r["system"], r["load"]): r["confirmatory_role"] for r in p} == {("swarm", 1): "confirmatory_family_candidate", ("swarm", 10): "confirmatory_family_candidate",
                                                                              ("decision_table", 1): "confirmatory_family_candidate", ("decision_table", 10): "confirmatory_family_candidate"}
    stress = _plan(users=[50])
    assert {r["confirmatory_role"] for r in stress} == {"stress_descriptive"}
    aux = _plan(systems=["swarm", "decision_table", "rules"])
    assert {r["system"]: r["comparison_role"] for r in aux} == {"swarm": CONTRAST, "decision_table": CONTRAST, "rules": campaign_spec.ROLE_AUXILIARY}


def test_proposal_cost_cells_are_swarm_only_on_flagged_not_in_the_contrast_and_share_seed_and_sequence_with_their_off_cell():
    p = _plan(proposal_persistence_cost=True)
    on = [r for r in p if r["persist_policy"] == "on"]
    assert on and {r["system"] for r in on} == {"swarm"} and {r["comparison_role"] for r in on} == {campaign_spec.ROLE_PROPOSAL_COST} and {r["persistence_condition"] for r in on} == {"proposal_cost_on"}
    assert {r["confirmatory_role"] for r in on} == {"descriptive_cost_measurement"} and all(r["cell"].endswith("|persON") and r["run_id"].endswith(f"r{r['run_index']:02d}") for r in on)
    assert len({r["run_id"] for r in p}) == len(p)                                                      # ningún identificador se repite entre condiciones
    assert not [r for r in p if r["system"] == "decision_table" and r["persist_policy"] != "off"]       # nunca persistencia (artificial) en el baseline
    off = {(r["run_index"], r["load"]): r for r in p if r["system"] == "swarm" and r["persist_policy"] == "off"}
    for r in on:
        o = off[(r["run_index"], r["load"])]
        assert (r["seed"], r["profile_sequence_sha256"]) == (o["seed"], o["profile_sequence_sha256"])  # misma semilla y misma secuencia de perfiles que su celda OFF
    contrast = [r for r in p if r["comparison_role"] in campaign_spec.CONTRAST_ROLES]
    assert {r["persist_policy"] for r in contrast} == {"off"} and len(contrast) == len(p) - len(on)


def test_on_is_refused_for_any_system_but_the_proposal_and_for_oe4():
    with pytest.raises(ValueError, match="solo se mide en la propuesta"):
        hc._cell_conditions("oe2", "decision_table", 1, "on")
    with pytest.raises(ValueError, match="solo aplica a OE2"):
        hc.plan("oe4", runs=1, base_seed=1, users=[1], particles=[20], systems=["swarm"], order="sequential", campaign_id="x", profile_ids=IDS, proposal_persistence_cost=True)


def _args(**kw):
    import argparse
    base = dict(experiment="oe2", campaign_id="dry", runs=1, users=[1], particles=[20], systems=list(hc.DEFAULT_OE2_SYSTEMS), warmup=10.0, window=60.0, base_seed=26100501,
                order="randomized-blocks", persist_policy="off", official=False)
    return argparse.Namespace(**{**base, **kw})


def test_provenance_and_dry_run_register_system_persistence_roles_and_never_say_off_is_the_literal_l_resp(capsys, tmp_path):
    runs = _plan(proposal_persistence_cost=True)
    prov = hc.provenance(_args(users=[1, 10], runs=2), runs)
    pc = prov["persistence_conditions"]
    assert pc["comparison"] == "off" and pc["proposal_cost"] == "on" and pc["comparison_off_is_literal_l_resp"] is False and pc["proposal_on_in_contrast"] is False
    assert pc["n_runs_by_condition"] == {"comparison_off": 8, "proposal_cost_on": 4} and pc["server_env"]["proposal_cost_on"] == {"SWARM_API_PERSIST": "1"}
    assert hc.provenance(_args(), _plan())["persistence_conditions"]["proposal_cost"] is None
    out = tmp_path / "never"
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(out), "--runs", "2", "--users", "1,10", "--proposal-persistence-cost", "--dry-run"])
    import json
    text = capsys.readouterr().out
    d = json.loads(text[text.index("{"):])
    assert not out.exists() and d["persistence_conditions"]["proposal_cost"] == "on" and d["scope"]["conventional_baseline"] == "decision_table"
    assert d["official"] is False and d["oe2_official"] is False
    assert any("[B5]" in r for r in d["official_refusals"])                                           # B5 sigue en pie: la decisión es provisional y no está aprobada


def test_execute_asks_the_server_for_the_run_policy_and_records_system_persistence_and_roles():
    runs = _plan(proposal_persistence_cost=True, runs=1, users=[1])
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT",
            "official": False, "oe2_official": False}
    asked = []
    raw = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])
    recs = hc.execute(runs, prov, warmup=10, window=60, do_run=lambda r, w, win: raw, ensure_server=lambda n, p: asked.append((n, p)), log=lambda m: None, profile_ids=IDS)
    assert sorted(set(asked)) == [(20, "off"), (20, "on")] and len(recs) == 3
    by = {r["run_id"]: r for r in recs}
    on = [r for r in recs if r["persist_policy"] == "on"]
    assert len(on) == 1 and on[0]["system"] == "swarm" and on[0]["comparison_role"] == campaign_spec.ROLE_PROPOSAL_COST and on[0]["persistence_condition"] == "proposal_cost_on"
    assert all(r["comparison_role"] == CONTRAST and r["persist_policy"] == "off" for r in recs if r is not on[0]) and len(by) == 3
    assert {"persistence_condition", "comparison_role", "confirmatory_role"} <= set(guards.REQUIRED_RUN_FIELDS) and not hc.missing_run_fields()


def test_server_per_n_rejects_an_unknown_persistence_policy_before_starting_anything():
    s = hc.ServerPerN("python", 8999, "k")
    with pytest.raises(ValueError, match="política de persistencia desconocida"):
        s.ensure(20, "maybe")
    assert s.proc is None


def _runs(on_p95=4000.0, on_role=campaign_spec.ROLE_PROPOSAL_COST, with_on=True, on_policy="on", on_system="swarm"):
    rng = np.random.default_rng(0)
    out = []
    for s, lat, thr in (("swarm", 900.0, 12.0), ("decision_table", 200.0, 300.0)):
        for u in (1, 10):
            for i in range(5):
                out.append({"status": "ok", "system": s, "load": u, "users": u, "run_id": f"{s}-{u}-{i}", "latency_p95_ms": lat * float(np.exp(rng.normal(0, 0.05))), "throughput_rps": thr + float(rng.normal(0, 0.3)),
                            "decision_ms_mean": 1.0, "comparable": True, "persist_policy": "off", "comparison_role": CONTRAST, "persistence_condition": "comparison_off"})
    if with_on:
        for u in (1, 10):
            for i in range(5):
                out.append({"status": "ok", "system": on_system, "load": u, "users": u, "run_id": f"on-{u}-{i}", "latency_p95_ms": on_p95 * float(np.exp(rng.normal(0, 0.05))), "throughput_rps": 9.0 + float(rng.normal(0, 0.3)),
                            "decision_ms_mean": 1.0, "comparable": True, "persist_policy": on_policy, "comparison_role": on_role, "persistence_condition": "proposal_cost_on"})
    return out


def test_an_on_run_of_the_proposal_never_enters_the_swarm_vs_decision_table_contrast():
    without = o2.analyze([], _runs(with_on=False))
    with_on = o2.analyze([], _runs())
    assert with_on["families"] == without["families"]                                                     # el contraste es idéntico con o sin las corridas ON (que además son muy distintas)
    cost = with_on["proposal_persistence_cost"]
    assert cost["confirmatory"] is False and cost["in_swarm_vs_decision_table_contrast"] is False and cost["l_resp_literal"] is True and cost["family"] == "PENDING_METHODOLOGICAL_DECISION"
    assert cost["u1"]["n_runs_on"] == 5 and cost["u1"]["runs_with_p95_below_2000ms"] == 0 and cost["u1"]["vs_swarm_off"]["confirmatory"] is False and with_on["n_http_runs_proposal_cost"] == 10
    assert with_on["http_runs_excluded_from_contrast"] == [] and with_on["persistence_conditions"]["comparison_off_is_literal_l_resp"] is False
    assert without["proposal_persistence_cost"].keys() == {"role", "confirmatory", "in_swarm_vs_decision_table_contrast", "l_resp_literal", "family", "note"}


@pytest.mark.parametrize("kw", [dict(on_role=CONTRAST), dict(on_policy="off", on_role=campaign_spec.ROLE_PROPOSAL_COST), dict(on_system="decision_table")])
def test_a_mislabelled_or_inconsistent_on_run_is_excluded_not_silently_mixed_into_the_contrast(kw):
    base = o2.analyze([], _runs(with_on=False))["families"]
    res = o2.analyze([], _runs(**kw))
    assert len(res["http_runs_excluded_from_contrast"]) == 10                                              # ON con rol de contraste / política off con rol de costo / decision_table ON: ninguna entra
    assert res["families"] == base and res["n_http_runs_proposal_cost"] == 0


def test_runs_without_declared_persistence_or_role_fail_closed():
    recs = _runs(with_on=False)
    for r in recs:
        r.pop("persist_policy")
    res = o2.analyze([], recs)
    assert res["families"]["primary:swarm_vs_decision_table"]["n_tested"] == 0 and len(res["http_runs_excluded_from_contrast"]) == len(recs)
    recs2 = _runs(with_on=False)
    for r in recs2:
        r.pop("comparison_role")
    assert o2.analyze([], recs2)["families"]["primary:swarm_vs_decision_table"]["n_tested"] == 0


def test_analyze_records_passes_the_persistence_fields_through_so_on_runs_stay_apart():
    recs = [{**r, "p95_ms": r["latency_p95_ms"], "throughput_http": r["throughput_rps"]} for r in _runs()]
    res = hc.analyze_records("oe2", recs)
    assert res["n_http_runs_proposal_cost"] == 10 and res["proposal_persistence_cost"]["u10"]["n_runs_on"] == 5
    assert res["families"]["primary:swarm_vs_decision_table"]["m"] == 8 and res["families"]["primary:swarm_vs_decision_table"]["n_tested"] == 4


def test_l_resp_and_t_conv_definitions_are_not_redefined_and_the_spec_declares_off_is_not_the_approved_l_resp():
    lr, tc = defs.DEFINITIONS["latency_l_resp"], defs.DEFINITIONS["t_conv"]
    assert lr["status"] == defs.APPROVED and lr["definition"] == ("L_resp = petición HTTP → último byte del JSON con el paquete (incluye RF01, AG1, PSO, Redis, ensamblado y persistencia síncrona mínima; "
                                                                  "excluye descarga de audio y persistencia asíncrona); P95 con ≤ 25 usuarios")
    assert tc["status"] == defs.APPROVED and tc["definition"] == "T_conv se reporta en iteraciones (k_stop) y en milisegundos (t_convergencia − t_inicio_búsqueda); regla de parada |ΔF|<ε o k_max=15"
    pp = campaign_spec.SPEC["oe2"]["persist_policy"]
    assert pp["comparison_persistence"] == "off" and pp["proposal_persistence_cost"] == "on" and pp["comparison_off_is_literal_l_resp"] is False and pp["proposal_on_is_literal_l_resp"] is True
    assert pp["artificial_persistence_in_baseline"] is False and pp["status"] == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED" and pp["campaign"] == "off"
    assert guards.persistence_status("off")["status"] == "INCOMPATIBLE_WITH_APPROVED_L_RESP_DEFINITION"          # el guard sigue diciendo la verdad: OFF no es el L_resp aprobado


# ═════════════════════════ P3 — alcance del comparador ═════════════════════════
def test_scope_is_the_proposal_vs_decision_table_with_no_additional_conventional_systems_and_a_generalization_limit():
    sc = campaign_spec.SPEC["oe2"]["scope"]
    assert sc["proposal"] == "swarm" and sc["conventional_baseline"] == "decision_table" and sc["additional_conventional_systems"] == []
    assert sc["reference_optimum"] == "bruteforce" and sc["swarm_ablation"] == "rules" and sc["oe2_text_modified"] is False and sc["status"] == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"
    assert "NO permiten generalizar" in sc["generalization_limit"]
    assert conventional.SYSTEM_ROLES == {"decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "bruteforce": "reference_optimum"}
    assert [s for s, r in conventional.SYSTEM_ROLES.items() if r == "conventional_independent"] == ["decision_table"]                 # un único convencional independiente
    oe2 = campaign_spec.SPEC["oe2"]
    assert oe2["design"]["systems"] == ["swarm", "decision_table"] and oe2["auxiliary_contrasts"] == ["rules", "bruteforce"] and oe2["comparator_scope_validation"]["implemented_conventional_systems"] == ["decision_table"]
    assert oe2["comparator_scope_validation"]["status"] != "VALIDATED" and oe2["comparator_scope_validation"]["decision"] == "B13-A (provisional)"           # sigue sin aprobarse: el guard B13 se mantiene
    assert "B13" in {b.id for b in guards.evaluate(None) if b.critical and b.frozen}


def test_the_plan_still_requires_exactly_the_proposal_and_decision_table_and_rejects_unknown_systems():
    with pytest.raises(ValueError, match="exige la propuesta y el convencional independiente"):
        _plan(systems=["swarm", "rules"])
    with pytest.raises(ValueError, match="sistemas desconocidos"):
        _plan(systems=["swarm", "decision_table", "lms"])


# ═════════════════════════ P4 — guard DEF dependency-aware ═════════════════════════
def _def_reasons(monkeypatch=None, experiment="oe2"):
    return [b.reason for b in guards.evaluate(None, experiment) if b.id == "DEF"]


def _resolve_all(monkeypatch, experiment="oe2"):
    for k in defs.OE_DEFINITION_DEPENDENCIES[experiment]:
        monkeypatch.setitem(defs.DEFINITIONS, k, {**defs.DEFINITIONS[k], "status": defs.APPROVED})


def test_default_oe2_blockers_are_exactly_its_real_pending_dependencies_and_not_those_of_oe1_or_oe5():
    reasons = " | ".join(_def_reasons())
    assert defs.blocked_for("oe2") == ["common_time_indicator_oe2", "statistical_unit_performance"]
    assert all(k in reasons for k in ("common_time_indicator_oe2", "statistical_unit_performance")) and "t_conv_baselines" not in reasons
    assert "compliance_score_oe1" not in reasons and "reliability_oe1" not in reasons and "F1 v3" not in reasons
    assert defs.blocked_for("oe1") == ["compliance_score_oe1", "reliability_oe1"]                         # el mapa funciona en ambos sentidos: OE1 sí depende de las suyas


@pytest.mark.parametrize("dep", ["common_time_indicator_oe2", "statistical_unit_performance"])
def test_a_pending_real_dependency_of_oe2_blocks(monkeypatch, dep):
    _resolve_all(monkeypatch)
    assert _def_reasons() == []
    monkeypatch.setitem(defs.DEFINITIONS, dep, {**defs.DEFINITIONS[dep], "status": defs.PENDING})
    assert [r for r in _def_reasons() if dep in r] and defs.blocked_for("oe2") == [dep]
    assert any(b.id == "DEF" and b.critical for b in guards.evaluate(None))


def test_a_pending_definition_of_oe1_that_oe2_does_not_need_does_not_block_oe2(monkeypatch):
    _resolve_all(monkeypatch)
    for k in ("compliance_score_oe1", "reliability_oe1"):
        monkeypatch.setitem(defs.DEFINITIONS, k, {**defs.DEFINITIONS[k], "status": defs.PENDING})
    assert _def_reasons() == [] and defs.blocked_for("oe2") == [] and defs.blocked_for("oe1") == ["compliance_score_oe1", "reliability_oe1"]


def test_a_pending_definition_of_oe5_or_an_unsealed_f1_v3_does_not_block_oe2(monkeypatch):
    from adaptation_swarm.gold import rubric_v3
    _resolve_all(monkeypatch)
    monkeypatch.setitem(defs.DEFINITIONS, "oe5_only_hypothetical", {"status": defs.PENDING, "definition": "solo OE5"})
    monkeypatch.setitem(defs.DEFINITIONS, "precision_multimodal_oe5", {**defs.DEFINITIONS["precision_multimodal_oe5"], "status": defs.PENDING})
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset())
    assert _def_reasons() == [] and defs.blocked_for("oe2") == []


def test_the_def_guard_fails_closed_on_missing_unknown_status_and_unknown_experiment(monkeypatch):
    _resolve_all(monkeypatch)
    monkeypatch.delitem(defs.DEFINITIONS, "statistical_unit_performance")
    assert defs.blocked_for("oe2") == ["statistical_unit_performance (no registrada)"] and [r for r in _def_reasons() if "no registrada" in r]
    monkeypatch.setitem(defs.DEFINITIONS, "statistical_unit_performance", {"definition": "sin estado"})
    assert defs.blocked_for("oe2") == ["statistical_unit_performance"]
    monkeypatch.setitem(defs.DEFINITIONS, "statistical_unit_performance", {"status": "resuelta?", "definition": "estado desconocido"})
    assert defs.blocked_for("oe2") == ["statistical_unit_performance"]                                    # un estado que no es APPROVED/PARTIAL no desbloquea
    assert defs.blocked_for("oe9") == ["<experimento desconocido: 'oe9'>"] and any(b.id == "DEF" and b.critical for b in guards.evaluate(None, "oe9"))


def test_the_def_guard_reads_state_not_free_text(monkeypatch):
    _resolve_all(monkeypatch)
    monkeypatch.setitem(defs.DEFINITIONS, "common_time_indicator_oe2", {**defs.DEFINITIONS["common_time_indicator_oe2"], "status": defs.PENDING, "definition": "APPROVED resuelta aprobada", "note": "status APPROVED"})
    assert defs.blocked_for("oe2") == ["common_time_indicator_oe2"]                                         # reescribir el texto no desbloquea
    src = inspect.getsource(defs.blocked_for)
    assert "re.search" not in src and "re.match" not in src and '["definition"]' not in src and '["note"]' not in src and 'status' in src
    monkeypatch.setitem(defs.DEFINITIONS, "common_time_indicator_oe2", {**defs.DEFINITIONS["common_time_indicator_oe2"], "status": defs.APPROVED})
    assert defs.blocked_for("oe2") == []                                                                    # solo el cambio de ESTADO lo desbloquea


def test_evaluate_takes_the_experiment_from_the_provenance_and_defaults_to_oe2(monkeypatch):
    _resolve_all(monkeypatch)
    monkeypatch.setitem(defs.DEFINITIONS, "compliance_score_oe1", {**defs.DEFINITIONS["compliance_score_oe1"], "status": defs.PENDING})
    assert _def_reasons(experiment="oe2") == [] and [b for b in guards.evaluate({"experiment": "oe1"}) if b.id == "DEF"]
    assert [b for b in guards.evaluate({}) if b.id == "DEF"] == []                                       # sin experimento declarado = OE2 (guard de campaña OE2)


def test_the_official_flag_is_still_refused_because_oe2_real_dependencies_remain_pending():
    refusals = hc.official_refusals({"vcpu": 20, "ram_gib": 31.75}, 10, 10.0, 60.0, None)
    text = " | ".join(refusals)
    assert "[DEF]" in text and "common_time_indicator_oe2" in text and "[B1]" in text and "[B5]" in text and "[B13]" in text
    assert campaign_spec.open_blockers() and campaign_spec.SPEC["advisor_approved"] is False


# ═════════════════════════ Corrección final de B1 y auditoría (antes de D.4) ═════════════════════════
def test_t_conv_baselines_is_superseded_not_a_dependency_and_no_active_text_equates_t_conv_between_systems():
    tb = defs.DEFINITIONS["t_conv_baselines"]
    assert tb["status"] == defs.SUPERSEDED and "common_time_indicator_oe2" in tb["note"] and not any("t_conv_baselines" in v for v in defs.OE_DEFINITION_DEPENDENCIES.values())
    assert "t_conv_baselines" not in defs.blocked_for("oe2") and not any("t_conv_baselines" in r for r in _def_reasons())
    assert "SOLO de la propuesta" in defs.DEFINITIONS["t_conv"]["note"]
    active = [v["definition"] + " " + v.get("note", "") for k, v in defs.DEFINITIONS.items() if v["status"] != defs.SUPERSEDED] + list(time_contract.DEFINITIONS.values())
    assert not [t for t in active if "equipar" in t.lower() and "t_conv" in t.lower() and "no se" not in t.lower()]


def test_a_superseded_status_is_never_treated_as_resolved_if_it_were_a_dependency(monkeypatch):
    monkeypatch.setitem(defs.OE_DEFINITION_DEPENDENCIES, "oe2", defs.OE_DEFINITION_DEPENDENCIES["oe2"] + ["t_conv_baselines"])
    assert "t_conv_baselines" in defs.blocked_for("oe2")                                                   # fail-closed: un estado distinto de APPROVED/PARTIAL no desbloquea


def test_the_only_experimental_conventional_baseline_is_decision_table_and_no_lms_llm_system_exists():
    from adaptation_swarm.oe import conditions
    assert set(conditions.SYSTEMS) == {"swarm", "rules", "bruteforce", "decision_table"} and set(conventional.SYSTEMS) == {"rules", "bruteforce", "decision_table"}
    roles = campaign_spec.SPEC["oe2"]["system_roles"]
    assert [s for s, r in roles.items() if r == "conventional_independent"] == ["decision_table"] and roles["rules"] == "swarm_heuristic_ablation" and roles["bruteforce"] == "reference_optimum"
    assert campaign_spec.SPEC["oe2"]["comparator_primary"] == "decision_table" and set(campaign_spec.SPEC["oe2"]["auxiliary_contrasts"]) == {"rules", "bruteforce"}
    for bad in ("lms", "moodle", "canvas", "llm", "llm_monolithic"):
        with pytest.raises(ValueError, match="sistemas desconocidos"):
            _plan(systems=["swarm", "decision_table", bad])


def test_every_frozen_decision_stays_provisional_and_not_advisor_approved_and_the_guards_keep_blocking():
    spec = campaign_spec.SPEC["oe2"]
    for status in (time_contract.TTFC_CONTRACT["status"], spec["scope"]["status"], spec["persist_policy"]["status"]):
        assert status == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"
    assert campaign_spec.SPEC["advisor_approved"] is False and time_contract.STATUS.endswith("UNVALIDATED") and spec["comparator_scope_validation"]["status"] != "VALIDATED"
    crit = {b.id: b for b in guards.evaluate(None) if b.critical}
    assert {"B1", "B5", "B13", "DEF"} <= set(crit) and all(crit[i].frozen for i in ("B1", "B5", "B13"))
    assert "APPROVED" not in {time_contract.VALIDATION_STATUS, time_contract.T_CONV_EQUIVALENCE}
