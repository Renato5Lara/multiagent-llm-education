"""OE2 Fase D.4.1: corrección de inconsistencias OBJETIVAS detectadas por la auditoría D.4 (unidad estadística, guards B1/B5 con camino de aprobación correcto, aislamiento de Redis, provenance de PostgreSQL y de roles).
No resuelve ninguna decisión metodológica pendiente (pareamiento, `m` de Holm, errores en el P95, H1, cold/warm, asimetría del indicador) ni cambia T_conv, L_resp, el indicador común, `decision_ms`, PSO o AG0."""

import argparse
import inspect
import json
import uuid

import pytest

from adaptation_swarm.baselines import conventional
from adaptation_swarm.oe import campaign_guards as guards
from adaptation_swarm.oe import campaign_spec, code_state, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, run_isolation, time_contract
from adaptation_swarm.oe import definitions as defs

IDS = [f"p{i}" for i in range(100)]


# ═════════════════════════ 1 — statistical_unit_performance ═════════════════════════
def test_statistical_unit_performance_states_the_real_units_and_cannot_go_back_to_the_old_generic_text():
    d = defs.DEFINITIONS["statistical_unit_performance"]
    text = d["definition"]
    assert d["status"] == defs.PENDING                                                                   # sigue pendiente de validación: no se aprobó nada
    for must in ("L_resp = P95 por CORRIDA HTTP", "throughput = por CORRIDA HTTP", "time_to_final_config_ms = PERFIL", "media de las K réplicas", "T_conv = solo descriptivo de la propuesta", "nunca es una observación independiente"):
        assert must in text, must
    assert "unidad para T_conv, latencia y throughput" not in text and "media por perfil para T_conv" not in text + d["note"] and "LOTE" not in text + d["note"]
    assert "DEFINITIVA de OE2 sigue PENDING" in d["note"] and "INTERNA de estudio (F.2.3, no aprobada por el asesor)" in d["note"] and "P95 vs media" in d["note"] and "H1" in d["note"]            # G.2: lo pendiente queda dicho; lo interno no se presenta como del asesor


def test_the_definition_matches_what_the_implementation_and_the_spec_actually_use():
    oe2 = campaign_spec.SPEC["oe2"]
    assert oe2["design"]["unit_throughput"].startswith("run") and "corrida HTTP" in oe2["design"]["unit_common_time_indicator_and_latency"] and "profile" in oe2["design"]["unit_common_time_indicator_and_latency"]
    assert time_contract.TTFC_CONTRACT["experimental_unit"].startswith("perfil") and oe2["time_contract"]["t_conv_scope"].startswith("T_conv es SOLO de la propuesta")
    assert 'lat = [r["response_ms"] for r in ok]' in inspect.getsource(hw.summarize_run) and '"unit": "run"' in inspect.getsource(hw.summarize_run)
    assert '"unit": "run"' in inspect.getsource(o2.runs_comparison) and '"unit": "profile"' in inspect.getsource(o2.paired_log_by_profile)


# ═════════════════════════ 2 — guards B1 y B5 ═════════════════════════
def _crit():
    return {b.id: b for b in guards.evaluate(None) if b.critical}


def test_today_b1_and_b5_remain_blocked_frozen_and_nothing_is_advisor_approved():
    crit = _crit()
    assert crit["B1"].frozen and crit["B5"].frozen and crit["B13"].frozen
    assert campaign_spec.SPEC["advisor_approved"] is False and time_contract.TTFC_CONTRACT["status"] == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"
    assert campaign_spec.SPEC["oe2"]["persist_policy"]["status"] == "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED" and time_contract.VALIDATION_STATUS == "PENDING_METHODOLOGICAL_VALIDATION"
    assert "NO con equivalencia con T_conv" in crit["B1"].reason and "no modificando L_resp ni activando persistencia en el baseline" in crit["B5"].reason


