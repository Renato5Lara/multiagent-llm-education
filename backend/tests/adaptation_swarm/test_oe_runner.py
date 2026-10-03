"""Ejecutor y análisis de OE2/OE3/OE4 (`oe/`). Parte pura (diseños, bucle cerrado, análisis sobre observaciones sintéticas de forma conocida: solo prueban el CÓDIGO, no son resultados del estudio) y
parte de integración (Redis real + biblioteca real: una corrida pequeña de extremo a extremo con sus archivos de salida)."""

import asyncio
import json
import uuid

import numpy as np
import pytest

from adaptation_swarm.fitness.fitness import FitnessWeights
from adaptation_swarm.oe import analysis as oea
from adaptation_swarm.oe import runner
from adaptation_swarm.oe.conditions import Condition, oe2_systems, oe3_full_factorial, oe3_one_factor_at_a_time, oe4_grid


# ── diseños ────────────────────────────────────────────────────────────────────────────────────────────
def test_designs_have_unique_named_conditions():
    full, ofat, grid = oe3_full_factorial(), oe3_one_factor_at_a_time(), oe4_grid()
    assert len(full) == 48 and len({c.name for c in full}) == 48 and len(ofat) == 7 and len(grid) == 18
    assert [c.system for c in oe2_systems(4)] == ["swarm", "rules", "bruteforce"] and all(c.concurrency == 4 for c in oe2_systems(4))
    assert Condition() in full and Condition() in ofat                                    # la referencia histórica forma parte de ambos diseños


def test_mechanism_maps_to_pso_coefficients_and_validation():
    ref = Condition().pso_params()
    assert (ref.c1, ref.c2) == (1.494, 1.494)
    assert (Condition(mechanism="cognitive").pso_params().c1, Condition(mechanism="cognitive").pso_params().c2) == (1.494, 0.0)
    assert (Condition(mechanism="social").pso_params().c1, Condition(mechanism="social").pso_params().c2) == (0.0, 1.494)
    assert Condition(n_particles=30).pso_params().n_particles == 30
    for bad in ({"system": "x"}, {"dispatch": "x"}, {"mechanism": "x"}, {"concurrency": 0}, {"replicas": 0}):
        with pytest.raises(ValueError):
            Condition(**bad)


# ── bucle cerrado ───────────────────────────────────────────────────────────────────────────────────────
async def test_closed_loop_respects_concurrency_and_runs_every_task():
    state = {"now": 0, "peak": 0}

    class P:                                              # solo necesita lo que lee el bucle
        def __init__(self, i):
            self.profile_id, self.archetype, self.difficulty = f"p{i}", None, None

    async def call(p, rep):
        state["now"] += 1
        state["peak"] = max(state["peak"], state["now"])
        await asyncio.sleep(0.01)
        state["now"] -= 1
        return {"status": "completed"}

    rows, elapsed = await runner._closed_loop(call, [(P(i), 0) for i in range(12)], concurrency=3)
    assert len(rows) == 12 and state["peak"] == 3 and all(r["latency_ms"] >= 10 for r in rows)
    assert 0.03 <= elapsed < 0.2                          # 12 tareas de 10 ms con 3 usuarios ≈ 40 ms


def test_validity_requires_all_conditions_and_lists_reasons():
    hw_ok = {"vcpu": 8, "ram_gib": 32.0}
    hw_bad = {"vcpu": 8, "ram_gib": 7.5}
    full = oe2_systems(1)
    ok = runner.validity("oe2", hw=hw_ok, n_profiles=100, k=10, batches=5, warmup=10, conditions=full)
    assert not ok["reasons"] and ok["blocked_definitions"] == ["t_conv_baselines", "statistical_unit_performance"]          # todo medido, pero hay definiciones PENDING
    assert ok["status"] == "EXPLORATORY" and ok["official_execution"] == "BLOCKED_DEFINITION" and ok["environment_class"] == "OFFICIAL_TARGET"
    assert runner.validity("oe3", hw=hw_ok, n_profiles=100, k=10, batches=1, warmup=10, conditions=[])["blocked_definitions"] == ["statistical_unit_performance"]
    bad = runner.validity("oe2", hw=hw_bad, n_profiles=100, k=10, batches=5, warmup=10, conditions=full)
    assert bad["status"] == "EXPLORATORY" and bad["reasons"] == ["no se cumple: hardware_cercano_al_objetivo"]
    assert bad["official_execution"] == "PENDING_HARDWARE" and bad["environment_class"] == "PILOT"
    assert runner.validity("oe2", hw=hw_ok, n_profiles=100, k=10, batches=5, warmup=10, conditions=full[:2])["status"] == "EXPLORATORY"
    assert runner.validity("oe3", hw=hw_ok, n_profiles=100, k=3, batches=1, warmup=10, conditions=[])["status"] == "EXPLORATORY"
    assert runner.PENDING_DECISIONS and "convencional" in runner.PENDING_DECISIONS[0]


