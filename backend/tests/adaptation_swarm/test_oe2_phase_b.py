"""OE2 Fase B: contrato de tiempo comparable (decision_ms vs T_conv), secuencia determinista de perfiles, persistencia equivalente, y campaña HTTP con propuesta + convencional independiente.
Sin campañas: solo plan/dry-run, E/S inyectada y la pila real para las respuestas HTTP. Nada de esto genera resultados oficiales."""

import ast
import hashlib
import inspect
import json
import random
import subprocess
from pathlib import Path

import httpx
import pytest

import adaptation_swarm.api.router as router_mod
from adaptation_swarm.analysis import d11c_campaign
from adaptation_swarm.oe import campaign_spec, code_state, http_campaign as hc, http_window as hw, profile_sequence as ps, runner, time_contract
from adaptation_swarm.oe.conditions import oe2_systems
from app.main import app

BACK = Path(__file__).resolve().parents[2]
IDS = [f"p{i}" for i in range(100)]
KEY = "test-key-b"


# ── B.1 contrato de tiempo ──────────────────────────────────────────────────────────────────────────────────
def test_time_contract_keeps_t_conv_proposal_only_and_defines_the_common_metric():
    assert time_contract.COMMON_METRIC == "decision_ms" and time_contract.STATUS.endswith("UNVALIDATED") and "NOT_ADVISOR_APPROVED" in time_contract.STATUS
    assert time_contract.VALIDATION_STATUS == "PENDING_METHODOLOGICAL_VALIDATION" and time_contract.T_CONV_EQUIVALENCE == "NOT_ESTABLISHED"
    assert time_contract.response_contract("proposal") == {"version": "oe2-time-contract-v1", "candidate_common_metric": "decision_ms", "validation": "PENDING_METHODOLOGICAL_VALIDATION", "t_conv_applies": True}
    for role in ("conventional_independent", "swarm_heuristic_ablation", "reference_optimum"):
        assert time_contract.response_contract(role)["t_conv_applies"] is False
    d = time_contract.DEFINITIONS
    assert "Solo propuesta" in d["t_conv_ms"] and "engine.initialize" in d["t_conv_ms"] and "= t_conv_ms de AG0 (copiado)" in d["decision_ms"]
    assert "NO es T_conv" in d["decision_ms"] and "candidata" in d["decision_ms"] and "validación pendiente" in d["decision_ms"]       # nunca como sinónimo de T_conv
    assert any("inicialización de partículas" in x for x in time_contract.KNOWN_LIMITS) and any("NO validada" in x for x in time_contract.KNOWN_LIMITS)


def test_in_process_swarm_row_copies_t_conv_into_decision_ms_without_changing_it():
    class M:
        n_messages, comm_overhead_ms, inflight_overlap = 3, 1.0, True

    class R:
        status, stop_reason, k_stop, t_conv_ms, total_ms, g_best_F, g_best_S, predicted_dominant, metrics = "completed", "epsilon", 4, 123.456, 200.0, 0.5, [1] * 8, "code", M()
        package, W, iterations, error = None, None, [], None
    row = runner._swarm_row(R())
    assert row["t_conv_ms"] == 123.456 and row["decision_ms"] == 123.456


# ── B.2 secuencia determinista ──────────────────────────────────────────────────────────────────────────────
def test_profile_sequence_is_deterministic_depends_on_seed_and_user_and_not_on_the_system():
    a = ps.user_sequence(26100501, 0, 3, 40, IDS)
    assert a == ps.user_sequence(26100501, 0, 3, 40, IDS)                                            # misma configuración => misma secuencia
    assert a != ps.user_sequence(26100502, 0, 3, 40, IDS) and a != ps.user_sequence(26100501, 0, 4, 40, IDS) and a != ps.user_sequence(26100501, 1, 3, 40, IDS)
    assert ps.sequence_sha256(7, 5, 30, IDS) == ps.sequence_sha256(7, 5, 30, IDS) != ps.sequence_sha256(8, 5, 30, IDS)
    assert "system" not in inspect.signature(ps.user_sequence).parameters and "system" not in inspect.signature(ps.sequence_sha256).parameters
    assert a[:10] == ps.user_sequence(26100501, 0, 3, 10, IDS)                                       # la posición de la petición fija su perfil: prefijos consistentes