def test_b1_is_resolved_only_by_the_explicit_approval_of_the_common_indicator_never_by_a_t_conv_equivalence(monkeypatch):
    monkeypatch.setattr(time_contract, "VALIDATION_STATUS", "VALIDATED")
    assert "B1" in _crit()                                                                               # validado pero sin aprobación explícita: sigue bloqueado
    monkeypatch.setattr(time_contract, "T_CONV_EQUIVALENCE", "ESTABLISHED")
    monkeypatch.setitem(time_contract.TTFC_CONTRACT, "status", time_contract.APPROVED_STATUS)
    assert "B1" in _crit() and "contradicción con B1" in _crit()["B1"].reason                            # declarar equivalencia de T_conv no desbloquea: contradice B1, aun con el indicador aprobado
    monkeypatch.setattr(time_contract, "T_CONV_EQUIVALENCE", "NOT_ESTABLISHED")
    assert "B1" not in _crit()                                                                           # aprobación + validación del indicador común, SIN equivalencia con T_conv
    assert time_contract.T_CONV_EQUIVALENCE == "NOT_ESTABLISHED" and time_contract.TTFC_CONTRACT["t_conv_equivalence_claimed"] is False and time_contract.TTFC_CONTRACT["is_t_conv"] is False


def test_b5_is_resolved_only_by_the_explicit_approval_of_b5_c_without_touching_l_resp_or_the_baseline(monkeypatch):
    lresp = defs.DEFINITIONS["latency_l_resp"]["definition"]
    pp = campaign_spec.SPEC["oe2"]["persist_policy"]
    monkeypatch.setitem(pp, "status", campaign_spec.APPROVED_STATUS)
    assert "B5" not in _crit()                                                                           # basta la aprobación de la decisión: L_resp intacto, baseline sin persistencia
    assert defs.DEFINITIONS["latency_l_resp"]["definition"] == lresp and pp["artificial_persistence_in_baseline"] is False and pp["on_supported_for_comparison"] is False and pp["comparison_persistence"] == "off"
    assert campaign_spec.SPEC["advisor_approved"] is False                                              # aprobar una decisión no marca la spec completa como aprobada
    assert "B5" in {b.id for b in guards.evaluate({"persist_policy": "on"}) if b.critical}               # la política efectiva del contraste debe seguir siendo OFF
    monkeypatch.setitem(pp, "artificial_persistence_in_baseline", True)
    assert "B5" in _crit()                                                                               # persistencia artificial en el baseline: incoherente con la decisión
    monkeypatch.setitem(pp, "artificial_persistence_in_baseline", False)
    monkeypatch.setitem(defs.DEFINITIONS, "latency_l_resp", {**defs.DEFINITIONS["latency_l_resp"], "definition": "L_resp = petición HTTP → último byte, sin persistencia síncrona"})
    assert "B5" in _crit() and "L_resp" in _crit()["B5"].reason                                          # reformular L_resp para que OFF parezca literal NO desbloquea


def test_the_b5_state_function_never_lists_modifying_l_resp_or_enabling_baseline_persistence_as_a_way_out():
    src = inspect.getsource(guards.persistence_decision_state)
    assert "on_supported_for_comparison" in src and "artificial_persistence_in_baseline" in src
    st = guards.persistence_decision_state("off")
    assert st["blocking"] and st["pending_approval"] and any("sin aprobación del asesor" in r for r in st["reasons"])


# ═════════════════════════ 3 — aislamiento de Redis ═════════════════════════
@pytest.fixture
def redis_client():
    import redis
    from adaptation_swarm.config import SETTINGS
    c = redis.Redis.from_url(SETTINGS.redis_url)
    c.ping()
    return c


@pytest.fixture
def iso(redis_client):
    prefix = run_isolation.campaign_prefix(f"t-{uuid.uuid4().hex[:8]}")
    i = run_isolation.RedisRunIsolation(prefix, redis_client, quiesce_s=0.0, sleep=lambda s: None)
    yield i
    i.purge_namespace()


def _seed_run_state(c, prefix, tag):
    c.set(f"{prefix}log:{tag}", "x")
    c.hset(f"{prefix}state:{tag}", mapping={"k": 1})
    c.set(f"{prefix}seen:AG1:{tag}", "1")


def test_campaign_prefix_is_unambiguous_per_campaign_and_never_the_production_or_empty_prefix():
    a, b = run_isolation.campaign_prefix("camp-A"), run_isolation.campaign_prefix("camp-B")
    assert a != b and a == "oe2c:camp-A:" and run_isolation.campaign_prefix("a b/c") == "oe2c:a-b-c:"
    for bad in ("", "swarm:", "pilotd1-x:", "oe2c:", "oe2c::"):
        with pytest.raises(ValueError, match="fuera del namespace"):
            run_isolation.RedisRunIsolation(bad)
    with pytest.raises(ValueError, match="campaign_id vacío"):
        run_isolation.campaign_prefix("///")


