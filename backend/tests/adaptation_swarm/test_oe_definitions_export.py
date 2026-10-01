"""Registro de definiciones (aprobadas vs PENDING) y exportación de datos para la fase estadística (observaciones, no promedios)."""

import csv
import io

from adaptation_swarm.oe import definitions as D
from adaptation_swarm.oe import export as E


def test_registry_distinguishes_approved_from_pending_and_cites_sources():
    assert {v["status"] for v in D.DEFINITIONS.values()} <= {D.APPROVED, D.PARTIAL, D.PENDING}
    for k in ("t_conv", "latency_l_resp", "quality_f1_adapt", "usability_sus", "reference_value_75", "statistical_unit_f1"):
        assert D.DEFINITIONS[k]["status"] == D.APPROVED and D.DEFINITIONS[k]["source"] != "—", k
    for k in ("compliance_score_oe1", "reliability_oe1", "t_conv_baselines", "statistical_unit_performance"):
        assert D.DEFINITIONS[k]["status"] == D.PENDING, k
    assert "75" in D.DEFINITIONS["reference_value_75"]["definition"] and "T_conv" in D.DEFINITIONS["efficiency_of_adaptation_oe3"]["definition"]
    assert D.blocked_for("oe1") == ["compliance_score_oe1", "reliability_oe1"] and D.blocked_for("oe5") == []


def _obs():
    base = {"condition": "swarm|a", "status": "completed", "profile_id": "p1", "archetype": "x", "difficulty": "y", "replicate": 0, "batch": 0, "seed": 7, "t_start_utc": "2026-10-01T00:00:00.000+00:00",
            "t_conv_ms": 12.5, "latency_ms": 15.0, "k_stop": 2, "F": 0.5, "gap_vs_optimum": 0.01, "S": [1, 2, 0, 1, 1, 1, 2, 0], "f_system": "swarm", "f_concurrency": 1, "n_messages": 40, "comm_overhead_ms": None}
    return [base, {**base, "profile_id": "p2", "latency_ms": 20.0, "k_stop": None}]


def test_raw_csv_keeps_one_row_per_observation_with_seed_timestamp_and_factors():
    rows = list(csv.DictReader(io.StringIO(E.raw_observations_csv("lab", "oe3", _obs()))))
    assert len(rows) == 2 and rows[0]["run_label"] == "lab" and rows[0]["experiment"] == "oe3" and rows[0]["seed"] == "7" and rows[0]["S"] == "1-2-0-1-1-1-2-0"
    assert rows[0]["t_start_utc"].startswith("2026-10-01") and rows[0]["f_system"] == "swarm" and rows[1]["k_stop"] == "" and rows[0]["profile_id"] == "p1"


def test_statistical_input_is_long_and_has_explicit_units():
    bat = [{"condition": "swarm|a", "batch": 0, "throughput_rps": 21.5, "t_start_utc": "2026-10-01T00:00:00.000+00:00"}, {"condition": "swarm|a", "batch": 1, "throughput_rps": None}]
    rows = E.statistical_input_rows("lab", "oe4", _obs(), bat)
    lat = [r for r in rows if r["metric"] == "latency_ms"]
    assert [r["value"] for r in lat] == [15.0, 20.0] and {r["unit_type"] for r in lat} == {"profile"} and [r["unit_id"] for r in lat] == ["p1", "p2"]
    assert not [r for r in rows if r["metric"] == "k_stop" and r["unit_id"] == "p2"]               # los None no se exportan como cero
    thr = [r for r in rows if r["metric"] == "throughput_rps"]
    assert len(thr) == 1 and thr[0]["unit_type"] == "batch" and thr[0]["unit_id"] == "batch:0" and thr[0]["value"] == 21.5
    assert set(E.LONG_FIELDS) == set(rows[0])
    text = E.statistical_input_csv("lab", "oe4", _obs(), bat)
    assert text.splitlines()[0].split(",") == list(E.LONG_FIELDS)
