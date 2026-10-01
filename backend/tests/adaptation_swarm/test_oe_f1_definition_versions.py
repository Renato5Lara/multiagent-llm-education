"""Definición F1 versionada en `oe/definitions.py` y en el provenance de OE (Fase 3): v2 histórica (K10 v2) y v3 PROVISIONAL conviven sin fallback ni aprobación implícita; los provenance históricos no cambian."""

import json
from pathlib import Path

import pytest

from adaptation_swarm.gold import rubric_v2, rubric_v3
from adaptation_swarm.metrics import panel_versions as pv
from adaptation_swarm.oe import definitions as D
from adaptation_swarm.oe import runner
from adaptation_swarm.oe.conditions import oe2_systems

PILOTS = Path(__file__).resolve().parents[2] / "experiments" / "oe_pilots_2026-10-01"
V2, V3 = D.F1_DEFINITION_VERSIONS["v2"], D.F1_DEFINITION_VERSIONS["v3"]


def test_v2_is_exactly_the_historical_definition_and_the_historical_key_is_v2():
    assert V2["formula"] == "P_i = {m : e_m ≥ 1}" and V2["inclusion_integer_form"] == "e_m >= 1" and V2["inclusion_rule_id"] == "incl-ge1"
    assert V2["status"] == D.STATUS_F1_V2 == "HISTORICAL_OFFICIAL_V2" and V2["official"] is True and "k10_official_2026-09-27" in V2["associated_runs"][0]
    assert V2["rule_version"] == rubric_v2.get_rule("gold-v2-cand-A", "incl-ge1").rule_version == "gold-v2-cand-A+incl-ge1"
    assert V2["full_rule_version"] in rubric_v2.APPROVED_RULE_VERSIONS and V2["panel_protocol_version"] == rubric_v2.PANEL_PROTOCOL_VERSION
    assert V2["gold_expected_by_archetype"] == {"visual_dominant": ["diagram"], "logical_syntactic": ["code"], "explanatory_conceptual": ["text"], "balanced_multimodal": ["code", "diagram", "text", "audio"]}
    h = D.DEFINITIONS["quality_f1_adapt"]                                                    # clave histórica: contenido de v2, ahora con su versión declarada
    assert h["definition_version"] == "v2" and h["definition"].startswith("F1_i = 2|G_i ∩ P_i|/(|G_i|+|P_i|), P_i = {m : e_m ≥ 1}") and "26/09" in h["source"]


def test_v3_is_exactly_the_specified_definition_derived_from_rubric_v3():
    assert V3["formula"] == "S = {m | e_m ≥ 1 ∧ e_m/Σe ≥ 0.20}" and V3["inclusion_integer_form"] == "5*e_m >= sum(e)" and (V3["min_emphasis"], V3["share"]) == (1, "1/5")
    assert V3["inclusion_rule_id"] == rubric_v3.INCLUSION_RULE_ID == "incl-rel20" and V3["rule_version"] == rubric_v3.RULE_VERSION and V3["empty_total"].startswith("sum(e) = 0")
    assert V3["gold_expected_by_archetype"] == {"visual_dominant": ["code", "diagram"], "logical_syntactic": ["code", "diagram"], "explanatory_conceptual": ["code", "diagram", "text"],
                                               "balanced_multimodal": ["code", "diagram", "text", "audio"]}
    rule = rubric_v3.INCLUSION_RULES["incl-rel20"]                                            # la forma entera de la definición coincide con lo que evalúa rubric_v3
    for e, expected in (((2, 2, 2, 1), {"code", "diagram", "text"}), ((2, 2, 1, 1), {"code", "diagram"}), ((1, 1, 1, 2), {"code", "diagram", "text", "audio"})):
        assert rule.predicted_set(e) == expected


def test_v2_and_v3_are_different_and_v3_is_provisional_not_approved():
    assert V2 != V3 and V2["formula"] != V3["formula"] and V2["rule_version"] != V3["rule_version"] and V2["gold_expected_by_archetype"] != V3["gold_expected_by_archetype"]
    assert V3["status"] == D.STATUS_F1_V3 == "PROVISIONAL_NOT_APPROVED" and V3["official"] is False and V3["approved"] is False and V3["approved_in"] is None
    assert V3["rule_version"] not in rubric_v3.APPROVED_RULE_VERSIONS and rubric_v3.APPROVED_RULE_VERSIONS == frozenset() and V3["associated_runs"] == []
    assert V3["full_rule_version"] is None and V3["panel_protocol_version"] is None and "full_rule_version" in V3["pending"] and "panel_protocol_version" in V3["pending"]