def test_run_b_does_not_inherit_the_per_cycle_state_of_run_a_and_only_the_campaign_namespace_is_touched(iso, redis_client):
    p = iso.prefix
    other = run_isolation.campaign_prefix(f"other-{uuid.uuid4().hex[:6]}")
    redis_client.set(f"{other}log:keep", "intacto")                                                    # otra campaña
    redis_client.set(f"pilotd1-test-{uuid.uuid4().hex[:6]}:log:keep", "intacto")                       # dato histórico de otro prefijo
    redis_client.xadd(f"{p}agent:AG1", {"m": "1"})                                                     # infraestructura viva del servidor
    first = iso.reset("run-A")
    assert first["per_cycle_keys_found"] == 0 and first["per_cycle_keys_remaining"] == 0 and first["agent_streams_untouched"] == {f"{p}agent:AG1": 1}
    _seed_run_state(redis_client, p, "cycleA")                                                          # la corrida A deja estado por ciclo
    assert iso._keys(run_isolation.PER_CYCLE_KINDS)
    rep = iso.reset("run-B")                                                                            # antes de la corrida B
    assert rep["run_id"] == "run-B" and rep["per_cycle_keys_found"] == 3 and rep["per_cycle_keys_deleted"] == 3 and rep["per_cycle_keys_remaining"] == 0
    assert iso._keys(run_isolation.PER_CYCLE_KINDS) == [] and not redis_client.exists(f"{p}log:cycleA", f"{p}state:cycleA", f"{p}seen:AG1:cycleA")         # nada de A queda en B
    assert redis_client.xlen(f"{p}agent:AG1") == 1 and redis_client.get(f"{other}log:keep") == b"intacto"                                       # streams y otras campañas, intactos
    assert [k for k in redis_client.scan_iter(match="pilotd1-test-*")] and rep["cache_policy"].startswith("PENDING_METHODOLOGICAL_DECISION")
    for k in list(redis_client.scan_iter(match="pilotd1-test-*")) + [f"{other}log:keep"]:
        redis_client.delete(k)


def test_reset_fails_closed_when_keys_remain_or_the_server_never_quiets_down(redis_client):
    p = run_isolation.campaign_prefix(f"t-{uuid.uuid4().hex[:8]}")

    class Stubborn:                                            # cliente cuyo `delete` no borra nada
        def __init__(self, c):
            self.c = c

        def __getattr__(self, name):
            return (lambda *a, **k: 0) if name == "delete" else getattr(self.c, name)
    i = run_isolation.RedisRunIsolation(p, Stubborn(redis_client), quiesce_s=0.0, sleep=lambda s: None)
    try:
        _seed_run_state(redis_client, p, "c1")
        with pytest.raises(RuntimeError, match="aislamiento Redis fallido"):
            i.reset("r")
    finally:
        run_isolation.RedisRunIsolation(p, redis_client).purge_namespace()

    class Busy(run_isolation.RedisRunIsolation):               # un ciclo rezagado sigue escribiendo
        n = 0

        def _keys(self, kinds):
            Busy.n += 1
            return [f"k{Busy.n}".encode()]
    with pytest.raises(RuntimeError, match="no quedó quieto"):
        Busy(p, redis_client, quiesce_s=1.0, timeout_s=3.0, sleep=lambda s: None).wait_quiescent()


def test_purge_namespace_removes_only_this_campaign(iso, redis_client):
    other = run_isolation.campaign_prefix(f"o-{uuid.uuid4().hex[:6]}")
    _seed_run_state(redis_client, iso.prefix, "x")
    redis_client.xadd(f"{iso.prefix}agent:AG2", {"m": "1"})
    redis_client.set(f"{other}log:y", "1")
    rep = iso.purge_namespace()
    assert rep["keys_found"] == 4 and rep["keys_deleted"] == 4 and not list(redis_client.scan_iter(match=f"{iso.prefix}*")) and redis_client.get(f"{other}log:y") == b"1"
    redis_client.delete(f"{other}log:y")


def _prov_for(runs, users=(1,), campaign_id="C"):
    args = argparse.Namespace(experiment="oe2", campaign_id=campaign_id, runs=1, users=list(users), particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                              persist_policy="off", official=False)
    return hc.provenance(args, runs)


def _plan(**kw):
    return hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="C", profile_ids=IDS, **kw)


