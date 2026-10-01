"""`gold/rubric_v3.py` — P1 (inclusión relativa) y P2 (gold) aprobadas el 28/09/2026 (`ESPECIFICACION-METODOLOGICA-P1-P2-2026-09-28.md` §3 y §4).

Pruebas deterministas y puras (sin Redis, LLM, red ni BD). Fijan: P1 exacta (`e_m ≥ 1 ∧ e_m/Σe ≥ 0.20`, comparada en enteros), la matriz P2, audio solo en Balanced, sin desempate, un identificador propio de v3, un registro
de aprobación propio (vacío) y la no regresión de `rubric_v2` (sellado de K = 10 v2). Los vectores numéricos son de VERIFICACIÓN de la fórmula; ninguno procede de una corrida oficial.
"""

import hashlib
import itertools
import json
from fractions import Fraction
from pathlib import Path

import pytest

from adaptation_swarm.gold import f1_multilabel as f1m
from adaptation_swarm.gold import rubric_v2 as v2
from adaptation_swarm.gold import rubric_v3 as v3
from adaptation_swarm.gold.rubric_v2 import NoRuleSelected, RuleNotApproved
from adaptation_swarm.profiles.models import Archetype
from adaptation_swarm.pso.space import MODALITIES

BACKEND = Path(__file__).resolve().parents[2]
V2_OFFICIAL_VERSION = "gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2"
ORDER = {m: i for i, m in enumerate(MODALITIES)}                      # code, diagram, text, audio


def _incl(*emphasis):
    return v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID).predicted_set(emphasis)


# ── P1 · inclusión e_m ≥ 1 ∧ e_m/Σe ≥ 0.20 ───────────────────────────────────────────────────────────────────────
def test_A_a_modality_with_zero_emphasis_is_never_included():
    assert "audio" not in _incl(2, 2, 2, 0) and "text" not in _incl(2, 1, 0, 2)


def test_B_emphasis_one_below_twenty_percent_is_excluded():
    # e = (1, 2, 2, 2): Σ = 7 → s_code = 1/7 ≈ 0.143 < 0.20 → excluida; las demás (2/7 ≈ 0.286) se incluyen.
    assert _incl(1, 2, 2, 2) == {"diagram", "text", "audio"}


def test_C_a_modality_exactly_at_twenty_percent_is_included():
    # e = (1, 1, 1, 2): Σ = 5 → s = 1/5 = 0.20 exacto para code, diagram y text («≥» ⇒ se incluyen); audio 2/5 también.
    assert _incl(1, 1, 1, 2) == {"code", "diagram", "text", "audio"}
    # e = (1, 0, 0, 0): Σ = 1 → s = 1.0; e = (1, 2, 2, 0): Σ = 5 → code 0.20 exacto.
    assert _incl(1, 0, 0, 0) == {"code"} and _incl(1, 2, 2, 0) == {"code", "diagram", "text"}


def test_D_a_modality_above_twenty_percent_is_included():
    assert _incl(2, 1, 0, 0) == {"code", "diagram"}                  # 2/3 y 1/3
    assert _incl(2, 2, 0, 0) == {"code", "diagram"}


def test_E_each_modality_is_evaluated_independently():
    # e = (2, 1, 1, 1): Σ = 5 → code 0.40, el resto 0.20 → las cuatro. e = (2, 2, 2, 1): Σ = 7 → audio 1/7 < 0.20 → solo audio cae.
    assert _incl(2, 1, 1, 1) == {"code", "diagram", "text", "audio"}
    assert _incl(2, 2, 2, 1) == {"code", "diagram", "text"}
    assert _incl(1, 2, 2, 2) == {"diagram", "text", "audio"}


