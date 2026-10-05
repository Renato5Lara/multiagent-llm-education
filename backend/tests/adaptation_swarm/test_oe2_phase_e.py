"""OE2 Fase E: preparación técnica posterior a D.5. Solo infraestructura que NO decide ninguna cuestión metodológica: guard `PEND` (decisiones de D.5 representadas y bloqueantes), trazabilidad de orden/arranque del servidor,
observación de PostgreSQL por corrida, invariantes de integridad, esquema de corrida y provenance. Sin campañas."""

import inspect
import json

import numpy as np
import pytest

from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import campaign_guards as guards
from adaptation_swarm.oe import campaign_spec, code_state, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, run_isolation
from adaptation_swarm.oe import stats_cli

IDS = [f"p{i}" for i in range(100)]
DECISIONS = campaign_spec.SPEC["oe2"]["methodological_decisions"]
EXPECTED = sorted(["common_indicator_asymmetry", "cold_warm_policy", "errors_timeouts_in_l_resp", "execution_order", "holm_family_size", "http_pairing", "l_resp_literal_hypothesis_h1", "latency_statistic"])


# ═════════════════════════ guard PEND ═════════════════════════
def test_every_d5_decision_is_represented_pending_and_blocks_official_without_being_decided_by_default():
    assert sorted(DECISIONS) == EXPECTED and guards.pending_methodological_decisions() == EXPECTED
    assert all(d["status"] == "PENDING" and d["chosen"] is None and len(d["options"]) >= 2 and d["source"] for d in DECISIONS.values())
    peb = [b for b in guards.evaluate(None) if b.id == "PEND"]
    assert len(peb) == 1 and peb[0].critical and peb[0].frozen and peb[0].kind == "methodological" and all(k in peb[0].reason for k in EXPECTED)
    assert any("[PEND]" in r for r in hc.official_refusals({"vcpu": 20, "ram_gib": 31.75}, 10, 10.0, 60.0, None))


def test_a_decision_is_resolved_only_by_an_explicit_decided_status_with_a_choice_among_its_options(monkeypatch):
    key = "http_pairing"
    for bad in ({"status": "DECIDED", "chosen": None}, {"status": "DECIDED", "chosen": "otra_cosa"}, {"status": "PENDING", "chosen": "independent_runs"}, {"status": "decided", "chosen": "independent_runs"},
                {"status": "ADVISOR_APPROVED", "chosen": "independent_runs"}):
        monkeypatch.setitem(DECISIONS, key, {**DECISIONS[key], **bad})
        assert key in guards.pending_methodological_decisions(), bad
    monkeypatch.setitem(DECISIONS, key, {**DECISIONS[key], "status": "DECIDED", "chosen": "paired_by_run_index_and_load"})
    assert key not in guards.pending_methodological_decisions() and len(guards.pending_methodological_decisions()) == len(EXPECTED) - 1


def test_the_pend_guard_fails_closed_on_missing_or_malformed_structure_and_lifts_only_when_everything_is_decided(monkeypatch):
    monkeypatch.setitem(campaign_spec.SPEC["oe2"], "methodological_decisions", {})
    assert guards.pending_methodological_decisions() == ["<estructura de decisiones ausente>"]
    monkeypatch.setitem(campaign_spec.SPEC["oe2"], "methodological_decisions", {"x": "no es un mapa"})
    assert guards.pending_methodological_decisions() == ["x"]
    monkeypatch.undo()
    for k, d in DECISIONS.items():
        monkeypatch.setitem(DECISIONS, k, {**d, "status": "DECIDED", "chosen": d["options"][0]})
    assert guards.pending_methodological_decisions() == [] and "PEND" not in {b.id for b in guards.evaluate(None)}


def test_no_analysis_module_reads_the_pending_decisions_so_representing_them_changes_no_behaviour():
    for mod in (o2, oea, hw, stats_cli):
        src = inspect.getsource(mod)
        assert "methodological_decisions" not in src and '"chosen"' not in src, mod.__name__
    assert "independent_comparison" in inspect.getsource(o2.runs_comparison)                          # lo implementado hoy sigue siendo lo declarado en `implemented_today`
    assert DECISIONS["http_pairing"]["implemented_today"] == "independent_runs" and DECISIONS["latency_statistic"]["implemented_today"] == "p95"
    assert "dynamic_m" == DECISIONS["holm_family_size"]["implemented_today"] and DECISIONS["holm_family_size"]["advisor_backing"].startswith("NO DETERMINABLE")


