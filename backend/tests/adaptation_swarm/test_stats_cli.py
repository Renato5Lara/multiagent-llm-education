"""`oe/stats_cli.py`: la fase estadística se alimenta SOLO de `statistical_input.csv` (+ manifiesto), elige el diseño por experimento, hereda la etiqueta de validez y no formula hipótesis académicas.
Observaciones SINTÉTICAS de forma conocida (solo prueban el código)."""

import json

import numpy as np
import pytest

from adaptation_swarm.oe import export, stats_cli
from adaptation_swarm.oe.conditions import Condition, oe2_systems, oe3_one_factor_at_a_time, oe4_grid


def _write_run(tmp_path, exp, obs, bat, validity="EXPLORATORY"):
    d = tmp_path / exp
    d.mkdir()
    (d / "statistical_input.csv").write_text(export.statistical_input_csv("syn", exp, obs, bat), encoding="utf-8")
    (d / "manifest.json").write_text(json.dumps({"experiment": exp, "validity": validity, "environment_class": "PILOT", "official_execution": "PENDING_HARDWARE",
                                                 "files": {"statistical_input.csv": "abc"}}))
    return d


def _row(cond, pid, **v):
    return {"condition": cond.name, "status": "completed", "profile_id": pid, "replicate": 0, "batch": 0, "seed": 1, "t_start_utc": "t", "t_conv_ms": 10.0, "latency_ms": 12.0, "k_stop": 2, **v}


def test_oe2_plan_pairs_by_profile_and_tests_throughput_by_batch(tmp_path):
    rng = np.random.default_rng(0)
    obs, bat = [], []
    for c, mu, thr in zip(oe2_systems(1), (40.0, 1.0, 80.0), (20.0, 900.0, 11.0)):
        obs += [_row(c, f"p{i:02d}", t_conv_ms=mu + rng.normal(0, 1), latency_ms=mu + 5 + rng.normal(0, 1)) for i in range(25)]
        bat += [{"condition": c.name, "batch": b, "throughput_rps": thr + rng.normal(0, .5)} for b in range(5)]
    res = stats_cli.analyze_run(_write_run(tmp_path, "oe2", obs, bat))
    r = res["contrasts"]["c1|swarm_vs_rules"]
    assert r["t_conv_ms"]["design"] == "paired" and r["t_conv_ms"]["unit"].startswith("profile_mean") and r["t_conv_ms"]["significant"] and r["t_conv_ms"]["academic_label"] is None
    assert r["throughput_rps"]["design"] == "independent" and r["throughput_rps"]["unit"] == "batch" and r["throughput_rps"]["significant"]
    assert res["label"].startswith("EXPLORATORY") and res["environment_class"] == "PILOT" and "swarm|batch|bc1|h1|pso|r1|N20|c1" in res["normality_by_condition"]
    assert res["normality_by_condition"]["rules|c1"]["t_conv_ms"]["unit"].startswith("profile_mean")


def test_oe3_ofat_plan_uses_reference_and_holm(tmp_path):
    rng = np.random.default_rng(1)
    obs = []
    for c in oe3_one_factor_at_a_time():
        obs += [_row(c, f"p{i:02d}", t_conv_ms=40 + (30 if c.dispatch == "sequential" else 0) + rng.normal(0, 1) + i * .05) for i in range(25)]
    res = stats_cli.analyze_run(_write_run(tmp_path, "oe3", obs, []))
    t = res["contrasts"]["t_conv_ms"]
    assert t["reference"] == Condition().name and len(t["comparisons"]) == 6
    assert t["comparisons"][Condition(dispatch="sequential").name]["p_holm"] < 0.05 and t["comparisons"][Condition(broadcast_gbest=False).name]["p_holm"] > 0.05


def test_oe4_plan_and_validity_label_inherited(tmp_path):
    rng = np.random.default_rng(2)
    obs, bat = [], []
    for c in oe4_grid(concurrency=(1, 10, 50), n_particles=(20, 30)):
        obs += [_row(c, f"p{i:02d}", t_conv_ms=10 + c.n_particles / 2 + rng.normal(0, .3)) for i in range(20)]
        bat += [{"condition": c.name, "batch": b, "throughput_rps": 20 + c.concurrency / 10 + rng.normal(0, .1)} for b in range(4)]
    res = stats_cli.analyze_run(_write_run(tmp_path, "oe4", obs, bat, validity="OFFICIAL_CANDIDATE"))
    assert res["contrasts"]["throughput_across_load|N20"]["design"] == "k_independent" and res["contrasts"]["throughput_across_load|N20"]["significant"]
    assert res["contrasts"]["particles_effect_t_conv_at_c1"]["design"] == "k_paired" or res["contrasts"]["particles_effect_t_conv_at_c1"]["test"]
    assert res["label"].startswith("OFFICIAL_CANDIDATE")                               # hereda la etiqueta; no la eleva ni la rebaja


def test_unsupported_experiment_is_rejected(tmp_path):
    d = _write_run(tmp_path, "oe1", [], [])
    with pytest.raises(KeyError):
        stats_cli.analyze_run(d)