def test_F_the_denominator_is_the_sum_of_all_four_emphases():
    # Mismo e_audio = 1, distinto Σe: con Σ = 5 se incluye (1/5 = 0.20); con Σ = 6 y Σ = 7 queda excluida (1/6, 1/7 < 0.20). Solo cambia el total de las DEMÁS modalidades.
    assert "audio" in _incl(2, 2, 0, 1)                              # Σ = 5
    assert "audio" not in _incl(2, 2, 1, 1)                          # Σ = 6
    assert "audio" not in _incl(2, 2, 2, 1)                          # Σ = 7
    assert _incl(2, 2, 1, 1) == {"code", "diagram"}                  # code y diagram: 2/6 ≈ 0.33 ≥ 0.20; text y audio: 1/6 < 0.20


def test_empty_total_gives_an_empty_set():
    assert _incl(0, 0, 0, 0) == frozenset()                          # Σe = 0 ⇒ S = ∅ (F1 = 0)


def test_the_comparison_is_exact_integer_arithmetic_and_matches_a_rational_reference_for_all_81_vectors():
    ref = Fraction(1, 5)
    for e in itertools.product((0, 1, 2), repeat=4):
        total = sum(e)
        expected = frozenset() if total == 0 else frozenset(m for m, em in zip(MODALITIES, e) if em >= 1 and Fraction(em, total) >= ref)
        assert _incl(*e) == expected, e
        assert _incl(*e) == (frozenset() if total == 0 else frozenset(m for m, em in zip(MODALITIES, e) if em >= 1 and 5 * em >= total)), e


def test_the_inclusion_rule_is_the_relative_rule_not_a_threshold_or_top_set():
    assert set(v3.INCLUSION_RULES) == {"incl-rel20"}
    # Un umbral `e ≥ 1` incluiría todas las modalidades con e ≥ 1 (incl-ge1 de v2); la regla relativa excluye la de 1/7.
    assert v2.INCLUSION_RULES["incl-ge1"].predicted_set((1, 2, 2, 2)) == {"code", "diagram", "text", "audio"} != _incl(1, 2, 2, 2)


@pytest.mark.parametrize("bad", [(1, 1, 1), (1, 1, 1, 1, 1), (3, 0, 0, 0), (-1, 1, 1, 1)])
def test_invalid_emphasis_vectors_are_rejected(bad):
    with pytest.raises(ValueError):
        _incl(*bad)


# ── P2 · matriz del gold ─────────────────────────────────────────────────────────────────────────────────────────
def _gold(arch):
    return v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID).expected_set(arch)


def test_G_visual_dominant_is_exactly_diagram_and_code():
    assert _gold(Archetype.VISUAL_DOMINANT) == {"diagram", "code"}


def test_H_logical_syntactic_is_exactly_code_and_diagram():
    assert _gold(Archetype.LOGICAL_SYNTACTIC) == {"code", "diagram"}


def test_I_explanatory_conceptual_is_exactly_text_diagram_and_code():
    assert _gold(Archetype.EXPLANATORY_CONCEPTUAL) == {"text", "diagram", "code"}


def test_J_balanced_multimodal_is_exactly_the_four_modalities():
    assert _gold(Archetype.BALANCED_MULTIMODAL) == {"code", "diagram", "text", "audio"}


def test_K_audio_appears_only_in_balanced():
    for arch in (Archetype.VISUAL_DOMINANT, Archetype.LOGICAL_SYNTACTIC, Archetype.EXPLANATORY_CONCEPTUAL):
        assert "audio" not in _gold(arch), arch
    assert [a for a in Archetype if "audio" in _gold(a)] == [Archetype.BALANCED_MULTIMODAL]


def test_L_balanced_contains_every_modality():
    assert _gold(Archetype.BALANCED_MULTIMODAL) == frozenset(MODALITIES)


def test_M_no_tie_break_balanced_is_never_collapsed_to_one_modality():
    g = _gold(Archetype.BALANCED_MULTIMODAL)
    assert len(g) == 4
    assert all(len(_gold(a)) >= 2 for a in Archetype)                # ningún arquetipo se reduce a una sola modalidad


def test_the_gold_depends_only_on_the_archetype_not_on_the_difficulty():
    from adaptation_swarm.profiles.models import Difficulty
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    for arch in Archetype:
        assert {rule.expected_set(arch, d) for d in Difficulty} | {rule.expected_set(arch, None)} == {_gold(arch)}