def test_execute_isolates_after_the_server_is_ready_and_before_the_load_and_records_the_result_per_run():
    runs = _plan(proposal_persistence_cost=True)
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT",
            "official": False, "oe2_official": False}
    order = []
    raw = ([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, "t_conv_ms": None, "metrics_ok": True} for i in range(800)], [])
    recs = hc.execute(runs, prov, warmup=10, window=60, log=lambda m: None, profile_ids=IDS,
                      ensure_server=lambda n, p: (order.append(("server", p)), {"persist_policy": p})[1], isolate=lambda r: (order.append(("isolate", r["run_id"])), {"run_id": r["run_id"], "per_cycle_keys_remaining": 0})[1],
                      do_run=lambda r, w, win: (order.append(("load", r["run_id"])), raw)[1])
    assert [o[0] for o in order] == ["server", "isolate", "load"] * 3 and len(recs) == 3
    for r in recs:
        assert r["redis_isolation"]["run_id"] == r["run_id"] and r["redis_isolation"]["per_cycle_keys_remaining"] == 0 and r["persist_policy_effective"] == r["persist_policy"]
    on = [r for r in recs if r["persist_policy"] == "on"]
    assert len(on) == 1 and on[0]["persist_policy_effective"] == "on"


def test_a_failing_isolation_stops_the_campaign_before_any_load_is_generated():
    runs = _plan()
    prov = {"campaign_id": "C", "campaign_spec": campaign_spec.identity(), "code": {"commit": "x"}, "hardware": {"cpu": "t"}, "definition_version": {"requirements": "v"}, "environment_class": "PILOT",
            "official": False, "oe2_official": False}
    loaded = []

    def boom(r):
        raise RuntimeError("aislamiento Redis fallido")
    with pytest.raises(RuntimeError, match="aislamiento Redis fallido"):
        hc.execute(runs, prov, warmup=10, window=60, log=lambda m: None, profile_ids=IDS, ensure_server=lambda n, p: None, isolate=boom, do_run=lambda r, w, win: loaded.append(r) or ([], []))
    assert loaded == []


def test_without_isolation_the_record_says_none_not_verified_and_the_server_receives_the_campaign_namespace_and_label(monkeypatch):
    class FakeProc:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass

    class FakeResp:
        def read(self):
            return json.dumps({"persist_policy": "on", "baseline_quality_in_request": False, "library_version": "v"}).encode()
    seen = {}
    import urllib.request
    with monkeypatch.context() as m:
        m.setattr(hc.subprocess, "Popen", lambda cmd, env=None, **kw: (seen.update(env=env), FakeProc())[1])
        m.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeResp())
        s = hc.ServerPerN("python", 8999, "k", redis_prefix="oe2c:C:", run_label="C")
        health = s.ensure(20, "on")
    assert seen["env"]["SWARM_REDIS_PREFIX"] == "oe2c:C:" and seen["env"]["SWARM_API_RUN_LABEL"] == "C" and seen["env"]["SWARM_API_PERSIST"] == "1"
    assert health["persist_policy"] == "on" and (health["server_instance"], health["server_restarted_before_run"], health["server_runs_served_before"]) == (1, True, 0)
    assert [(n, p, h["persist_policy"]) for n, p, h in s.health_log] == [(20, "on", "on")] and "server_instance" not in s.health_log[0][2]            # el /health crudo no se contamina con la trazabilidad
    with monkeypatch.context() as m:
        seen.clear()
        m.setattr(hc.subprocess, "Popen", lambda cmd, env=None, **kw: (seen.update(env=env), FakeProc())[1])
        m.setattr(urllib.request, "urlopen", lambda req, timeout=None: FakeResp())
        hc.ServerPerN("python", 8999, "k").ensure(20, "on")                                             # sin prefijo ni etiqueta: no se inventan variables
        assert "SWARM_REDIS_PREFIX" not in seen["env"] or seen["env"]["SWARM_REDIS_PREFIX"] == __import__("os").environ.get("SWARM_REDIS_PREFIX")
        assert seen["env"].get("SWARM_API_RUN_LABEL") == __import__("os").environ.get("SWARM_API_RUN_LABEL")


