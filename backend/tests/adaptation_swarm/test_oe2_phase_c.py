"""OE2 Fase C — cierre de bloqueos TÉCNICOS (B3, B6, B7, B11, B12, B14). B1, B5 y B13 son decisiones metodológicas CONGELADAS: aquí solo se comprueba que los guards las REPRESENTAN, no que se resuelvan.
Sin campañas oficiales: servidores falsos locales, E/S inyectada y la pila real solo donde hace falta."""

import argparse
import csv
import http.server
import json
import os
import subprocess
import sys
import threading
from importlib import metadata
from pathlib import Path

import httpx
import numpy as np
import pytest

import adaptation_swarm.api.router as router_mod
from adaptation_swarm.analysis import baseline_bruteforce as bb
from adaptation_swarm.baselines import conventional as conv
from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.gold import rubric_v3
from adaptation_swarm.oe import campaign_guards as guards, campaign_spec, code_state, definitions as defs, http_campaign as hc, http_window as hw, oe2_confirmatory as o2, runner, time_contract
from adaptation_swarm.oe.conditions import Condition
from adaptation_swarm.profiles.generator import read_dataset
from app.main import app

BACK = Path(__file__).resolve().parents[2]
IDS = [f"p{i}" for i in range(100)]
KEY = "test-key-c"


# ═════════════════════════════ B3 — 𝓕 de reporte fuera de la región medida ═════════════════════════════
@pytest.fixture
def spy(monkeypatch):
    """Registra si `evaluate` (𝓕) se ejecuta DENTRO de una llamada a `ConventionalAdapter.adapt` (la región medida) o fuera."""
    state = {"inside": False, "calls": []}
    real_eval, real_adapt = conv.evaluate, conv.ConventionalAdapter.adapt
    monkeypatch.setattr(conv, "evaluate", lambda *a, **k: (state["calls"].append(state["inside"]), real_eval(*a, **k))[1])

    def wrapped(self, profile, **kw):
        state["inside"] = True
        try:
            return real_adapt(self, profile, **kw)
        finally:
            state["inside"] = False
    monkeypatch.setattr(conv.ConventionalAdapter, "adapt", wrapped)
    return state


@pytest.mark.requires_library_audio
@pytest.mark.parametrize("system", ["decision_table", "rules"])
def test_quality_is_not_evaluated_inside_the_measured_call_and_is_reconstructible_outside(store, slice_profile, spy, system):
    adapter = conv.ConventionalAdapter(store, system)
    r = adapter.adapt(slice_profile, report_quality=False)
    assert r.status == "completed" and r.F is None and spy["calls"] == []                         # la región medida NO calcula 𝓕
    assert r.decision_ms > 0 and r.total_ms >= r.decision_ms
    F = adapter.evaluate_quality(slice_profile, r.S)                                              # fuera de la región medida
    assert spy["calls"] == [False] and F == adapter.adapt(slice_profile).F                         # mismo 𝓕 que el reporte por defecto (que lo calcula DESPUÉS de cerrar los cronómetros)


@pytest.mark.requires_library_audio
async def test_in_process_runner_times_the_call_without_quality_and_fills_it_after(store, spy):
    profs = read_dataset(bb.DEFAULT_PROFILES)[:3]
    obs, _ = await runner.run_condition(store, Condition(system="decision_table"), profs, k=1, batches=1, warmup=0, batch_seed=runner.DEFAULT_BATCH_SEED, fw=FitnessWeights(), log=lambda *_: None)
    assert spy["calls"] and not any(spy["calls"])                                                   # 𝓕 se evaluó (para reportar), pero NUNCA dentro de `adapt`
    adapter = conv.ConventionalAdapter(store, "decision_table")
    for row in obs:
        assert row["status"] == "completed" and row["F"] == pytest.approx(adapter.evaluate_quality(next(p for p in profs if p.profile_id == row["profile_id"]), row["S"]))
        assert row["decision_ms"] > 0 and row["t_conv_ms"] is None


@pytest.fixture
async def client(monkeypatch):
    monkeypatch.setenv("SWARM_API_KEY", KEY)
    monkeypatch.setenv("SWARM_API_PERSIST", "0")
    monkeypatch.setenv("SWARM_REDIS_PREFIX", "swarm-phasec:")
    router_mod._stack = None
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c
    await router_mod.shutdown_stack()
    if router_mod._stack is None:
        from adaptation_swarm.bus.redis_bus import RedisBus
        b = await RedisBus(prefix="swarm-phasec:").connect()
        await b.purge_prefix()
        await b.close()


@pytest.mark.integration
@pytest.mark.requires_library_audio
@pytest.mark.parametrize("system", ["decision_table", "rules"])
async def test_baseline_endpoint_does_not_evaluate_quality_inside_the_request(client, slice_profile, monkeypatch, system):
    def boom(*a, **k):
        raise AssertionError("𝓕 evaluada dentro de la petición medida del baseline")
    monkeypatch.setattr(conv, "evaluate", boom)
    r = await client.post(f"/api/adaptation/baseline/{system}", json=slice_profile.model_dump(mode="json"), headers={"X-Swarm-Key": KEY})
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["g_best"]["F"] is None and out["quality_in_request"] is False and out["g_best"]["S"]                 # la configuración sí viaja: 𝓕 se reconstruye desde S
    health = (await client.get("/api/adaptation/health", headers={"X-Swarm-Key": KEY})).json()
    assert health["baseline_quality_in_request"] is False