def test_provenance_and_dry_run_carry_the_unresolved_decisions_and_the_cold_warm_facts(capsys, tmp_path):
    out = tmp_path / "never"
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(out), "--runs", "2", "--users", "1,10", "--proposal-persistence-cost", "--dry-run"])
    text = capsys.readouterr().out
    d = json.loads(text[text.index("{"):])
    assert not out.exists() and d["methodological_decisions_unresolved"] == EXPECTED and d["cold_warm"]["policy"].startswith("NOT_DECIDED") and d["cold_warm"]["n_runs"] == 12
    assert d["cold_warm"]["planned_server_starts"] >= 2 and "server_instance" in d["cold_warm"]["recorded_per_run"]
    assert d["official"] is False and any("[PEND]" in r for r in d["official_refusals"])


# ═════════════════════════ trazabilidad de arranque (cold/warm) y de orden ═════════════════════════
def _fake_server(monkeypatch, healths):
    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass

    class Resp:
        def __init__(self, b):
            self.b = b

        def read(self):
            return self.b
    import urllib.request
    state = {"policy": "off"}
    monkeypatch.setattr(hc.subprocess, "Popen", lambda cmd, env=None, **kw: (state.update(policy="off" if env["SWARM_API_PERSIST"] == "0" else "on"), FakeProc())[1])
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: Resp(json.dumps({"persist_policy": state["policy"], "baseline_quality_in_request": False, "library_version": "v"}).encode()))


def test_the_server_reports_which_instance_serves_each_run_whether_it_was_restarted_and_how_many_runs_it_had_served(monkeypatch):
    _fake_server(monkeypatch, None)
    s = hc.ServerPerN("python", 8999, "k")
    seq = [s.ensure(20, "off"), s.ensure(20, "off"), s.ensure(20, "off"), s.ensure(20, "on"), s.ensure(20, "on"), s.ensure(10, "on")]
    assert [(h["server_instance"], h["server_restarted_before_run"], h["server_runs_served_before"]) for h in seq] == [(1, True, 0), (1, False, 1), (1, False, 2), (2, True, 0), (2, False, 1), (3, True, 0)]
    assert all("library_version" in h and h["baseline_quality_in_request"] is False for h in seq)       # el /health sigue ahí


def _prov():
    return {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT",
            "official": False, "oe2_official": False}


_RAW = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])


def _plan(**kw):
    return hc.plan("oe2", runs=2, base_seed=3, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="C", profile_ids=IDS, **kw)


def test_each_record_carries_run_index_execution_order_and_the_server_traceability(monkeypatch):
    _fake_server(monkeypatch, None)
    server = hc.ServerPerN("python", 8999, "k")
    runs = _plan()
    recs = hc.execute(runs, _prov(), warmup=10, window=60, do_run=lambda r, w, win: _RAW, ensure_server=server.ensure, log=lambda m: None, profile_ids=IDS)
    assert [r["execution_index"] for r in recs] == [1, 2, 3, 4] and [r["run_index"] for r in recs] == [r["run_index"] for r in runs]
    assert [(r["server_instance"], r["server_restarted_before_run"], r["server_runs_served_before"]) for r in recs] == [(1, True, 0), (1, False, 1), (1, False, 2), (1, False, 3)]
    assert all(r["batch_id"] and r["seed"] is not None for r in recs) and not hc.missing_run_fields()


def test_the_analysis_receives_the_pairing_keys_but_does_not_use_them(monkeypatch):
    captured = {}
    monkeypatch.setattr(o2, "analyze", lambda obs, http_runs: captured.setdefault("s", list(http_runs)) and {})
    recs = [{**hc.record_stub(), "status": "ok", "system": "swarm", "load": 1, "users": 1, "run_id": "a", "p95_ms": 1.0, "throughput_http": 1.0, "run_index": 3, "batch_id": "b3", "seed": 9, "execution_index": 7}]
    hc.analyze_records("oe2", recs)
    assert {k: captured["s"][0][k] for k in ("run_index", "batch_id", "seed", "execution_index")} == {"run_index": 3, "batch_id": "b3", "seed": 9, "execution_index": 7}


def test_planned_server_starts_counts_changes_of_n_and_persistence_and_the_default_plan_needs_one():
    mk = lambda *keys: [{"swarm_N": n, "persist_policy": p} for n, p in keys]
    assert hc.planned_server_starts(mk((20, "off"))) == 1 and hc.planned_server_starts(mk((20, "off"), (20, "off"), (20, "on"), (20, "off"), (10, "off"))) == 4 and hc.planned_server_starts([]) == 0
    default = hc.plan("oe2", runs=10, base_seed=26100501, users=[1, 5, 10, 25, 50, 100], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="x", profile_ids=IDS)
    with_on = hc.plan("oe2", runs=10, base_seed=26100501, users=[1, 5, 10, 25, 50, 100], particles=[20], systems=["swarm", "decision_table"], order="randomized-blocks", campaign_id="x", profile_ids=IDS, proposal_persistence_cost=True)
    assert hc.planned_server_starts(default) == 1 and hc.planned_server_starts(with_on) > 10                 # el efecto de las celdas ON sobre los reinicios queda a la vista (no se decide aquí)