def test_profile_sequence_does_not_use_object_identity_memory_or_time():
    src = Path(inspect.getsourcefile(ps)).read_text(encoding="utf-8")
    tree = ast.parse(src)
    calls = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)} | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    assert not calls & {"id", "time", "monotonic", "perf_counter", "urandom", "getpid", "uuid4", "now"}
    ltree = ast.parse((BACK / "loadtest" / "locustfile.py").read_text(encoding="utf-8"))
    lcalls = {n.func.id for n in ast.walk(ltree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "id" not in lcalls                                                                         # ya no se siembra con id(self) (llamada real, no solo texto)


def _locust_algorithm():
    tree = ast.parse((BACK / "loadtest" / "locustfile.py").read_text(encoding="utf-8"))
    keep = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in ("_user_rng", "_next_request")) or
            (isinstance(n, ast.Assign) and any(getattr(t, "id", None) in ("SEQUENCE_ALGORITHM", "REPLICATE_MAX") for t in n.targets))]
    ns = {"hashlib": hashlib, "random": random}
    exec(compile(ast.Module(body=keep, type_ignores=[]), "locustfile_sequence", "exec"), ns)
    return ns


def test_locustfile_copy_of_the_algorithm_matches_the_canonical_module():
    ns = _locust_algorithm()
    assert ns["SEQUENCE_ALGORITHM"] == ps.ALGORITHM and ns["REPLICATE_MAX"] == ps.REPLICATE_MAX
    for seed, worker, user in ((26100501, 0, 0), (26100501, 0, 7), (5, 2, 3), (99, 0, 11)):
        rng_a, rng_b = ns["_user_rng"](seed, worker, user), ps.user_rng(seed, worker, user)
        got = [ns["_next_request"](rng_a, len(IDS)) for _ in range(25)]
        assert got == [ps.next_request(rng_b, len(IDS)) for _ in range(25)]
        assert [(IDS[i], r) for i, r in got] == ps.user_sequence(seed, worker, user, 25, IDS)


def test_every_request_draws_profile_and_replicate_so_baseline_and_proposal_stay_aligned():
    src = (BACK / "loadtest" / "locustfile.py").read_text(encoding="utf-8")
    body = ast.get_source_segment(src, next(n for n in ast.parse(src).body if isinstance(n, ast.ClassDef)))
    assert body.index("_next_request(self.rng") < body.index("self.client.post") and "replicate={replicate}" in body and "context=context" in body


def test_logged_sequence_is_verified_against_the_expected_one_and_mismatches_are_detected():
    expected = ps.user_sequence(11, 0, 2, 20, IDS)
    logged = [{"user_index": 2, "seq_pos": i, "profile_id": pid} for i, (pid, _) in enumerate(expected)]
    assert ps.check_logged(logged, 11, IDS) == {"checked": 20, "mismatches": 0, "unindexed": 0}
    logged[5] = {**logged[5], "profile_id": "p_otro"}
    logged.append({"profile_id": "x"})
    assert ps.check_logged(logged, 11, IDS) == {"checked": 20, "mismatches": 1, "unindexed": 1}
    s = hw.summarize_run([{"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": True, "timeout": False, "decision_ms": 0.1, **l} for i, l in enumerate(logged * 40)], [], users=1,
                         system="decision_table", run_id="t", batch_seed=11, profile_ids=IDS)
    assert s["profile_sequence_check"]["mismatches"] > 0 and s["decision_ms_mean"] == pytest.approx(0.1)


# ── B.3 persistencia ────────────────────────────────────────────────────────────────────────────────────────
class _FakeProc:
    def poll(self):
        return None

    def terminate(self):
        pass

    def wait(self, timeout=None):
        pass


def test_server_is_started_with_persistence_off_and_the_effective_policy_is_verified(monkeypatch):
    launched = {}

    def popen(cmd, env=None, **kw):
        launched["env"] = env
        return _FakeProc()

    class Resp:
        def __init__(self, policy):
            self.policy = policy

        def read(self):
            return json.dumps({"status": "ok", "persist_policy": self.policy, "baseline_quality_in_request": False}).encode()
    seen = {}

    def urlopen(req, timeout=None):
        seen["key"] = req.get_header("X-swarm-key")
        return Resp(seen.get("policy", "off"))
    monkeypatch.setattr(hc.subprocess, "Popen", popen)
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    monkeypatch.setenv("SWARM_API_PERSIST", "1")                                                    # el entorno del usuario no puede colar persistencia en la campaña
    server = hc.ServerPerN("python", 8999, "k")
    server.ensure(20)
    assert launched["env"]["SWARM_API_PERSIST"] == "0" and launched["env"]["SWARM_API_N_PARTICLES"] == "20" and seen["key"] == "k"
    seen["policy"] = "on"
    other = hc.ServerPerN("python", 8999, "k", ready_s=5)
    with pytest.raises(RuntimeError, match="política de persistencia efectiva 'on'"):
        other.ensure(30)