def test_guard_b3_follows_the_real_state_of_the_baseline_path(monkeypatch):
    assert "B3" not in {b.id for b in guards.evaluate(None)}
    monkeypatch.setattr(conv, "BASELINE_REPORTS_QUALITY_IN_REQUEST", True)
    assert "B3" in {b.id for b in guards.evaluate(None) if b.critical}
    monkeypatch.setattr(conv, "BASELINE_REPORTS_QUALITY_IN_REQUEST", False)
    prov = {"server": {"baseline_quality_in_request": True}}                                         # lo registrado para ESA ejecución también cuenta
    assert "B3" in {b.id for b in guards.evaluate(prov)}
    assert "B3" in {b.id for b in guards.evaluate({"server": {}})}                                    # no registrado = no verificado


# ═════════════════════════════ B6 — timeout de cliente ═════════════════════════════
def test_errors_are_classified_by_exception_type_so_a_timeout_is_never_confused_with_another_error():
    import requests
    CatchResponseError = type("CatchResponseError", (Exception,), {})                                  # mismo nombre de clase que el de Locust (no se importa locust en-proceso: gevent rompe pytest); el caso REAL va en el test con servidor falso
    assert hw.classify_error(None) == ""
    assert hw.classify_error(requests.exceptions.ReadTimeout("read timed out")) == "timeout"
    assert hw.classify_error(requests.exceptions.ConnectTimeout("x")) == "timeout"
    assert hw.classify_error(CatchResponseError("HTTP 502")) == "http_502"
    assert hw.classify_error(CatchResponseError("HTTP 500 timeout upstream")) == "http_500"             # la palabra «timeout» en el MENSAJE no lo convierte en timeout
    assert hw.classify_error(CatchResponseError("paquete multimodal incompleto")) == "incomplete_package"
    assert hw.classify_error(requests.exceptions.ConnectionError("refused")) == "exception_ConnectionError"
    assert hw.classify_error(ValueError("timeout")) == "exception_ValueError"


def _raw(n, kinds=(), decision=0.1):
    rows = []
    for i in range(n):
        kind = kinds[i % len(kinds)] if kinds else ""
        rows.append({"t_end_epoch_s": 1000 + i / 10, "response_ms": 5.0, "ok": kind == "", "timeout": kind == "timeout", "error_kind": kind, "decision_ms": decision if kind == "" else None,
                     "t_conv_ms": None, "metrics_ok": True})
    return rows


def test_summary_counts_timeouts_and_other_errors_separately():
    s = hw.summarize_run(_raw(900, ("", "", "timeout", "http_502", "")), [{"t_epoch_s": 1000.0 + t, "loadgen_cpu_percent": 10.0} for t in range(95)], users=1, system="decision_table", run_id="t")
    assert s["status"] == "ok" and s["error_count"] == s["errors"] and s["timeout_count"] == s["timeouts"] > 0
    assert s["errors_by_kind"] == {"timeout": s["timeout_count"], "http_502": s["errors_non_timeout"]} and s["errors"] == s["timeout_count"] + s["errors_non_timeout"]


class _Server:
    """Servidor HTTP local de prueba: `slow` responde tras 2 s (provoca timeout de cliente de 0,5 s); `502` responde 502 al instante."""

    def __init__(self, mode):
        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                if mode == "slow":
                    import time
                    time.sleep(2.0)
                self.send_response(200 if mode == "slow" else 502)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

            def log_message(self, *a):
                pass
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()


def _run_locust(port, raw_path, timeout_s):
    env = {**os.environ, "SWARM_API_KEY": "k", "SWARM_LOAD_RAW_CSV": str(raw_path), "SWARM_LOAD_SYSTEM": "decision_table", "SWARM_LOAD_BATCH_SEED": "5", "SWARM_LOAD_WORKER_INDEX": "0",
           "SWARM_LOAD_TIMEOUT_S": str(timeout_s), "PYTHONUTF8": "1"}
    subprocess.run([sys.executable, "-m", "locust", "-f", f"{BACK / 'loadtest' / 'locustfile.py'},{BACK / 'adaptation_swarm' / 'oe' / 'locust_raw_log.py'}", "--headless", "-u", "1", "-r", "1", "-t", "4s",
                    "--host", f"http://127.0.0.1:{port}"], env=env, cwd=str(BACK), capture_output=True, text=True, timeout=120)
    return hw.read_raw(Path(raw_path))


def test_a_real_client_timeout_is_recorded_as_timeout_and_a_502_is_not(tmp_path):
    slow = _Server("slow")
    try:
        rows = _run_locust(slow.port, tmp_path / "slow.csv", 0.5)
    finally:
        slow.close()
    assert rows and all(not r["ok"] and r["timeout"] and r["error_kind"] == "timeout" for r in rows)      # timeout REAL de cliente (Locust + requests), no simulado
    bad = _Server("502")
    try:
        rows502 = _run_locust(bad.port, tmp_path / "bad.csv", 0.5)
    finally:
        bad.close()
    assert rows502 and all(not r["ok"] and not r["timeout"] and r["error_kind"] == "http_502" for r in rows502)