# ═════════════════════════ PostgreSQL por corrida y observación ═════════════════════════
@pytest.mark.parametrize("policy, before, after, consistent", [("on", 5, 9, True), ("on", 5, 5, False), ("off", 5, 5, True), ("off", 5, 6, False)])
def test_postgres_observation_checks_that_on_wrote_rows_and_off_wrote_none(policy, before, after, consistent):
    o = hc.postgres_observation(policy, before, after)
    assert o["observed"] is True and o["cycles_delta"] == after - before and o["consistent"] is consistent and o["expected"] == ("rows" if policy == "on" else "no_rows")


def test_an_unreachable_postgres_is_reported_as_not_observed_never_as_consistent():
    o = hc.postgres_observation("on", None, None)
    assert o == {"observed": False, "cycles_before": None, "cycles_after": None, "cycles_delta": None, "expected": "rows", "consistent": None}


def _run_with_postgres(rows_written_by_on_runs):
    runs = _plan(proposal_persistence_cost=True)
    state = {"cycles": 0}
    order = []

    def do_run(r, w, win):
        order.append(("load", r["persist_policy"]))
        if r["persist_policy"] == "on":
            state["cycles"] += rows_written_by_on_runs                                                      # lo que la persistencia ON realmente escribió
        return _RAW
    recs = hc.execute(runs, _prov(), warmup=10, window=60, log=lambda m: None, profile_ids=IDS, ensure_server=lambda n, p: {"persist_policy": p}, do_run=do_run,
                      observe=lambda r: (order.append(("obs", r["persist_policy"])), state["cycles"])[1])
    return recs, order


def test_execute_observes_postgres_before_and_after_the_load_and_records_the_result_per_run():
    recs, order = _run_with_postgres(40)
    assert [o[0] for o in order[:3]] == ["obs", "load", "obs"] and len(recs) == 6
    on = [r["postgres_observation"] for r in recs if r["persist_policy"] == "on"]
    off = [r["postgres_observation"] for r in recs if r["persist_policy"] == "off"]
    assert len(on) == 2 and all(o["cycles_delta"] == 40 and o["consistent"] is True for o in on) and len(off) == 4 and all(o["cycles_delta"] == 0 and o["consistent"] is True for o in off)
    assert hc.integrity_violations(recs) == [] or all(v["kind"] != "postgres_disagrees_with_persistence_policy" for v in hc.integrity_violations(recs))


def test_an_on_run_whose_persistence_silently_failed_is_flagged_by_the_observation():
    recs, _ = _run_with_postgres(0)                                                                         # el router traga los fallos de persistencia: PostgreSQL delata que no se escribió nada
    flagged = [v for v in hc.integrity_violations(recs) if v["kind"] == "postgres_disagrees_with_persistence_policy"]
    assert len(flagged) == 2 and all(next(r for r in recs if r["run_id"] == v["run_id"])["persist_policy"] == "on" for v in flagged) and len(recs) == 6      # se informa; las corridas se conservan


def test_the_postgres_probe_returns_a_count_or_none_and_never_writes():
    import uuid
    probe = run_isolation.PostgresRunProbe(f"probe-{uuid.uuid4().hex[:8]}")
    assert probe.cycles() in (0, None)                                                                       # etiqueta nueva: 0 filas (o None si PostgreSQL no responde)

    def boom():
        raise RuntimeError("sin base")
    assert run_isolation.PostgresRunProbe("x", session_factory=boom).cycles() is None
    src = inspect.getsource(run_isolation.PostgresRunProbe.cycles)
    assert "insert" not in src.lower() and "delete" not in src.lower() and "commit" not in src


# ═════════════════════════ invariantes de integridad y esquema ═════════════════════════
def _rec(**kw):
    return {**hc.record_stub(), "run_id": "r1", "persist_policy": "off", "profile_sequence_check": {"checked": 100, "mismatches": 0, "unindexed": 0}, "requests_without_cycle_metrics": 0, **kw}