def test_only_the_off_policy_is_supported_for_comparison_and_it_is_recorded_everywhere():
    assert hc.PERSIST_POLICIES == ("off",) and campaign_spec.SPEC["oe2"]["persist_policy"]["on_supported_for_comparison"] is False
    assert all(r["persist_policy"] == "off" for r in hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=list(hc.DEFAULT_OE2_SYSTEMS), order="sequential", campaign_id="C", profile_ids=IDS))


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SWARM_API_KEY", KEY)
    monkeypatch.setenv("SWARM_API_PERSIST", "0")
    monkeypatch.setenv("SWARM_REDIS_PREFIX", "swarm-phaseb:")
    router_mod._stack = None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
    await router_mod.shutdown_stack()
    if router_mod._stack is None:
        from adaptation_swarm.bus.redis_bus import RedisBus
        b = await RedisBus(prefix="swarm-phaseb:").connect()
        await b.purge_prefix()
        await b.close()


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_proposal_response_exposes_decision_ms_equal_to_t_conv_and_the_effective_persistence(client, slice_profile):
    r = await client.post("/api/adaptation", json=slice_profile.model_dump(mode="json"), headers={"X-Swarm-Key": KEY})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["t_conv_ms"] > 0 and out["decision_ms"] == out["t_conv_ms"] and out["system"] == "swarm" and out["system_role"] == "proposal"
    assert out["time_contract"] == {"version": "oe2-time-contract-v1", "candidate_common_metric": "decision_ms", "validation": "PENDING_METHODOLOGICAL_VALIDATION", "t_conv_applies": True} and out["persistence"] == "off"
    assert hw.extract_cycle_metrics(out) == {"shape": "swarm", "t_conv_ms": out["t_conv_ms"], "decision_ms": out["decision_ms"], "k_stop": out["k_stop"], "profile_id": out["profile_id"]}
    health = (await client.get("/api/adaptation/health", headers={"X-Swarm-Key": KEY})).json()
    assert health["persist_policy"] == "off"


# ── B.4–B.8 sistemas, spec, runner, campaña ─────────────────────────────────────────────────────────────────
def test_runner_validity_requires_the_proposal_and_the_independent_conventional():
    kw = dict(hw={"vcpu": 8, "ram_gib": 32.0}, n_profiles=100, k=10, batches=5, warmup=10)
    ok = runner.validity("oe2", conditions=oe2_systems(), **kw)["conditions"]
    assert ok["propuesta_y_convencional_independiente_presentes"] is True
    for incomplete in ([c for c in oe2_systems() if c.system != "decision_table"], [c for c in oe2_systems() if c.system == "swarm"]):
        v = runner.validity("oe2", conditions=incomplete, **kw)
        assert v["conditions"]["propuesta_y_convencional_independiente_presentes"] is False and any("convencional_independiente" in r for r in v["reasons"])
    assert [c.system for c in oe2_systems()] == ["swarm", "rules", "bruteforce", "decision_table"]    # rules y bruteforce se conservan (contrastes auxiliares)


def test_spec_records_decision_table_as_the_only_conventional_and_rules_bruteforce_are_not():
    oe2 = campaign_spec.SPEC["oe2"]
    conventional = [s for s, role in oe2["system_roles"].items() if role == "conventional_independent"]
    assert conventional == ["decision_table"] == [oe2["comparator_primary"]] and "rules" not in conventional and "bruteforce" not in conventional
    assert oe2["system_roles"]["rules"] == "swarm_heuristic_ablation" and oe2["system_roles"]["bruteforce"] == "reference_optimum"
    assert campaign_spec.SPEC["advisor_approved"] is False and campaign_spec.STATUS.startswith("TECHNICAL_INTERNAL")


def _args(**kw):
    import argparse
    base = dict(experiment="oe2", campaign_id="dry", runs=10, users=[1, 10, 25, 50], particles=[20], systems=list(hc.DEFAULT_OE2_SYSTEMS), warmup=10.0, window=60.0, base_seed=26100501,
                order="randomized-blocks", persist_policy="off", official=False)
    return argparse.Namespace(**{**base, **kw})