# ── análisis sobre observaciones sintéticas de forma conocida ───────────────────────────────────────────
def _row(cond, factors, pid, **v):
    base = {"condition": cond, "status": "completed", "package_valid": True, "profile_id": pid, "replicate": 0, "batch": 0,
            "t_conv_ms": 10.0, "latency_ms": 12.0, "k_stop": 2, "n_messages": 50, "F": 0.5, "gap_vs_optimum": 0.01}
    base.update({f"f_{k}": x for k, x in factors.items()}, **v)
    return base


def _factors(**kw):
    f = {"system": "swarm", "dispatch": "batch", "broadcast_gbest": True, "heuristic_seed": True, "mechanism": "pso", "replicas": 1, "n_particles": 20, "concurrency": 1}
    f.update(kw)
    return f


def test_analyze_oe2_detects_a_known_difference_and_reports_throughput():
    rng = np.random.default_rng(0)
    obs, bat = [], []
    for system, mu, thr in (("swarm", 40.0, 20.0), ("rules", 1.0, 900.0)):
        name = f"{system}|c1"
        for i in range(30):
            obs.append(_row(name, _factors(system=system), f"p{i}", t_conv_ms=mu + rng.normal(0, 2), latency_ms=mu + 5 + rng.normal(0, 2)))
        bat += [{"condition": name, "batch": b, "concurrency": 1, "n_requests": 30, "n_ok": 30, "n_failed": 0, "elapsed_s": 1.0, "throughput_rps": thr + rng.normal(0, 1)} for b in range(5)]
    a = oea.analyze("oe2", obs, bat)
    c = a["comparisons"]["c1|swarm_vs_rules"]
    assert c["t_conv_ms"]["significant"] and c["t_conv_ms"]["mean_diff"] > 30 and c["latency_ms"]["significant"] and c["throughput_rps"]["significant"]
    assert a["conditions"]["swarm|c1"]["error_rate"] == 0 and len(a["conditions"]["swarm|c1"]["throughput_by_batch"]) == 5


def test_analysis_ignores_failed_requests_but_reports_error_rate():
    obs = [_row("swarm|c1", _factors(), f"p{i}") for i in range(10)] + [_row("swarm|c1", _factors(), "pX", status="failed", t_conv_ms=None)]
    s = oea.summarize_conditions(obs, [])["swarm|c1"]
    assert s["n_ok"] == 10 and s["error_rate"] == pytest.approx(1 / 11) and s["t_conv_ms"]["n"] == 10


def test_analyze_oe3_ofat_compares_each_level_with_the_reference_with_holm():
    rng = np.random.default_rng(1)
    obs = []
    for cond in oe3_one_factor_at_a_time():
        shift = 30.0 if cond.dispatch == "sequential" else 0.0
        for i in range(30):
            obs.append(_row(cond.name, cond.factors(), f"p{i:02d}", t_conv_ms=40 + shift + rng.normal(0, 2) + i * 0.1))
    a = oea.analyze("oe3", obs, [])
    assert a["design"] == "one_factor_at_a_time" and a["reference"] == Condition().name and len(a["vs_reference"]) == 6
    seq = a["vs_reference"][Condition(dispatch="sequential").name]["t_conv_ms"]
    other = a["vs_reference"][Condition(broadcast_gbest=False).name]["t_conv_ms"]
    assert seq["significant_holm"] is True and other["significant_holm"] is False and a["interactions"] == "not_estimated"


