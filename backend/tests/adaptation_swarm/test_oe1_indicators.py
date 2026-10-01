"""OE1 (`oe/oe1.py`): la tabla de requisitos solo marca MET/NOT_MET con datos MEDIDOS (nunca infiere), el puntaje de cumplimiento y su relación con el desempeño se calculan sin fabricar
correlaciones, y las sondas de determinismo y persistencia (RF06) corren contra la pila real. Las observaciones sintéticas de la parte pura solo prueban el código."""

import numpy as np
import pytest

from adaptation_swarm.oe import oe1
from adaptation_swarm.oe.conditions import Condition


def _obs(cond="swarm|a", n=20, **over):
    base = {"condition": cond, "status": "completed", "package_valid": True, "w_valid": True, "iterations_logged": True, "inflight_overlap": True, "error_code": None, "k_stop": 2,
            "stop_reason": "epsilon", "latency_ms": 50.0, "t_conv_ms": 40.0, "gap_vs_optimum": 0.01, "f_system": "swarm", "f_concurrency": 1}
    return [{**base, "profile_id": f"p{i}", **over} for i in range(n)]


def _bat(cond="swarm|a", thr=25.0, n=5):
    return [{"condition": cond, "batch": b, "throughput_rps": thr} for b in range(n)]


def _by_id(table):
    return {r["id"]: r for r in table}


def test_registry_covers_all_requirements_and_dimensions():
    ids = [r.id for r in oe1.REQUIREMENTS]
    assert ids[:6] == [f"RF0{i}" for i in range(1, 7)] and {"RNF01", "RNF02", "RNF03", "RNF04", "RNF05"} <= set(ids)
    assert {r.dimension for r in oe1.REQUIREMENTS} == set(oe1.DIMENSIONS) and len(set(ids)) == len(ids)
    assert all(r.indicator and r.threshold and r.source for r in oe1.REQUIREMENTS)


def test_table_marks_measured_requirements_and_leaves_unmeasured_not_measured():
    t = _by_id(oe1.requirement_table(_obs(), _bat()))
    for rid in ("RF01", "RF02", "RF03", "RF04", "RF05", "REL-C", "RNF01", "RNF02", "RNF04"):
        assert t[rid]["status"] == oe1.MET, rid
    for rid in ("RF06", "REL-D", "RNF03", "RNF05"):
        assert t[rid]["status"] == oe1.NOT_MEASURED and t[rid]["reason"], rid          # nada se infiere sin medición


def test_failures_and_threshold_violations_are_not_met():
    obs = _obs(n=18) + _obs(n=2, status="failed", package_valid=False, w_valid=None, inflight_overlap=None, k_stop=None, stop_reason="error", error_code="CycleFailedError")
    t = _by_id(oe1.requirement_table(obs, _bat(thr=10.0)))
    assert t["RF05"]["status"] == oe1.NOT_MET and t["REL-C"]["status"] == oe1.NOT_MET and t["REL-C"]["value"] == pytest.approx(0.9)
    assert t["RNF04"]["status"] == oe1.NOT_MET and t["RF01"]["status"] == oe1.MET
    slow = _by_id(oe1.requirement_table(_obs(latency_ms=2500.0), _bat()))
    assert slow["RNF01"]["status"] == oe1.NOT_MET
    seq = _by_id(oe1.requirement_table(_obs(inflight_overlap=False), _bat()))
    assert seq["RF03"]["status"] == oe1.NOT_MET
    nonconv = _by_id(oe1.requirement_table(_obs(stop_reason="k_max", k_stop=15), _bat()))
    assert nonconv["RNF02"]["status"] == oe1.NOT_MET


def test_external_evidence_is_evaluated_only_when_provided():
    ext = _by_id(oe1.requirement_table(_obs(), _bat(), persistence={"rate": 1.0, "n": 5}, determinism={"rate": 1.0, "n": 5}, f1={"f1_adapt": 0.9},
                                       sus={"mean": 80.0, "test_p": 0.01, "n": 12}))
    assert all(ext[r]["status"] == oe1.MET for r in ("RF06", "REL-D", "RNF03", "RNF05"))
    low = _by_id(oe1.requirement_table(_obs(), _bat(), f1={"f1_adapt": 0.80}, sus={"mean": 80.0, "test_p": 0.2, "n": 12}, persistence={"rate": 0.9, "n": 10}))
    assert low["RNF03"]["status"] == oe1.NOT_MET and low["RNF05"]["status"] == oe1.NOT_MET and low["RF06"]["status"] == oe1.NOT_MET
    assert _by_id(oe1.requirement_table(_obs(), _bat(), sus={"mean": None}))["RNF05"]["status"] == oe1.NOT_MEASURED
    pend = oe1.requirement_table(_obs(), _bat())
    d = oe1.dimension_summary(pend)
    assert set(d) == set(oe1.DIMENSIONS) and d["calidad"]["not_measured"] == 2 and d["funcionalidad"]["not_measured"] == 1