def test_dry_run_plan_shows_proposal_conventional_sequence_persistence_metrics_and_provenance(capsys, tmp_path):
    out_dir = tmp_path / "never_created"
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(out_dir), "--runs", "3", "--users", "1,10,25,50", "--dry-run"])
    text = capsys.readouterr().out
    d = json.loads(text[text.index("{"):])
    assert not out_dir.exists()                                                                       # el dry-run no escribe nada
    assert d["proposal"] == ["swarm"] and d["conventional_independent"] == ["decision_table"] and d["auxiliary_contrasts"] == [] and d["official"] is False
    assert d["profile_sequence"]["same_sequence_for_all_systems"] is True and len(d["profile_sequence"]["example_sha256_run00"]) == 64 and d["persist_policy"] == "off"
    assert d["metrics"]["candidate_common_time_metric"] == "decision_ms" and d["metrics"]["candidate_validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and d["metrics"]["t_conv_equivalence"] == "NOT_ESTABLISHED" and d["metrics"]["t_conv_ms"].startswith("solo la propuesta")
    assert d["load_conditions"] == {"contrast_users_le_25": [1, 10, 25], "stress_users_gt_25": [50]} and d["configuration"]["swarm_N"] == [20]
    assert {"code_state", "campaign_source_fingerprints", "systems", "time_contract", "profile_sequence", "persist_policy", "hardware"} <= set(d["provenance_prepared"])
    assert d["campaign"] == "OE2-PREPARATION-NOT-EXECUTED" and any("contrato de tiempo" in r for r in d["official_refusals"]) and d["oe2_official"] is False


def test_official_flag_is_still_refused_and_writes_nothing(tmp_path):
    out_dir = tmp_path / "official_never"
    with pytest.raises(SystemExit, match="CAMPAÑA OFICIAL RECHAZADA"):
        hc.main(["oe2", "--campaign-id", "x", "--out-dir", str(out_dir), "--official"])
    assert not out_dir.exists()


def test_provenance_records_real_code_state_fingerprints_roles_and_sequence_hashes():
    runs = hc.plan("oe2", runs=2, base_seed=3, users=[1, 10], particles=[20], systems=["swarm", "decision_table", "rules"], order="sequential", campaign_id="P", profile_ids=IDS)
    prov = hc.provenance(_args(runs=2, users=[1, 10], systems=["swarm", "decision_table", "rules"]), runs)
    assert prov["systems"] == {"decision_table": "conventional_independent", "rules": "swarm_heuristic_ablation", "swarm": "proposal"}
    assert prov["code_state"]["dirty"] in (True, False, None) and prov["code_state"]["method"] == "git status --porcelain" and prov["persist_policy"] == "off"
    fp = prov["campaign_source_fingerprints"]
    assert set(fp) == set(code_state.CAMPAIGN_SOURCES) and all(len(h) == 64 for h in fp.values())
    assert fp["adaptation_swarm/baselines/decision_table.py"] == hashlib.sha256((BACK / "adaptation_swarm/baselines/decision_table.py").read_bytes()).hexdigest()
    assert prov["time_contract"]["candidate_common_metric"] == "decision_ms" and prov["time_contract"]["validation"] == "PENDING_METHODOLOGICAL_VALIDATION" and prov["campaign_spec"]["sha256"] == campaign_spec.spec_hash() and prov["official"] is False
    assert set(prov["profile_sequence"]["sha256_by_run_index_and_load"]) == {"r00|u1", "r00|u10", "r01|u1", "r01|u10"}


@pytest.mark.parametrize("dirty, stdout", [(False, ""), (True, " M x.py\n")])
def test_code_state_reports_the_real_tree_and_never_assumes_clean(monkeypatch, dirty, stdout):
    monkeypatch.setattr(code_state.subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout=stdout, stderr=""))
    assert code_state.git_state()["dirty"] is dirty

    def boom(*a, **k):
        raise OSError("sin git")
    monkeypatch.setattr(code_state.subprocess, "run", boom)
    assert code_state.git_state()["dirty"] is None


def test_d11c_stays_separate_unofficial_and_untouched_by_the_oe2_contract():
    tree = ast.parse(Path(inspect.getsourcefile(d11c_campaign)).read_text(encoding="utf-8"))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not imported & {"adaptation_swarm.oe.time_contract", "adaptation_swarm.oe.campaign_spec", "adaptation_swarm.oe.http_campaign", "adaptation_swarm.oe.oe2_confirmatory"}
    assert d11c_campaign.CAMPAIGN == "D11C-EMPIRICAL-BASELINE" and "decision_ms" not in Path(inspect.getsourcefile(d11c_campaign)).read_text(encoding="utf-8")