def test_the_same_client_timeout_reaches_every_system_and_is_recorded(monkeypatch):
    seen = []
    with monkeypatch.context() as m:                                                                   # el parche de subprocess.run es global: se acota para no afectar a `git status` de la provenance
        m.setattr(hc.subprocess, "run", lambda cmd, env=None, **k: seen.append((env["SWARM_LOAD_SYSTEM"], env["SWARM_LOAD_TIMEOUT_S"])) or subprocess.CompletedProcess(cmd, 0))
        m.setattr(hc.http_window, "read_raw", lambda p: [])
        m.setattr(hc.http_window, "read_cpu", lambda p: [])
        run = hc.locust_runner("http://x", Path("l.py"), Path("p.py"), Path("."), "python", 12.5)
        for system in ("swarm", "decision_table"):
            run({"run_id": system, "seed": 1, "system": system, "load": 1}, 10.0, 60.0)
    assert seen == [("swarm", "12.5"), ("decision_table", "12.5")]
    args = argparse.Namespace(experiment="oe2", campaign_id="t", runs=1, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                              persist_policy="off", official=False, client_timeout=12.5)
    prov = hc.provenance(args, hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="t", profile_ids=IDS))
    assert prov["client_timeout_s"] == 12.5 and prov["client_timeout_status"] == "PROVISIONAL_TECHNICAL"


def test_guard_b6_blocks_a_missing_timeout_and_only_warns_when_it_is_provisional():
    assert not [b for b in guards.evaluate(None) if b.id == "B6" and b.critical]
    assert [b.critical for b in guards.evaluate(None) if b.id == "B6"] == [False]                       # provisional: aviso, no bloqueo
    assert [b.id for b in guards.evaluate({"client_timeout_s": None}) if b.id == "B6" and b.critical] == ["B6"]
    assert [b.id for b in guards.evaluate({"client_timeout_s": 0}) if b.id == "B6" and b.critical] == ["B6"]


# ═════════════════════════════ B7 — política del generador de carga ═════════════════════════════
def _cpu(peak, n=95):
    return [{"t_epoch_s": 1000.0 + t, "loadgen_cpu_percent": peak if t == 50 else 20.0} for t in range(n)]


def test_generator_policy_marks_saturated_or_unverifiable_runs_not_comparable_but_keeps_them():
    kw = dict(users=10, run_id="r")
    ok = hw.summarize_run(_raw(900), _cpu(60.0), system="swarm", **kw)
    sat = hw.summarize_run(_raw(900), _cpu(95.0), system="swarm", **kw)
    nocpu = hw.summarize_run(_raw(900), [], system="swarm", **kw)
    assert (ok["comparable"], ok["non_comparable_reason"]) == (True, None)
    assert (sat["comparable"], sat["non_comparable_reason"], sat["generator_saturated"]) == (False, "generator_saturated", True)
    assert (nocpu["comparable"], nocpu["non_comparable_reason"]) == (False, "generator_cpu_unavailable")        # no verificable ⇒ no se supone que esté bien
    assert sat["status"] == "ok" and sat["requests_ok"] > 0 and sat["latency_p95_ms"] is not None and sat["generator_policy"] == "generator-saturation-v1"       # se CONSERVA
    assert hw.GENERATOR_POLICY["threshold_percent"] == hw.LOADGEN_CPU_SATURATION == 90.0                         # el umbral ya existente, sin cambios


def test_generator_policy_is_symmetric_across_systems_and_has_no_system_dependent_branch():
    for peak in (60.0, 95.0):
        a = hw.summarize_run(_raw(900), _cpu(peak), users=10, system="swarm", run_id="a")
        b = hw.summarize_run(_raw(900), _cpu(peak), users=10, system="decision_table", run_id="b")
        assert (a["comparable"], a["non_comparable_reason"]) == (b["comparable"], b["non_comparable_reason"])
    assert "system" in hw.GENERATOR_POLICY["scope"] or "todos los sistemas" in hw.GENERATOR_POLICY["scope"]
    assert "prohibidas" in hw.GENERATOR_POLICY["manual_exclusions"]


def _http_records(saturated_at=None, systems=("swarm", "decision_table"), loads=(1, 10, 25), runs=6):
    rng = np.random.default_rng(0)
    recs = []
    for s, lat, thr in (("swarm", 900.0, 12.0), ("decision_table", 200.0, 300.0)):
        if s not in systems:
            continue
        for u in loads:
            for i in range(runs):
                bad = saturated_at is not None and (s, u, i) == saturated_at
                recs.append({"status": "ok", "system": s, "load": u, "users": u, "run_id": f"{s}-{u}-{i}", "latency_p95_ms": lat * float(np.exp(rng.normal(0, 0.05))), "throughput_rps": thr + float(rng.normal(0, 0.3)),
                             "decision_ms_mean": (130.0 if s == "swarm" else 0.02) * float(np.exp(rng.normal(0, 0.05))), "comparable": not bad,
                             "non_comparable_reason": "generator_saturated" if bad else None, "persist_policy": "off", "comparison_role": "swarm_vs_decision_table_contrast"})
    return recs