# ═════════════════════════ 4 y 5 — provenance ═════════════════════════
def test_postgresql_is_recorded_per_condition_and_never_declared_unused_when_an_on_condition_exists(monkeypatch):
    monkeypatch.setattr(code_state, "_postgres_version", lambda: "PostgreSQL 16.4")
    assert code_state.software_report("off")["postgresql"] == "not_used_persistence_off"
    assert code_state.software_report({"off"})["postgresql"] == "not_used_persistence_off"
    both = code_state.software_report({"off", "on"})["postgresql"]
    assert both == {"off": "not_used_persistence_off", "on": "PostgreSQL 16.4"}
    prov_on = _prov_for(_plan(proposal_persistence_cost=True))
    assert prov_on["software"]["postgresql"] == both and prov_on["persistence_conditions"]["proposal_cost"] == "on"
    prov_off = _prov_for(_plan())
    assert prov_off["software"]["postgresql"] == "not_used_persistence_off" and prov_off["persistence_conditions"]["proposal_cost"] is None
    monkeypatch.setattr(code_state, "_postgres_version", lambda: code_state.UNAVAILABLE)
    prov_gap = _prov_for(_plan(proposal_persistence_cost=True))
    assert "software.postgresql.on" in code_state.provenance_gaps(prov_gap) and "B12" in {b.id for b in guards.evaluate(prov_gap) if b.critical}      # no se falsifica: sin versión es un hueco
    assert "software.postgresql.on" not in code_state.provenance_gaps(_prov_for(_plan()))


@pytest.mark.integration
def test_the_real_postgres_version_is_read_when_the_server_answers():
    v = code_state._postgres_version()
    assert v.startswith("PostgreSQL") or v == code_state.UNAVAILABLE                                  # nunca un valor inventado


def test_provenance_required_now_includes_persistence_roles_and_redis_isolation_and_a_complete_provenance_has_no_gaps(monkeypatch):
    monkeypatch.setattr(code_state, "_postgres_version", lambda: "PostgreSQL 16.4")
    for field in ("persistence_conditions.comparison", "persistence_conditions.roles", "run_roles", "redis_isolation.prefix", "redis_isolation.mechanism"):
        assert field in code_state.PROVENANCE_REQUIRED
    prov = _prov_for(_plan(proposal_persistence_cost=True), campaign_id="Camp 1")
    assert code_state.provenance_gaps(prov) == []
    assert prov["redis_isolation"]["prefix"] == run_isolation.campaign_prefix("Camp 1") and prov["redis_isolation"]["mechanism"] == run_isolation.MECHANISM
    roles = prov["run_roles"]
    assert set(roles) == {"swarm|u1|N20", "decision_table|u1|N20", "swarm|u1|N20|persON"}
    assert roles["swarm|u1|N20|persON"] == {"system": "swarm", "system_role": "proposal", "persist_policy": "on", "persistence_condition": "proposal_cost_on", "comparison_role": "proposal_persistence_cost",
                                            "confirmatory_role": "descriptive_cost_measurement"}
    assert roles["decision_table|u1|N20"]["comparison_role"] == "swarm_vs_decision_table_contrast" and roles["decision_table|u1|N20"]["persist_policy"] == "off"
    broken = {k: v for k, v in prov.items() if k != "run_roles"}
    assert "run_roles" in code_state.provenance_gaps(broken)                                           # lo que falta SÍ se reporta


def test_required_run_fields_include_the_effective_policy_and_isolation_and_the_stub_provides_them():
    assert {"persist_policy_effective", "redis_isolation", "system_role", "comparison_role", "confirmatory_role", "persistence_condition"} <= set(guards.REQUIRED_RUN_FIELDS) and not hc.missing_run_fields()


def test_effective_server_state_is_kept_per_policy_and_every_server_must_match_the_registered_library():
    prov = _prov_for(_plan(proposal_persistence_cost=True))
    lib = prov["library"]["version"]
    good = [(20, "off", {"library_version": lib, "persist_policy": "off", "baseline_quality_in_request": False}), (20, "on", {"library_version": lib, "persist_policy": "on", "baseline_quality_in_request": False})]
    hc.record_effective_server(prov, good)
    assert prov["server"]["library_version_matches"] is True and set(prov["server"]["effective_by_policy"]) == {"off", "on"} and prov["server"]["effective_by_policy"]["on"]["persist_policy"] == "on"
    bad = [good[0], (20, "on", {**good[1][2], "library_version": "otra"})]
    hc.record_effective_server(prov, bad)
    assert prov["server"]["library_version_matches"] is False and "B12" in {b.id for b in guards.evaluate(prov) if b.critical}
    hc.record_effective_server(prov, {"library_version": lib, "persist_policy": "off", "baseline_quality_in_request": False})                  # forma antigua (un solo /health): sigue funcionando
    assert prov["server"]["library_version_matches"] is True