def test_analyze_oe3_full_factorial_main_effects():
    rng = np.random.default_rng(2)
    obs = []
    for cond in oe3_full_factorial():
        shift = 25.0 if cond.mechanism == "cognitive" else 0.0
        for i in range(12):
            obs.append(_row(cond.name, cond.factors(), f"p{i:02d}", t_conv_ms=40 + shift + rng.normal(0, 1), k_stop=2))
    a = oea.analyze("oe3", obs, [])
    me = a["main_effects"]["t_conv_ms"]
    assert a["design"] == "full_factorial_2x2x2x2x3" and set(me) == set(oea.OE3_FACTORS)
    assert me["mechanism"]["pairwise"]["cognitive__vs__pso"]["significant_holm"] is True
    assert me["dispatch"]["pairwise"]["batch__vs__sequential"]["significant"] is False
    assert a["main_effects"]["k_stop"]["mechanism"]["friedman"]["status"] == "undefined_identical_conditions"


def test_analyze_oe4_load_trend_and_particles_effect():
    rng = np.random.default_rng(3)
    obs, bat = [], []
    for cond in oe4_grid(concurrency=(1, 5, 10), n_particles=(10, 20)):
        for i in range(12):
            obs.append(_row(cond.name, cond.factors(), f"p{i:02d}", latency_ms=20.0 * cond.concurrency + rng.normal(0, 1), t_conv_ms=10.0 + cond.n_particles + rng.normal(0, .5)))
        bat += [{"condition": cond.name, "batch": b, "concurrency": cond.concurrency, "n_requests": 12, "n_ok": 12, "n_failed": 0, "elapsed_s": 1.0,
                 "throughput_rps": 20.0 + 2 * cond.concurrency + rng.normal(0, .1)} for b in range(4)]
    a = oea.analyze("oe4", obs, bat)
    e = a["by_particles"]["20"]
    assert e["throughput_across_load"]["kruskal"]["significant"] and e["spearman_load_vs_p50_latency"]["rho"] == pytest.approx(1.0)
    assert a["particles_effect_at_c1"]["t_conv_ms"]["pairwise"]["N10__vs__N20"]["significant"] is True
    with pytest.raises(ValueError):
        oea.analyze("oe9", [], [])


# ── integración: corrida pequeña de extremo a extremo ──────────────────────────────────────────────────
@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_end_to_end_small_run_writes_reproducible_results(store, profiles, tmp_path, monkeypatch):
    profs = list(profiles.values())[:5]
    fw = FitnessWeights()
    obs, bat = [], []
    for cond in oe2_systems(2):
        o, b = await runner.run_condition(store, cond, profs, k=1, batches=3, warmup=2, batch_seed=runner.DEFAULT_BATCH_SEED, fw=fw, log=lambda *_: None)
        obs += o
        bat += b
    runner.add_optimum_gap(store, profs, obs, fw)
    assert len(obs) == 3 * 5 * 3 and all(r["status"] == "completed" and r["package_valid"] for r in obs)
    assert all(r["gap_vs_optimum"] >= -1e-9 for r in obs) and {r["f_system"] for r in obs} == {"swarm", "rules", "bruteforce"}
    swarm = [r for r in obs if r["f_system"] == "swarm"]
    assert all(r["k_stop"] is not None and r["n_messages"] > 20 for r in swarm)
    assert all(b["throughput_rps"] > 0 and b["n_ok"] == 5 for b in bat) and len(bat) == 9

    class Args:
        experiment, label, k, batches, warmup, batch_seed, concurrency, design, particles = "oe2", "t", 1, 3, 2, runner.DEFAULT_BATCH_SEED, [2], None, None

    monkeypatch.setattr(runner, "hardware_profile", lambda: {"vcpu": 8, "cpu_model": None, "ram_gib": 7.53, "python": "fijo", "numpy": "fijo", "platform": "fijo"})   # la clase de entorno depende del hardware medido: se fija uno que NO cumple para que el test sea determinista
    prov = runner.provenance(store, runner.DEFAULT_PROFILES, Args, oe2_systems(2), len(profs))
    assert prov["definitions"]["registry"]["compliance_score_oe1"]["status"] == "PENDING" and prov["validity"]["blocked_definitions"]
    assert prov["validity"]["status"] == "EXPLORATORY" and prov["library_version"] == store.version and prov["code"]["commit"]
    out = tmp_path / "run"
    analysis = runner.write_results(out, prov, obs, bat)
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["validity"] == "EXPLORATORY" and manifest["environment_class"] == "PILOT" and manifest["official_execution"] == "PENDING_HARDWARE"
    assert set(manifest["files"]) == {"observations.jsonl", "batches.json", "provenance.json", "analysis.json", "raw_observations.csv", "statistical_input.csv", "environment.json", "summary.json", "logs/run.log"}
    sums = dict(reversed(l.split("  ")) for l in (out / "checksums.txt").read_text().splitlines())
    assert sums == manifest["files"]                                                                      # checksums.txt = hashes del manifiesto
    # datos crudos para la fase estadística: una fila por observación (con semilla y marca de tiempo) y formato largo por métrica
    import csv
    raw = list(csv.DictReader((out / "raw_observations.csv").open(encoding="utf-8")))
    assert len(raw) == len(obs) and all(r["t_start_utc"] and r["run_label"] == "t" for r in raw)
    assert all(r["seed"] for r in raw if r["f_system"] == "swarm") and all(r["seed"] == "" for r in raw if r["f_system"] != "swarm")
    long = list(csv.DictReader((out / "statistical_input.csv").open(encoding="utf-8")))
    assert {r["metric"] for r in long} >= {"t_conv_ms", "latency_ms", "throughput_rps", "gap_vs_optimum"}
    assert sum(1 for r in long if r["metric"] == "latency_ms") == len(obs) and sum(1 for r in long if r["metric"] == "throughput_rps") == len(bat)
    assert all(r["unit_type"] == "batch" for r in long if r["metric"] == "throughput_rps") and all(r["unit_id"].startswith("batch:") for r in long if r["unit_type"] == "batch")
    eq = json.loads((out / "provenance.json").read_text())["equivalence"]
    assert eq["all_equivalent"] and set(eq["per_load_level"]["c2"]["conditions"]) == {c.name for c in oe2_systems(2)}
    for name, sha in manifest["files"].items():
        assert runner._sha_bytes((out / name).read_bytes()) == sha
    assert json.loads(json.dumps(runner.analyze_dir(out), sort_keys=True, default=str)) == json.loads(json.dumps(analysis, sort_keys=True, default=str))   # análisis reproducible
    with pytest.raises(FileExistsError):
        runner.write_results(out, prov, obs, bat)                                     # nunca sobrescribe


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_swarm_condition_variants_all_complete(store, profiles):
    profs = list(profiles.values())[:3]
    for cond in (Condition(dispatch="sequential"), Condition(broadcast_gbest=False), Condition(heuristic_seed=False), Condition(mechanism="cognitive"), Condition(replicas=2)):
        o, _ = await runner.run_condition(store, cond, profs, k=1, batches=1, warmup=0, batch_seed=runner.DEFAULT_BATCH_SEED, fw=FitnessWeights(), log=lambda *_: None)
        assert len(o) == 3 and all(r["status"] == "completed" and r["package_valid"] for r in o), cond.name