def test_the_gold_matrix_is_frozen_with_a_stable_fingerprint():
    g = v3.GOLD_RULES[v3.GOLD_RULE_VERSION]
    assert g.fingerprint() == v3.GoldRuleV3(g.rule_version, g.description, dict(g.expected_by_archetype)).fingerprint()
    altered = dict(g.expected_by_archetype) | {Archetype.VISUAL_DOMINANT: frozenset({"diagram"})}
    assert v3.GoldRuleV3(g.rule_version, g.description, altered).fingerprint() != g.fingerprint()
    assert g.to_dict()["expected_by_archetype"]["balanced_multimodal"] == ["code", "diagram", "text", "audio"]


def test_the_gold_requires_the_four_archetypes_and_rejects_empty_or_unknown_sets():
    with pytest.raises(ValueError):
        v3.GoldRuleV3("x", "x", {Archetype.VISUAL_DOMINANT: frozenset({"code"})})
    full = {a: frozenset({"code"}) for a in Archetype}
    with pytest.raises(ValueError):
        v3.GoldRuleV3("x", "x", {**full, Archetype.LOGICAL_SYNTACTIC: frozenset()})
    with pytest.raises(ValueError):
        v3.GoldRuleV3("x", "x", {**full, Archetype.LOGICAL_SYNTACTIC: frozenset({"video"})})


# ── N · versión propia ───────────────────────────────────────────────────────────────────────────────────────────
def test_N_the_v3_identifier_is_defined_and_differs_from_v2():
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    assert rule.rule_version == v3.RULE_VERSION == "gold-v3-multimodal+incl-rel20" and v3.official_version(rule) == v3.RULE_VERSION
    assert v3.FAMILY == "gold-v3" != v2.FAMILY and V2_OFFICIAL_VERSION not in v3.RULE_VERSION
    assert "v2" not in v3.RULE_VERSION and v3.GOLD_RULE_VERSION not in v2.GOLD_RULES


# ── O · aprobación con registro propio ───────────────────────────────────────────────────────────────────────────
def test_O_v3_has_its_own_empty_approval_registry_so_its_rule_is_provisional_until_sealed():
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    assert v3.APPROVED_RULE_VERSIONS == frozenset()
    assert v3.is_registered_v3(rule) and not v3.is_approved(rule) and v3.status_of(rule) == v3.STATUS_PROVISIONAL
    with pytest.raises(RuleNotApproved):
        v3.require_approved(rule)


def test_O_v3_functions_use_their_own_registry_and_do_not_touch_the_v2_one(monkeypatch):
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    monkeypatch.setattr(v3, "APPROVED_RULE_VERSIONS", frozenset({v3.official_version(rule)}))                      # registro v3 en memoria
    assert v3.is_approved(rule) and v3.status_of(rule) == v3.STATUS_OFFICIAL and v3.GOLD_RULES[v3.GOLD_RULE_VERSION].status == v3.STATUS_OFFICIAL
    v3.require_approved(rule)
    assert v2.APPROVED_RULE_VERSIONS == frozenset({V2_OFFICIAL_VERSION}) and not v2.is_approved(rule)              # v2 intacto y no la reconoce


def test_O_an_altered_copy_or_a_v2_rule_is_not_registered_even_if_it_repeats_a_version(monkeypatch):
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    monkeypatch.setattr(v3, "APPROVED_RULE_VERSIONS", frozenset({v3.official_version(rule)}))
    copy_gold = v3.GoldRuleV3(rule.gold.rule_version, "copia", dict(rule.gold.expected_by_archetype))
    assert not v3.is_approved(v3.MultilabelRuleV3(copy_gold, rule.inclusion))
    assert not v3.is_approved(v2.get_rule("gold-v2-cand-A", "incl-ge1"))
    assert not v2.is_approved(rule)