def test_final_git_state_is_recorded_compared_with_the_start_and_a_change_during_the_campaign_is_reported(monkeypatch):
    prov = _prov_for(_plan())
    start_fp = dict(prov["campaign_source_fingerprints"])
    monkeypatch.setattr(code_state, "git_state", lambda repo=None: {"dirty": prov["code_state"]["dirty"], "modified_paths": prov["code_state"]["modified_paths"], "method": "git status --porcelain"})
    monkeypatch.setattr(code_state, "source_fingerprints", lambda sources=code_state.CAMPAIGN_SOURCES: start_fp)
    assert code_state.completion_gaps(prov) == [c for c in code_state.PROVENANCE_REQUIRED_AT_END]       # antes de verificar: faltan los tres
    code_state.final_code_state(prov)
    assert prov["code_state_final"]["unchanged_since_start"] is True and code_state.completion_gaps(prov) == []
    monkeypatch.setattr(code_state, "source_fingerprints", lambda sources=code_state.CAMPAIGN_SOURCES: {**start_fp, "adaptation_swarm/oe/http_campaign.py": "0" * 64})
    code_state.final_code_state(prov)
    assert prov["code_state_final"]["unchanged_since_start"] is False and any("cambió durante la campaña" in g for g in code_state.completion_gaps(prov))
    monkeypatch.setattr(code_state, "git_state", lambda repo=None: {"dirty": None, "modified_paths": None})
    code_state.final_code_state(prov)
    assert prov["code_state_final"]["unchanged_since_start"] is False                                  # git desconocido nunca cuenta como «sin cambios»


# ═════════════════════════ 6 a 8 — lo que NO se tocó y sigue pendiente ═════════════════════════
def test_pending_methodological_decisions_are_documented_in_spec_provenance_and_dry_run_and_not_decided(capsys, tmp_path):
    pend = campaign_spec.SPEC["oe2"]["pending_methodological_decisions"]
    joined = " | ".join(pend)
    for key in ("estadístico de latencia", "unidad estadística definitiva", "hipótesis estadística formal de OE2", "aprobación de B1", "hardware objetivo (P6)"):        # lo que SIGUE pendiente tras F.2.3
        assert key in joined, key
    assert "REQUIERE RESPALDO DEL ASESOR" in joined and "pareamiento" not in joined and "cold/warm" not in joined                                              # las decisiones internas ya no figuran como pendientes
    assert _prov_for(_plan())["pending_methodological_decisions"] == pend
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(tmp_path / "never"), "--runs", "1", "--users", "1", "--dry-run"])
    text = capsys.readouterr().out
    d = json.loads(text[text.index("{"):])
    assert d["pending_methodological_decisions"] == pend and d["redis_isolation"]["prefix"] == "oe2c:dry:" and not (tmp_path / "never").exists()


def test_statistics_error_handling_and_the_indicator_boundary_are_exactly_as_before():
    assert "independent_comparison" in inspect.getsource(o2.runs_comparison) and "paired_comparison" in inspect.getsource(o2.paired_log_by_profile)       # pareado/independiente: sin cambios
    assert 'p = {h: v["p_value"] for h, v in hypotheses.items() if v.get("p_value") is not None}' in inspect.getsource(o2.holm_family)                  # `m` = hipótesis testables (pendiente)
    src = inspect.getsource(hw.summarize_run)
    assert "ok = [r for r in win if r[\"ok\"]]" in src and 'lat = [r["response_ms"] for r in ok]' in src                                              # P95 solo de las correctas (pendiente)
    c = time_contract.TTFC_CONTRACT
    assert c["start"]["swarm"] == "fin de `step_receive` de AG0 (RF01 validado y ciclo registrado): `t_start_ns`" and c["stop"]["swarm"].startswith("entrada de `step_finalize` de AG0")
    assert c["swarm_formula"].startswith("(t_search_ns − t_start_ns)/1e6 + t_conv_ms") and c["condition"]["id"] == "isolated_inprocess"
    assert any("ASIMETRÍA CONOCIDA" in x for x in time_contract.KNOWN_LIMITS) and c["known_asymmetries"]
    assert set(conventional.SYSTEM_ROLES) == {"decision_table", "rules", "bruteforce"} and "conventional_independent" == conventional.SYSTEM_ROLES["decision_table"]