def test_a_generator_limited_load_leaves_the_confirmatory_family_for_both_systems_and_is_reported():
    res = o2.analyze([], _http_records(saturated_at=("decision_table", 10, 2)))
    prim = res["families"]["primary:swarm_vs_decision_table"]
    assert res["generator_limited_levels"] == {"10": ["generator_saturated"]} and res["n_http_runs_not_comparable"] == 1
    assert {h.split("@")[1] for h in prim["hypotheses"]} == {"u1", "u25"} and prim["m"] == 4                # u10 sale para AMBOS sistemas (aunque la propuesta no saturó)
    full = o2.analyze([], _http_records())
    assert full["generator_limited_levels"] == {} and {h.split("@")[1] for h in full["families"]["primary:swarm_vs_decision_table"]["hypotheses"]} == {"u1", "u10", "u25"}


def test_runs_without_a_comparable_flag_are_not_used_and_oe4_also_respects_the_policy():
    recs = _http_records()
    for r in recs:
        r.pop("comparable")
    res = o2.analyze([], recs)
    assert res["families"]["primary:swarm_vs_decision_table"]["m"] == 0 and res["n_http_runs_not_comparable"] == len(recs)       # no se supone comparable
    swarm = [{"status": "ok", "system": "swarm", "load": u, "swarm_N": n, "p95_ms": 500.0 + u, "throughput_http": 12.0, "error_rate": 0.0, "t_conv_ms_mean": 100.0, "comparable": u != 10}
             for u in (1, 10, 25) for n in (10, 20) for _ in range(3)]
    out = hc.analyze_oe4(swarm)
    assert out["runs_per_cell"] == [3] and {1, 25} == {r["load"] for r in swarm if r["comparable"]}


# ═════════════════════════════ B11 — integración HTTP → análisis ═════════════════════════════
def _prov(**kw):
    runs = hc.plan("oe2", runs=1, base_seed=1, users=[1], particles=[20], systems=["swarm", "decision_table"], order="sequential", campaign_id="C", profile_ids=IDS)
    args = argparse.Namespace(experiment="oe2", campaign_id="C", runs=1, users=[1], particles=[20], systems=["swarm", "decision_table"], warmup=10.0, window=60.0, base_seed=1, order="sequential",
                              persist_policy="off", official=False, **kw)
    return hc.provenance(args, runs), runs


def _fake_do_run(r, w, win):
    kind = r["system"] == "swarm"
    rows = [{"t_end_epoch_s": 1000 + i / 10, "response_ms": 200.0 if kind else 10.0, "ok": True, "timeout": False, "error_kind": "", "decision_ms": 128.0 if kind else 0.015,
             "t_conv_ms": 128.0 if kind else None, "metrics_ok": True, "profile_id": IDS[i % 100], "user_index": 0, "seq_pos": i} for i in range(900)]
    return rows, [{"t_epoch_s": 1000.0 + s, "loadgen_cpu_percent": 20.0} for s in range(95)]


def test_every_required_field_is_in_the_run_record_and_t_conv_is_never_copied_from_decision_ms():
    prov, runs = _prov()
    recs = hc.execute(runs, prov, warmup=10, window=60, do_run=_fake_do_run, ensure_server=lambda n, p: None, log=lambda m: None, profile_ids=IDS)
    assert not [f for f in guards.REQUIRED_RUN_FIELDS if any(f not in r for r in recs)]
    by = {r["system"]: r for r in recs}
    assert by["swarm"]["t_conv_ms_mean"] == pytest.approx(128.0) and by["decision_table"]["t_conv_ms_mean"] is None                    # T_conv solo donde corresponde
    assert by["decision_table"]["decision_ms_mean"] == pytest.approx(0.015) and by["decision_table"]["decision_ms_median"] == pytest.approx(0.015) and by["decision_table"]["decision_ms_p95"] == pytest.approx(0.015)
    for r in recs:
        assert r["batch_seed"] == r["seed"] and len(r["profile_sequence_hash"]) == 64 and r["p95_latency_ms"] == r["p95_ms"] and r["error_count"] == 0 and r["timeout_count"] == 0
        assert r["metric_validation_status"] == "PENDING_METHODOLOGICAL_VALIDATION" and r["official"] is False and r["oe2_official"] is False and r["comparable"] is True
        assert r["client_timeout_s"] == prov["client_timeout_s"] and r["persist_policy"] == "off"