def test_equivalence_detects_unequal_workloads():
    def row(cond, pid, rep=0, batch=0, level=1):
        return {"condition": cond, "profile_id": pid, "replicate": rep, "batch": batch, "f_concurrency": level}
    same = [row(c, p) for c in ("a", "b") for p in ("p1", "p2")]
    assert runner.equivalence(same)["all_equivalent"] is True
    unequal = same + [row("a", "p3")]
    eq = runner.equivalence(unequal)
    assert eq["all_equivalent"] is False and eq["per_load_level"]["c1"]["n_requests_each"] == {"a": 3, "b": 2}


def test_official_gate_refuses_non_target_hardware_without_relaxing_the_requirement():
    full = oe2_systems(1)
    bad = runner.validity("oe2", hw={"vcpu": 8, "ram_gib": 7.5}, n_profiles=100, k=10, batches=5, warmup=10, conditions=full)
    reasons = runner.official_gate(bad)
    assert reasons and reasons[0].startswith("hardware:")                                       # 7.5 GiB nunca habilita una ejecución oficial
    ok_hw = runner.validity("oe2", hw={"vcpu": 8, "ram_gib": 32.0}, n_profiles=100, k=10, batches=5, warmup=10, conditions=full)
    assert not any(r.startswith("hardware:") for r in runner.official_gate(ok_hw))               # con el hardware objetivo, el hardware deja de ser la razón
    assert runner.TARGET_HARDWARE == {"vcpu": 8, "ram_gib": 32.0}                                # el requisito no se relajó


def test_official_flag_aborts_before_writing_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "meets_target", lambda hw: False)
    out = tmp_path / "nuevo"
    monkeypatch.setattr(runner.iso, "require_isolated_redis", lambda: None)
    with pytest.raises(SystemExit, match="OFICIAL RECHAZADA"):
        runner.main(["oe4", "--label", "gate-test", "--out-dir", str(out), "--official", "--limit", "2"])
    assert not out.exists()