def test_explicit_selection_returns_that_version_and_the_historical_query_returns_v2_with_no_silent_fallback():
    assert D.f1_definition("v3") is V3 and D.f1_definition("v2") is V2 and D.f1_definition() is V2 and D.f1_definition(None) is V2
    for bad in ("v4", "", "V3", "gold-v3-multimodal+incl-rel20"):
        with pytest.raises(KeyError):
            D.f1_definition(bad)
    assert D.f1_selection_record("v3")["selected"] == "v3" and D.f1_selection_record("v3")["official"] is False and D.f1_selection_record("v3")["full_rule_version"] is None
    assert D.f1_selection_record("v2")["status"] == "HISTORICAL_OFFICIAL_V2" and D.f1_selection_record(None)["selected"] is None
    with pytest.raises(KeyError):
        D.f1_selection_record("v4")


def test_definitions_are_consistent_with_the_panel_registry_and_never_cross_versions():
    pairs = ((V2, pv.SPEC_V2, pv.SPEC_V3), (V3, pv.SPEC_V3, pv.SPEC_V2))
    for d, own, other in pairs:
        assert (d["gold_rule_version"], d["inclusion_rule_id"]) == (own.gold_rule_version, own.inclusion_rule_id)
        assert d["gold_expected_by_archetype"] == {a: list(s) for a, s in own.expected_sets.items()}
        assert (d["gold_rule_version"], d["inclusion_rule_id"]) != (other.gold_rule_version, other.inclusion_rule_id)
        assert d["gold_expected_by_archetype"] != {a: list(s) for a, s in other.expected_sets.items()}
    assert V3["rule_version"] not in pv.SPEC_V2.rule_version and V2["rule_version"] not in pv.SPEC_V3.rule_version        # panel v2 ≠ regla v3; panel v3 provisional ≠ regla v2
    assert pv.SPEC_V2.official and not pv.SPEC_V3.official and V2["official"] and not V3["official"]


class _Args:
    experiment, label, k, batches, warmup, batch_seed, concurrency, design, particles = "oe2", "t", 1, 1, 1, runner.DEFAULT_BATCH_SEED, [1], None, None


@pytest.mark.requires_library_audio
def test_new_provenance_records_the_selected_f1_version(store, tmp_path):
    prov = runner.provenance(store, runner.DEFAULT_PROFILES, _Args, oe2_systems(1), 100)
    d = prov["definitions"]
    assert d["f1_selected"]["selected"] is None and set(d["f1_definition_versions"]) == {"v2", "v3"} and d["registry"]["quality_f1_adapt"]["definition_version"] == "v2"

    class V3Args(_Args):
        f1_definition_version = "v3"
    sel = runner.provenance(store, runner.DEFAULT_PROFILES, V3Args, oe2_systems(1), 100)["definitions"]["f1_selected"]
    assert sel["selected"] == "v3" and sel["status"] == "PROVISIONAL_NOT_APPROVED" and sel["official"] is False and sel["full_rule_version"] is None
    assert sel["rule_version"] == rubric_v3.RULE_VERSION != D.f1_definition("v2")["rule_version"]

    class V2Args(_Args):
        f1_definition_version = "v2"
    assert runner.provenance(store, runner.DEFAULT_PROFILES, V2Args, oe2_systems(1), 100)["definitions"]["f1_selected"]["status"] == "HISTORICAL_OFFICIAL_V2"
    with pytest.raises(FileExistsError):                                                       # un directorio existente (p. ej. un piloto histórico) nunca se reescribe
        runner.write_results(tmp_path, prov, [], [])


def test_historical_pilot_manifests_were_not_migrated():
    seen = 0
    for p in sorted(PILOTS.glob("*/provenance.json")) if PILOTS.exists() else []:
        prov = json.loads(p.read_text(encoding="utf-8"))
        seen += 1
        assert "f1_selected" not in prov.get("definitions", {}) and "f1_definition_versions" not in prov.get("definitions", {}), p       # los escritos antes de la Fase 3 no cambian de significado
    if not seen:
        pytest.skip("no hay directorios piloto locales (no versionados)")


def test_oe1_requires_the_f1_definition_version_when_an_f1_result_is_given(tmp_path):
    from adaptation_swarm.oe import oe1
    f1 = tmp_path / "f1.json"
    f1.write_text('{"f1_adapt": 0.9}')
    with pytest.raises(SystemExit, match="--f1-definition-version"):
        oe1.main(["--runs", str(tmp_path), "--out-dir", str(tmp_path / "o"), "--f1-json", str(f1)])