def test_campaign_artifact_joins_run_level_http_data_with_the_analysis_and_hashes_the_raw_logs(tmp_path):
    prov, runs = _prov()
    recs = hc.execute(runs, prov, warmup=10, window=60, do_run=_fake_do_run, ensure_server=lambda n, p: None, log=lambda m: None, profile_ids=IDS)
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "r1.csv").write_text("a,b\n1,2\n", encoding="utf-8")
    obs = [{"condition": f"{s}|c1", "f_system": s, "f_concurrency": 1, "profile_id": f"p{p}", "replicate": 0, "batch": 0, "status": "completed", "package_valid": True, "decision_ms": (130.0 if s == "swarm" else 0.02) * (1 + p / 10),
            "t_conv_ms": None, "latency_ms": 1.0, "gap_vs_optimum": 0.0} for s in ("swarm", "decision_table") for p in range(6)]
    out = tmp_path / "camp"
    hc.write_campaign(out, prov, runs, recs, [], raw_dir=raw, inprocess_obs=obs)
    manifest = json.loads((out / "manifest.json").read_text())
    assert "runs.csv" in manifest["files"] and manifest["raw_files"] == {"r1.csv": __import__("hashlib").sha256((raw / "r1.csv").read_bytes()).hexdigest()}
    rows = list(csv.DictReader((out / "runs.csv").open(encoding="utf-8")))
    assert len(rows) == len(recs) == 2 and list(rows[0])[: len(guards.REQUIRED_RUN_FIELDS)] == list(guards.REQUIRED_RUN_FIELDS)               # una fila por CORRIDA, no por petición
    assert {r["system"] for r in rows} == {"swarm", "decision_table"} and all(r["profile_sequence_hash"] and r["batch_seed"] for r in rows)
    analysis = json.loads((out / "analysis.json").read_text())
    pend = analysis["families"]["primary:swarm_vs_decision_table"]["pending_metric_validation"]
    assert "decision_ms@c1" in pend["hypotheses"] and pend["excluded_from_holm"] is True and analysis["oe2_official"] is False         # in-process unido, exploratorio
    assert analysis["n_http_runs_used"] == 2 and analysis["generator_limited_levels"] == {}


def test_http_decision_ms_reaches_the_analysis_only_as_exploratory():
    recs = _http_records()
    res = o2.analyze([], recs)
    prim = res["families"]["primary:swarm_vs_decision_table"]
    assert set(prim["pending_metric_validation"]["hypotheses"]) == {"decision_ms_http@u1", "decision_ms_http@u10", "decision_ms_http@u25"}
    assert not any("decision_ms" in h for h in prim["hypotheses"]) and prim["m"] == 6                                            # fuera de Holm: solo L_resp y throughput
    h = prim["pending_metric_validation"]["hypotheses"]["decision_ms_http@u10"]
    assert h["confirmatory"] is False and h["p_holm"] is None and h["result"]["unit"] == "run"


def test_cli_analyze_joins_the_inprocess_run(tmp_path, capsys):
    prov, runs = _prov()
    recs = hc.execute(runs, prov, warmup=10, window=60, do_run=_fake_do_run, ensure_server=lambda n, p: None, log=lambda m: None, profile_ids=IDS)
    out = tmp_path / "camp"
    hc.write_campaign(out, prov, runs, recs, [])
    inproc = tmp_path / "inproc"
    inproc.mkdir()
    obs = [{"condition": f"{s}|c1", "f_system": s, "f_concurrency": 1, "profile_id": f"p{p}", "replicate": 0, "batch": 0, "status": "completed", "package_valid": True, "decision_ms": (130.0 if s == "swarm" else 0.02) * (1 + p / 10)}
           for s in ("swarm", "decision_table") for p in range(6)]
    (inproc / "observations.jsonl").write_text("\n".join(json.dumps(o) for o in obs), encoding="utf-8")
    hc.main(["analyze", "--out-dir", str(out), "--inprocess-run", str(inproc)])
    res = json.loads(capsys.readouterr().out)
    assert res["families"]["primary:swarm_vs_decision_table"]["pending_metric_validation"]["hypotheses"]["decision_ms@c1"]["result"]["n_effective"] == 6


# ═════════════════════════════ B12 — provenance completa ═════════════════════════════
def test_provenance_records_environment_library_dataset_workers_timeout_and_generator_policy():
    prov, _ = _prov()
    assert code_state.provenance_gaps(prov) == []
    sw = prov["software"]
    assert sw["locust"] == metadata.version("locust") and sw["uvicorn"] == metadata.version("uvicorn") and sw["python"] == sys.version.split()[0] and sw["os"] and sw["app_version"] != "unavailable"
    assert sw["postgresql"] == "not_used_persistence_off"                                                      # persistencia off: no interviene
    assert prov["library"]["version"].startswith("lib-v") and prov["dataset"]["n_profiles"] == 100
    assert prov["dataset"]["sha256"] == __import__("hashlib").sha256(bb.DEFAULT_PROFILES.read_bytes()).hexdigest()
    assert prov["server"]["uvicorn_workers"] == hc.SERVER_WORKERS == 1 and prov["generator_policy"]["id"] == "generator-saturation-v1" and prov["client_timeout_s"] == hc.CLIENT_TIMEOUT_S
    assert prov["persistence_status"]["status"] == "INCOMPATIBLE_WITH_APPROVED_L_RESP_DEFINITION" and prov["official"] is False and prov["oe2_official"] is False
    assert prov["code_state"]["dirty"] in (True, False)                                                       # nunca «limpio» supuesto