def test_integrity_violations_flags_each_declared_invariant_and_keeps_the_runs():
    assert hc.integrity_violations([_rec()]) == []
    kinds = lambda **kw: [v["kind"] for v in hc.integrity_violations([_rec(**kw)])]
    assert kinds(profile_sequence_check={"checked": 100, "mismatches": 2, "unindexed": 0}) == ["profile_sequence_mismatch"]
    assert kinds(profile_sequence_check={"checked": 100, "mismatches": 0, "unindexed": 3}) == ["profile_sequence_unindexed_requests"]
    assert kinds(requests_without_cycle_metrics=4) == ["requests_without_cycle_metrics"]
    assert kinds(persist_policy_effective="on") == ["effective_persistence_differs"]
    assert kinds(persist_policy="on", postgres_observation=hc.postgres_observation("on", 3, 3)) == ["postgres_disagrees_with_persistence_policy"]
    assert kinds(persist_policy_effective="off", postgres_observation=hc.postgres_observation("off", 1, 1)) == []
    recs = [_rec(), _rec(run_id="r2", requests_without_cycle_metrics=1)]
    assert len(recs) == 2 and [v["run_id"] for v in hc.integrity_violations(recs)] == ["r2"]               # solo se informa: nada se excluye


def test_write_campaign_rejects_incomplete_run_records_and_flags_official_validity(tmp_path):
    prov = {"campaign_id": "C", "experiment": "oe2", "campaign_spec": campaign_spec.identity(), "environment_class": "PILOT", "official": True, "oe2_official": False}
    good = [{**hc.record_stub(), "run_id": "a", "status": "ok", "system": "swarm", "load": 1, "users": 1, "p95_ms": 1.0, "throughput_http": 1.0}]
    bad = [{k: v for k, v in good[0].items() if k != "postgres_observation"}]
    with pytest.raises(ValueError, match="sin los campos requeridos"):
        hc.write_campaign(tmp_path / "bad", prov, [], bad, [])
    assert not (tmp_path / "bad").exists()                                                                   # nada se escribe con el esquema roto
    hc.write_campaign(tmp_path / "ok", prov, [], good, [])
    assert json.loads((tmp_path / "ok" / "manifest.json").read_text())["official_valid"] is True
    hc.write_campaign(tmp_path / "viol", {**prov, "integrity_violations": [{"run_id": "a", "kind": "x"}]}, [], good, [])
    assert json.loads((tmp_path / "viol" / "manifest.json").read_text())["official_valid"] is False
    hc.write_campaign(tmp_path / "gap", {**prov, "provenance_completion_gaps": ["code_state_final.dirty"]}, [], good, [])
    assert json.loads((tmp_path / "gap" / "manifest.json").read_text())["official_valid"] is False
    hc.write_campaign(tmp_path / "pilot", {**prov, "official": False}, [], good, [])
    assert json.loads((tmp_path / "pilot" / "manifest.json").read_text())["official_valid"] is False         # una campaña no oficial nunca es «oficial válida»


# ═════════════════════════ provenance ═════════════════════════
def test_hardware_cpu_model_and_the_other_environment_facts_are_required_for_reproducibility():
    for path in ("hardware.cpu_model", "software.redis_client", "software.fastapi", "cold_warm.planned_server_starts"):
        assert path in code_state.PROVENANCE_REQUIRED, path
    assert code_state.PROVENANCE_REQUIRED_FOR_EXECUTION == ("software.redis_server",) and "software.redis_server" not in code_state.PROVENANCE_REQUIRED
    args = __import__("argparse").Namespace(experiment="oe2", campaign_id="C", runs=1, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                                            persist_policy="off", official=False)
    prov = hc.provenance(args, _plan())
    broken = json.loads(json.dumps(prov))
    broken["hardware"]["cpu_model"] = None
    assert "hardware.cpu_model" in code_state.provenance_gaps(broken)
    assert prov["cold_warm"]["planned_server_starts"] == 1 and prov["methodological_decisions"] == campaign_spec.SPEC["oe2"]["methodological_decisions"]


def test_a_real_execution_is_refused_before_anything_starts_when_redis_cannot_be_recorded(monkeypatch, tmp_path):
    monkeypatch.setattr(code_state, "_redis_server_version", lambda: code_state.UNAVAILABLE)
    out = tmp_path / "never"
    with pytest.raises(SystemExit, match="faltan datos de provenance indispensables"):
        hc.main(["oe2", "--campaign-id", "x", "--out-dir", str(out), "--runs", "1", "--users", "1"])
    assert not out.exists() and not out.with_name(out.name + ".tmp-raw").exists()


def test_the_new_provenance_requirements_do_not_make_the_default_dry_run_incomplete():
    args = __import__("argparse").Namespace(experiment="oe2", campaign_id="C", runs=1, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                                            persist_policy="off", official=False)
    prov = hc.provenance(args, _plan())
    assert code_state.provenance_gaps(prov) == [] and np.isscalar(prov["cold_warm"]["planned_server_starts"])