def test_no_default_rule_is_selected_silently():
    with pytest.raises(NoRuleSelected):
        v3.get_rule()
    with pytest.raises(NoRuleSelected):
        v3.get_rule(v3.GOLD_RULE_VERSION, None)
    with pytest.raises(KeyError):
        v3.get_rule("gold-v3-otra", v3.INCLUSION_RULE_ID)


# ── contrato EvaluationRule: consumible por f1_multilabel ─────────────────────────────────────────────────────────
def test_the_rule_can_be_consumed_by_the_multilabel_metric_as_a_provisional_rule():
    rule = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID)
    # S = (e_code, v_code, e_diagram, v_diagram, e_text, v_text, e_audio, v_audio)
    records = [{"profile_id": "a", "archetype": "visual_dominant", "difficulty": "sequential", "S": [1, 0, 2, 0, 0, 0, 0, 0]},          # Σ=3 → {code, diagram} = gold → F1 = 1
               {"profile_id": "b", "archetype": "balanced_multimodal", "difficulty": "functions", "S": [2, 0, 2, 0, 2, 0, 1, 0]},      # Σ=7 → audio 1/7 excluida → Dice(3,4) = 6/7
               {"profile_id": "c", "archetype": "explanatory_conceptual", "difficulty": "repetitive", "S": [0, 0, 0, 0, 0, 0, 0, 0]}]  # Σ=0 → ∅ → F1 = 0
    cases = f1m.cases_from_records(records, rule)
    report = f1m.multilabel_report(cases, rule, require_official=False)
    by_id = {d["profile_id"]: d["f1"] for d in report.per_case}
    assert by_id == {"a": 1.0, "b": pytest.approx(6 / 7), "c": 0.0}
    assert report.status == "PROVISIONAL" and report.rule["rule_version"] == v3.RULE_VERSION and report.n_empty_predicted == 1


def test_to_dict_records_the_exact_rule_for_the_future_preregistration():
    d = v3.get_rule(v3.GOLD_RULE_VERSION, v3.INCLUSION_RULE_ID).to_dict()
    assert d["inclusion"]["share"] == "1/5" and d["inclusion"]["min_emphasis"] == 1 and "sum(e) = 0" in d["inclusion"]["empty_total"]
    assert d["gold"]["depends_on"] == "archetype only"
    json.dumps(d)                                                                                              # serializable


# ── P · no regresión de rubric_v2 (sellado de K = 10 v2) ─────────────────────────────────────────────────────────
def test_P_rubric_v2_registries_and_version_are_unchanged():
    assert v2.APPROVED_RULE_VERSIONS == frozenset({V2_OFFICIAL_VERSION}) and v2.PANEL_PROTOCOL_VERSION == "panel-arq-ac1-maj-tie0-v2" and v2.FAMILY == "gold-v2"
    assert set(v2.INCLUSION_RULES) == {"incl-ge1", "incl-ge2", "incl-top-tol0", "incl-top-tol1"} and "incl-rel20" not in v2.INCLUSION_RULES
    assert set(v2.GOLD_RULES) == {"gold-v2-cand-A", "gold-v2-cand-B-tol0.05", "gold-v2-cand-B-tol0.35"} and v3.GOLD_RULE_VERSION not in v2.GOLD_RULES
    assert v2.is_approved(v2.get_rule("gold-v2-cand-A", "incl-ge1"))


def test_P_rubric_v2_source_is_the_one_used_by_the_official_k10_v2_run():
    manifest = BACKEND / "official_runs" / "k10_official_2026-09-27" / "manifest.json"
    if not manifest.exists():
        pytest.skip("manifiesto oficial K=10 v2 no disponible")
    recorded = json.loads(manifest.read_text(encoding="utf-8"))["modules"]["gold/rubric_v2.py"]
    assert hashlib.sha256((BACKEND / "adaptation_swarm" / "gold" / "rubric_v2.py").read_bytes()).hexdigest() == recorded


def test_the_v3_layer_is_not_part_of_the_v2_fingerprints():
    from adaptation_swarm.analysis import replicas as rp
    assert not any("v3" in k for k in rp.module_fingerprints())