def test_what_cannot_be_obtained_is_declared_unavailable_and_missing_fields_are_gaps(monkeypatch):
    import redis
    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, *a, **k: (_ for _ in ()).throw(ConnectionError("sin redis"))))
    sw = code_state.software_report("off")
    assert sw["redis_server"] == "unavailable" and sw["locust"] != "unavailable"
    prov, _ = _prov()
    assert code_state.provenance_gaps(prov) == []                                                           # Redis es opcional: su ausencia no es un hueco
    for path, expected in (("library.version", "unavailable"), ("dataset.sha256", None), ("server.uvicorn_workers", None), ("software.locust", "unavailable"), ("code_state.dirty", None)):
        broken = json.loads(json.dumps(prov))
        node = broken
        *head, leaf = path.split(".")
        for k in head:
            node = node[k]
        node[leaf] = expected
        assert code_state.provenance_gaps(broken) == [path]
    assert any(b.id == "B12" for b in guards.evaluate({**prov, "library": {"version": "unavailable"}}))


def test_uvicorn_is_started_with_the_recorded_number_of_workers(monkeypatch):
    cmds = []

    class P:
        def poll(self):
            return None

        def terminate(self):
            pass

        def wait(self, timeout=None):
            pass
    monkeypatch.setattr(hc.subprocess, "Popen", lambda cmd, **k: cmds.append(cmd) or P())
    import urllib.request

    class R:
        def read(self):
            return json.dumps({"persist_policy": "off", "baseline_quality_in_request": False}).encode()
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: R())
    hc.ServerPerN("python", 8999, "k").ensure(20)
    assert cmds[0][cmds[0].index("--workers") + 1] == str(hc.SERVER_WORKERS)
    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: type("R2", (), {"read": lambda self: json.dumps({"persist_policy": "off", "baseline_quality_in_request": True}).encode()})())
    with pytest.raises(RuntimeError, match="evalúa 𝓕 de reporte dentro de la petición"):                     # B3 verificado contra el servidor real, no contra la spec
        hc.ServerPerN("python", 8999, "k", ready_s=5).ensure(30)


# ═════════════════════════════ B14 — guards dinámicos ═════════════════════════════
def _green(monkeypatch):
    """Lleva TODO el estado a «resuelto» SIN tocar ningún mensaje: solo el estado que origina cada bloqueo."""
    monkeypatch.setitem(time_contract.TTFC_CONTRACT, "status", time_contract.APPROVED_STATUS)                  # B1 se resuelve con la aprobación/validación del indicador común (NO con equivalencia con T_conv)
    monkeypatch.setattr(time_contract, "VALIDATION_STATUS", "VALIDATED")
    monkeypatch.setitem(campaign_spec.SPEC["oe2"]["comparator_scope_validation"], "status", "VALIDATED")
    monkeypatch.setitem(campaign_spec.SPEC["oe2"]["persist_policy"], "status", campaign_spec.APPROVED_STATUS)     # B5 se resuelve con la aprobación de B5-C (L_resp intacto, sin persistencia en el baseline)
    for k, d in campaign_spec.SPEC["oe2"]["methodological_decisions"].items():                                   # PEND: cada decisión de D.5 resuelta de forma EXPLÍCITA (solo para probar que el guard sigue al estado)
        monkeypatch.setitem(campaign_spec.SPEC["oe2"]["methodological_decisions"], k, {**d, "status": "DECIDED", "chosen": d["options"][0]})
    for k, v in list(defs.DEFINITIONS.items()):
        if v["status"] == defs.PENDING:
            monkeypatch.setitem(defs.DEFINITIONS, k, {**v, "status": defs.APPROVED})
    monkeypatch.setattr(rubric_v3, "APPROVED_RULE_VERSIONS", frozenset({"x"}))
    monkeypatch.setattr(hc, "CLIENT_TIMEOUT_STATUS", "VALIDATED")
    monkeypatch.setitem(hw.GENERATOR_POLICY, "status", "VALIDATED")


def test_the_default_state_is_fully_blocked_and_every_frozen_decision_is_represented():
    ids = {b.id for b in guards.evaluate(None) if b.critical}
    assert {"B1", "B5", "B13", "DEF"} <= ids and not ids & {"B3", "B6", "B7", "B11", "B12"}                    # técnicos cerrados; metodológicos congelados
    frozen = {b.id for b in guards.evaluate(None) if b.frozen}
    assert frozen == {"B1", "B5", "B13", "PEND"} and all(b.kind == "methodological" for b in guards.evaluate(None) if b.frozen)
    assert {b.id: b.critical for b in guards.evaluate(None) if b.id in ("B6", "B7")} == {"B6": False, "B7": False}     # provisionales: avisos


def test_with_every_state_resolved_nothing_blocks_proving_the_guards_are_state_driven(monkeypatch):
    _green(monkeypatch)
    monkeypatch.setattr(code_state, "git_state", lambda repo=None: {"dirty": False, "method": "git status --porcelain", "modified_paths": []})          # árbol limpio simulado: el test no depende del estado del repositorio
    prov, runs = _prov()
    assert guards.critical_reasons(prov) == [] and guards.warnings(prov) == []
    assert hc.official_refusals({"vcpu": 20, "ram_gib": 31.75}, 10, 10.0, 60.0, prov) == []                  # sin bloqueos reales, no hay rechazo: el guard no es un candado fijo