def test_conventional_systems_are_excluded_from_rf_evaluation():
    conv = _obs("rules|c1", w_valid=None, iterations_logged=None, inflight_overlap=None, f_system="rules")
    t = _by_id(oe1.requirement_table(conv, []))
    assert t["RF01"]["status"] == oe1.NOT_MEASURED and t["RF05"]["status"] == oe1.NOT_MEASURED


def test_relationship_is_undefined_when_compliance_does_not_vary():
    obs, bat = [], []
    for i in range(5):
        obs += _obs(f"swarm|c{i}", gap_vs_optimum=0.01 * i)
        bat += _bat(f"swarm|c{i}")
    rel = oe1.relationship(obs, bat)
    assert rel["n_conditions"] == 5 and all(v["compliance_score"] == 1.0 for v in rel["per_condition"].values())
    g = rel["spearman_compliance_vs_performance"]["gap_vs_optimum"]
    assert g["status"] == "undefined_constant_variable" and "no hay variación" in g["note"]


def test_relationship_detects_a_known_association():
    rng = np.random.default_rng(0)
    obs, bat = [], []
    for i in range(10):
        broken = i % 2 == 1                                          # condiciones que incumplen RF03 y RF04 son las de peor calidad
        obs += _obs(f"swarm|c{i}", inflight_overlap=not broken, iterations_logged=not broken, gap_vs_optimum=(0.05 if broken else 0.01) + float(rng.normal(0, 1e-4)))
        bat += _bat(f"swarm|c{i}")
    rel = oe1.relationship(obs, bat)
    s = rel["spearman_compliance_vs_performance"]["gap_vs_optimum"]
    assert s["status"] == "ok" and s["rho"] < -0.8 and s["p_value"] < 0.01
    assert rel["per_condition"]["swarm|c1"]["not_met"] == ["RF03", "RF04"]
    req = rel["request_level_functional_compliance_vs_gap"]
    assert req["n_compliant"] == 100 and req["n_non_compliant"] == 100 and req["significant"] is True and req["mean_a"] < req["mean_b"]


def test_markdown_renders_every_requirement():
    t = oe1.requirement_table(_obs(), _bat())
    md = oe1.render_markdown(t, oe1.dimension_summary(t), oe1.relationship(_obs(), _bat()))
    assert all(r.id in md for r in oe1.REQUIREMENTS) and "NOT_MEASURED" in md


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_determinism_probe_on_real_stack(store, profiles):
    r = await oe1.determinism_probe(store, list(profiles.values()), 4, 20260930)
    assert r["n"] == 4 and r["identical"] == 4 and r["rate"] == 1.0 and r["mismatches"] == []


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_persistence_probe_on_real_postgres(store, profiles):
    r = await oe1.persistence_probe(store, list(profiles.values()), 3, 20260930)
    assert r["n"] == 3 and r["complete"] == 3 and r["rate"] == 1.0 and r["failures"] == []


@pytest.mark.integration
@pytest.mark.requires_library_audio
async def test_protocol_violations_show_up_as_unmet_requirements(store, profiles):
    from adaptation_swarm.fitness.fitness import FitnessWeights
    from adaptation_swarm.oe import runner
    profs = list(profiles.values())[:6]
    obs, bat = [], []
    for cond in (Condition(), Condition(dispatch="sequential")):
        o, b = await runner.run_condition(store, cond, profs, k=1, batches=2, warmup=0, batch_seed=runner.DEFAULT_BATCH_SEED, fw=FitnessWeights(), log=lambda *_: None)
        obs += o
        bat += b
    runner.add_optimum_gap(store, profs, obs, FitnessWeights())
    per = oe1.condition_compliance(obs, bat)
    assert per[Condition().name]["not_met"] == [] or per[Condition().name]["not_met"] == ["RNF04"]
    assert "RF03" in per[Condition(dispatch="sequential").name]["not_met"]          # sin despacho concurrente no se cumple RF03