@pytest.mark.parametrize("breaker, expected", [
    (lambda m: m.setattr(time_contract, "T_CONV_EQUIVALENCE", "ESTABLISHED"), "B1"),                          # declarar equivalencia de T_conv CONTRADICE B1: bloquea, no desbloquea
    (lambda m: m.setattr(time_contract, "VALIDATION_STATUS", "PENDING_METHODOLOGICAL_VALIDATION"), "B1"),
    (lambda m: m.setitem(time_contract.TTFC_CONTRACT, "status", "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"), "B1"),
    (lambda m: m.setitem(campaign_spec.SPEC["oe2"]["comparator_scope_validation"], "status", "PENDING_METHODOLOGICAL_VALIDATION"), "B13"),
    (lambda m: m.setitem(campaign_spec.SPEC["oe2"]["persist_policy"], "status", "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED"), "B5"),
    (lambda m: m.setitem(defs.DEFINITIONS, "latency_l_resp", {**defs.DEFINITIONS["latency_l_resp"], "definition": "L_resp = petición HTTP → último byte, sin persistencia síncrona"}), "B5"),      # L_resp reformulada para que OFF parezca literal
    (lambda m: m.setitem(campaign_spec.SPEC["oe2"]["persist_policy"], "artificial_persistence_in_baseline", True), "B5"),
    (lambda m: m.setattr(conv, "BASELINE_REPORTS_QUALITY_IN_REQUEST", True), "B3"),
    (lambda m: m.setattr(guards, "REQUIRED_RUN_FIELDS", guards.REQUIRED_RUN_FIELDS + ("campo_inexistente",)), "B11"),
    (lambda m: m.delitem(hw.GENERATOR_POLICY, "on_saturation"), "B7"),
    (lambda m: m.setitem(defs.DEFINITIONS, "statistical_unit_performance", {**defs.DEFINITIONS["statistical_unit_performance"], "status": defs.PENDING}), "DEF"),
])
def test_each_single_state_change_produces_exactly_its_own_blocker_and_the_official_flag_is_refused(monkeypatch, breaker, expected):
    _green(monkeypatch)
    breaker(monkeypatch)
    prov, _ = _prov()
    critical = {b.id for b in guards.evaluate(prov) if b.critical}
    assert critical == {expected}
    assert any(f"[{expected}]" in r for r in hc.official_refusals({"vcpu": 20, "ram_gib": 31.75}, 10, 10.0, 60.0, prov))


def test_an_official_run_is_refused_when_the_git_tree_is_dirty_or_unknown(monkeypatch):
    _green(monkeypatch)
    ok = {"vcpu": 20, "ram_gib": 31.75}
    for dirty, word in ((False, None), (True, "con cambios sin commit"), (None, "de estado desconocido")):
        monkeypatch.setattr(code_state, "git_state", lambda repo=None, d=dirty: {"dirty": d, "method": "git status --porcelain", "modified_paths": []})
        prov, _ = _prov()
        refusals = hc.official_refusals(ok, 10, 10.0, 60.0, prov)
        assert (refusals == []) if word is None else (len(refusals) >= 1 and any(word in r for r in refusals))


def test_combined_blockers_are_all_reported_and_official_main_refuses_without_writing(monkeypatch, tmp_path):
    _green(monkeypatch)
    monkeypatch.setattr(conv, "BASELINE_REPORTS_QUALITY_IN_REQUEST", True)
    monkeypatch.setitem(time_contract.TTFC_CONTRACT, "status", "FROZEN_PROVISIONAL_NOT_ADVISOR_APPROVED")
    prov, _ = _prov(client_timeout=0)
    assert {b.id for b in guards.evaluate(prov) if b.critical} == {"B1", "B3", "B6"}
    out = tmp_path / "never"
    with pytest.raises(SystemExit) as exc:
        hc.main(["oe2", "--campaign-id", "x", "--out-dir", str(out), "--official", "--client-timeout", "0"])
    assert "[B1]" in str(exc.value) and "[B3]" in str(exc.value) and "[B6]" in str(exc.value) and not out.exists()


def test_persistence_status_represents_both_policies_without_deciding_between_them(monkeypatch):
    assert guards.persistence_status("off")["status"] == "INCOMPATIBLE_WITH_APPROVED_L_RESP_DEFINITION"
    assert guards.persistence_status("on")["status"] == "UNSUPPORTED_BY_BASELINE"                      # el baseline hoy no persiste
    assert guards.persistence_status("on", baseline_supports_persistence=True)["status"] == "COMPATIBLE"
    assert guards.persistence_status("maybe")["status"] == "UNDECIDED"
    monkeypatch.setitem(defs.DEFINITIONS, "latency_l_resp", {**defs.DEFINITIONS["latency_l_resp"], "definition": "L_resp sin persistencia síncrona"})
    assert guards.persistence_status("off")["status"] == "COMPATIBLE"                                  # si la definición vigente cambia, el estado cambia solo


def test_the_dry_run_shows_the_dynamic_state_and_still_refuses_official(capsys, tmp_path):
    out = tmp_path / "x"
    hc.main(["oe2", "--campaign-id", "dry", "--out-dir", str(out), "--runs", "3", "--users", "1,10,25,50", "--dry-run"])
    text = capsys.readouterr().out
    d = json.loads(text[text.index("{"):])
    assert not out.exists() and d["official"] is False and d["oe2_official"] is False
    assert d["frozen_methodological_decisions_pending"] == ["B1", "B13", "B5", "PEND"] and d["provenance_gaps"] == []
    assert d["client_timeout"] == {"seconds": 30.0, "status": "PROVISIONAL_TECHNICAL"} and d["generator_policy"]["id"] == "generator-saturation-v1"
    assert d["persistence_status"]["status"] == "INCOMPATIBLE_WITH_APPROVED_L_RESP_DEFINITION" and d["server"]["uvicorn_workers"] == 1 and d["server"]["baseline_quality_in_request"] is False
    assert d["library"]["version"].startswith("lib-v") and d["dataset"]["n_profiles"] == 100 and d["software"]["locust"] != "unavailable"
    with pytest.raises(SystemExit, match="CAMPAÑA OFICIAL RECHAZADA"):
        hc.main(["oe2", "--campaign-id", "dry2", "--out-dir", str(tmp_path / "y"), "--official"])


# ═════════════════════════════ Revisión pre-commit de la Fase C ═════════════════════════════
@pytest.mark.parametrize("text, required", [
    (defs.DEFINITIONS["latency_l_resp"]["definition"], True),                                           # la definición APROBADA vigente (incluye persistencia síncrona; excluye la ASÍNCRONA)
    ("L_resp incorpora persistencia síncrona mínima", True),                                            # reformulada: sigue exigida (falla cerrado)
    ("L_resp requiere persistencia", True),
    ("L_resp = petición HTTP → último byte, sin persistencia síncrona", False),                         # exclusión EXPLÍCITA de la síncrona
    ("L_resp: no incluye persistencia síncrona", False),
    ("L_resp = petición HTTP → último byte del JSON", False),                                           # no menciona persistencia
    ("L_resp excluye persistencia asíncrona", True),                                                    # excluir la ASÍNCRONA no libera la síncrona
])
def test_b5_guard_fails_closed_when_the_definition_is_reworded(monkeypatch, text, required):
    _green(monkeypatch)                                                                                 # B5-C aprobada: lo único que puede volver a bloquear es que L_resp ya no exija la persistencia síncrona
    monkeypatch.setitem(defs.DEFINITIONS, "latency_l_resp", {**defs.DEFINITIONS["latency_l_resp"], "definition": text})
    assert guards.l_resp_requires_sync_persistence() is required
    assert ("B5" in {b.id for b in guards.evaluate(None)}) is (not required)                            # reformular L_resp para que OFF parezca literal NO desbloquea: bloquea


def test_campaign_sources_have_no_duplicates_exist_and_cover_what_determines_the_campaign():
    srcs = code_state.CAMPAIGN_SOURCES
    assert len(srcs) == len(set(srcs)) and all((BACK / s).is_file() for s in srcs)
    assert {"adaptation_swarm/oe/code_state.py", "adaptation_swarm/metrics/performance.py", "adaptation_swarm/oe/campaign_guards.py", "adaptation_swarm/oe/http_window.py"} <= set(srcs)
    assert len(code_state.PROVENANCE_REQUIRED) == len(set(code_state.PROVENANCE_REQUIRED))


def test_effective_server_library_is_recorded_and_a_mismatch_blocks_b12():
    prov, _ = _prov()
    hc.record_effective_server(prov, {"library_version": prov["library"]["version"], "persist_policy": "off", "baseline_quality_in_request": False})
    assert prov["server"]["library_version_matches"] is True and "B12" not in {b.id for b in guards.evaluate(prov)}
    hc.record_effective_server(prov, {"library_version": "lib-v0-otra", "persist_policy": "off", "baseline_quality_in_request": False})
    assert prov["server"]["library_version_matches"] is False and prov["server"]["effective"]["library_version"] == "lib-v0-otra"
    assert [b.reason for b in guards.evaluate(prov) if b.id == "B12"] == ["la biblioteca efectiva del servidor (/health) no coincide con la registrada en la provenance"]


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_the_endpoint_really_follows_the_quality_policy_so_the_b3_test_would_catch_a_regression(client, slice_profile, monkeypatch):
    monkeypatch.setattr(router_mod, "BASELINE_REPORTS_QUALITY_IN_REQUEST", True)                      # regresión simulada: 𝓕 vuelve a la petición
    out = (await client.post("/api/adaptation/baseline/decision_table", json=slice_profile.model_dump(mode="json"), headers={"X-Swarm-Key": KEY})).json()
    assert out["g_best"]["F"] is not None and out["quality_in_request"] is True                      # el endpoint sí cambia ⇒ el test de «F fuera de la petición» (con `boom`) fallaría
    health = (await client.get("/api/adaptation/health", headers={"X-Swarm-Key": KEY})).json()
    assert health["baseline_quality_in_request"] is True                                              # y /health lo delata: ServerPerN/guards lo bloquearían
