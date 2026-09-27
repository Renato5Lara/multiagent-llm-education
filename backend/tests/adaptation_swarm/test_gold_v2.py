"""Métrica de inclusión/exclusión 4×4 con audio y reglas gold-v2 (respuesta del asesor, 2026-09-25: D1, D2). Puras: sin PostgreSQL, Redis, audio ni red.
Comprueban dimensiones 4×4, presencia del audio, que la regla de Balanced NO se fija en silencio, reproducibilidad, compatibilidad exacta con la evidencia histórica y
separación entre gold-v1 (histórico, intacto) y gold-v2 (candidatas provisionales)."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from adaptation_swarm.gold import f1 as f1_hist
from adaptation_swarm.gold import rubric as rubric_v1
from adaptation_swarm.gold import rubric_v2
from adaptation_swarm.gold.f1_multilabel import AGGREGATIONS, CaseLabels, bootstrap_ci, case_f1, cases_from_records, multilabel_report
from adaptation_swarm.gold.labels_v2 import ALL_MODALITIES, emphasis_from_S, from_indicator, modality_set, to_indicator
from adaptation_swarm.gold.rubric_v2 import (APPROVED_RULE_VERSIONS, GOLD_RULES, INCLUSION_RULES, LegacyDominantRule, NoRuleSelected, RuleNotApproved,
                                             get_rule, official_version, require_approved)
from adaptation_swarm.profiles.models import Archetype, Difficulty
from adaptation_swarm.pso.space import MODALITIES

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "backend" / "experiments" / "results"
PKG = ROOT / "backend" / "adaptation_swarm"
S = frozenset


def _c(pid, gold, pred, arch=None):
    return CaseLabels(pid, None if gold is None else S(gold), S(pred), arch)


def _hand_cases():
    return [_c("c1", {"code", "audio"}, {"code"}), _c("c2", {"diagram"}, {"diagram", "text"}),
            _c("c3", {"text", "audio"}, {"audio"}), _c("c4", set(MODALITIES), set(MODALITIES))]


LEGACY = LegacyDominantRule()


# ── etiquetas y dimensiones ─────────────────────────────────────────────────────────────────────────────────────────
def test_modality_labels_are_validated_ordered_and_include_audio():
    assert MODALITIES == ("code", "diagram", "text", "audio") and ALL_MODALITIES == S(MODALITIES)
    with pytest.raises(ValueError, match="desconocidas"):
        modality_set({"code", "video"})
    assert to_indicator(S({"diagram", "audio"})) == (0, 1, 0, 1) and from_indicator((1, 0, 1, 0)) == S({"code", "text"})
    with pytest.raises(ValueError):
        from_indicator((1, 0, 2, 0))
    assert emphasis_from_S([2, 0, 1, 1, 0, 2, 2, 0]) == (2, 1, 0, 2)                # dimensiones 0, 2, 4, 6
    with pytest.raises(ValueError):
        emphasis_from_S([3, 0, 0, 0, 0, 0, 0, 0])


def test_the_matrix_is_4x4_and_audio_is_a_first_class_modality():
    rep = multilabel_report(_hand_cases(), LEGACY)
    m = np.array(rep.matrix_4x4)
    assert m.shape == (4, 4) and list(rep.per_modality) == list(MODALITIES) and "audio" in rep.per_modality
    audio = rep.per_modality["audio"]
    assert (audio["tp"], audio["fp"], audio["fn"], audio["tn"]) == (2, 0, 1, 1) and audio["support"] == 3       # el audio puntúa: TP y FN reales
    assert np.trace(m) == sum(d["tp"] for d in rep.per_modality.values())                                          # la diagonal es TP


def test_scores_match_a_hand_computed_example():
    rep = multilabel_report(_hand_cases(), LEGACY)
    pm = rep.per_modality
    assert (pm["code"]["f1"], pm["diagram"]["f1"]) == (1.0, 1.0) and pm["text"]["f1"] == pytest.approx(0.5) and pm["audio"]["f1"] == pytest.approx(0.8)
    assert pm["audio"]["recall"] == pytest.approx(2 / 3) and pm["text"]["precision"] == pytest.approx(0.5)
    assert rep.f1("macro_defined") == pytest.approx(0.825) and rep.f1("macro_all4") == pytest.approx(0.825)
    assert rep.micro["tp"] == 7 and rep.micro["fp"] == 1 and rep.micro["fn"] == 2 and rep.f1("micro") == pytest.approx(14 / 17)
    assert [d["f1"] for d in rep.per_case] == pytest.approx([2 / 3, 2 / 3, 2 / 3, 1.0]) and rep.f1("samples") == pytest.approx(0.75)
    assert rep.exact_match == pytest.approx(0.25)
    assert rep.matrix_4x4 == [[2, 1, 1, 1], [1, 2, 2, 1], [1, 1, 1, 2], [2, 1, 1, 2]]


def test_zero_division_follows_the_historical_convention():
    cases = [_c("a", {"code"}, {"code"}), _c("b", {"code"}, {"code", "audio"})]
    pm = multilabel_report(cases, LEGACY).per_modality
    assert pm["diagram"]["f1"] is None and pm["diagram"]["precision"] is None and pm["diagram"]["recall"] is None       # ni gold ni predicho
    assert pm["audio"]["precision"] == 0.0 and pm["audio"]["recall"] is None and pm["audio"]["f1"] == 0.0                # solo falso positivo
    rep = multilabel_report(cases, LEGACY)
    assert rep.macro_defined == pytest.approx(0.5)              # (code 1.0 + audio 0.0) / 2: diagram y text (0/0) no cuentan
    assert rep.macro_all4 == pytest.approx(0.25)                # (1.0 + 0 + 0 + 0) / 4: con 0/0 ⇒ 0


def test_cases_without_gold_are_excluded_and_counted_and_empty_sets_are_handled():
    rep = multilabel_report([_c("a", {"code"}, {"code"}), _c("b", None, {"text"}), _c("c", {"text"}, set()), _c("d", set(), set())], LEGACY)
    assert rep.n_cases == 3 and rep.n_no_gold == 1 and rep.n_empty_predicted == 2 and rep.n_case_f1_undefined == 1      # d: gold y predicho vacíos
    assert case_f1(S(), S()) is None and case_f1(S({"code"}), S()) == 0.0 and rep.samples["n_defined"] == 2
    with pytest.raises(ValueError, match="sin casos"):
        multilabel_report([_c("x", None, {"code"})], LEGACY)


def test_there_is_no_default_aggregation_for_f1_adapt():
    rep = multilabel_report(_hand_cases(), LEGACY)
    assert not hasattr(rep, "f1_adapt") and set(AGGREGATIONS) == {"macro_defined", "macro_all4", "micro", "samples"}     # la elección es del asesor (P3)
    with pytest.raises(ValueError, match="agregación desconocida"):
        rep.f1("f1_adapt")


def test_output_is_reproducible_versioned_and_json_serializable():
    a, b = multilabel_report(_hand_cases(), LEGACY), multilabel_report(_hand_cases(), LEGACY)
    assert a.content_hash() == b.content_hash() and json.dumps(a.to_dict(), sort_keys=True) == json.dumps(b.to_dict(), sort_keys=True)
    assert a.to_dict()["metric_version"] == "f1-multilabel-v2"
    changed = multilabel_report(_hand_cases()[:3], LEGACY)
    assert changed.content_hash() != a.content_hash()
    r1 = bootstrap_ci(_hand_cases(), LEGACY, "samples", np.random.default_rng(7), n_boot=200)
    assert r1 == bootstrap_ci(_hand_cases(), LEGACY, "samples", np.random.default_rng(7), n_boot=200) and 0 <= r1[0] <= r1[1] <= 1


# ── inclusión: cuándo una modalidad cuenta como «incluida» ──────────────────────────────────────────────────────────
def test_inclusion_rules_have_explicit_and_different_semantics():
    e = (2, 0, 1, 2)
    pred = {k: r.predicted_set(e) for k, r in INCLUSION_RULES.items()}
    assert pred["incl-ge1"] == S({"code", "text", "audio"}) and pred["incl-ge2"] == S({"code", "audio"})
    assert pred["incl-top-tol0"] == S({"code", "audio"}) and pred["incl-top-tol1"] == S({"code", "text", "audio"})
    assert INCLUSION_RULES["incl-ge1"].predicted_set((0, 0, 0, 0)) == S() and INCLUSION_RULES["incl-top-tol0"].predicted_set((0, 0, 0, 0)) == ALL_MODALITIES


# ── Balanced: la regla no se fija en silencio ───────────────────────────────────────────────────────────────────────
def test_no_default_rule_and_no_rule_is_approved():
    assert APPROVED_RULE_VERSIONS == frozenset()
    for args in ((None, None), ("gold-v2-cand-A", None), (None, "incl-ge1"), ("", "")):
        with pytest.raises(NoRuleSelected):
            get_rule(*args)
    with pytest.raises(KeyError, match="regla desconocida"):
        get_rule("gold-v9", "incl-ge1")
    rule = get_rule("gold-v2-cand-A", "incl-ge1")
    with pytest.raises(RuleNotApproved):
        require_approved(rule)
    with pytest.raises(RuleNotApproved):
        multilabel_report(_hand_cases(), rule, require_official=True)
    assert multilabel_report(_hand_cases(), rule).status == "PROVISIONAL" and all(g.status == "PROVISIONAL" for g in GOLD_RULES.values())


def test_the_approval_gate_is_the_only_way_a_rule_becomes_official(monkeypatch):
    rule = get_rule("gold-v2-cand-A", "incl-ge1")
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(rule)}))
    require_approved(rule)
    assert multilabel_report(_hand_cases(), rule, require_official=True).status == "OFICIAL"
    assert multilabel_report(_hand_cases(), get_rule("gold-v2-cand-A", "incl-ge2")).status == "PROVISIONAL"      # otra regla sigue sin aprobar


def test_balanced_is_defined_by_an_expected_set_not_by_a_tie_break():
    A = GOLD_RULES["gold-v2-cand-A"]
    assert A.expected_set(Archetype.BALANCED_MULTIMODAL, Difficulty.SEQUENTIAL) == ALL_MODALITIES and "audio" in A.expected_set(Archetype.BALANCED_MULTIMODAL)
    assert A.expected_set(Archetype.VISUAL_DOMINANT) == S({"diagram"}) and A.expected_set(Archetype.LOGICAL_SYNTACTIC) == S({"code"})
    assert rubric_v1.expected_dominant(Archetype.BALANCED_MULTIMODAL, Difficulty.SEQUENTIAL) == "code"             # gold-v1 sigue con el desempate (intacto)
    tol005, tol035 = GOLD_RULES["gold-v2-cand-B-tol0.05"], GOLD_RULES["gold-v2-cand-B-tol0.35"]
    assert all(tol005.expected_set(a) == A.expected_set(a) for a in Archetype)                                     # con centroids-v1 equivale a A
    assert tol035.expected_set(Archetype.VISUAL_DOMINANT) == S({"diagram", "code"}) and tol035.expected_set(Archetype.BALANCED_MULTIMODAL) == ALL_MODALITIES


def test_cell_overrides_and_undefined_gold_are_supported():
    g = rubric_v2.GoldRuleV2("gold-v2-test", "prueba", {a: S({"code"}) for a in Archetype}, {(Archetype.VISUAL_DOMINANT, Difficulty.FUNCTIONS): None})
    assert g.expected_set(Archetype.VISUAL_DOMINANT, Difficulty.FUNCTIONS) is None and g.expected_set(Archetype.VISUAL_DOMINANT, Difficulty.SEQUENTIAL) == S({"code"})
    assert g.fingerprint() == g.fingerprint() and len(g.fingerprint()) == 64


# ── separación rule-v1 / rule-v2 y compatibilidad con lo histórico ──────────────────────────────────────────────────
def test_v1_and_v2_are_separated():
    assert rubric_v1.RULE_VERSION == "gold-v1" and all(v.startswith("gold-v2") for v in GOLD_RULES) and "gold-v1" not in "".join(GOLD_RULES)
    assert LEGACY.rule_version.startswith("gold-v1") and LEGACY.rule_version not in GOLD_RULES
    assert set(get_rule("gold-v2-cand-A", "incl-ge1").to_dict()) == {"rule_version", "gold", "inclusion"}


@pytest.mark.parametrize("label", ["corrida-poc-1", "corrida-poc-2"])
def test_the_legacy_rule_reproduces_the_frozen_runs_exactly(label):
    cases = [c for c in json.loads((RESULTS / f"adaptation_swarm_{label}.json").read_text(encoding="utf-8"))["cases"] if c["status"] == "completed"]
    hist = f1_hist.f1_report([(c["expected"], c["predicted"]) for c in cases])
    rep = multilabel_report(cases_from_records(cases, LEGACY), LEGACY)
    assert rep.n_cases == 100 and rep.matrix_4x4 == hist.confusion.tolist()                                        # la co-ocurrencia con etiquetas de 1 elemento = matriz clásica
    assert all(rep.per_modality[m]["f1"] == hist.per_class[m].f1 for m in MODALITIES)
    assert rep.f1("macro_defined") == hist.f1_adapt == pytest.approx(0.8031, abs=1e-4) and rep.f1("macro_all4") == hist.macro_f1_all4
    assert rep.f1("micro") == rep.f1("samples") == hist.accuracy == rep.exact_match


def test_historical_modules_and_data_are_untouched():
    """Los módulos y datos históricos no se modifican: si estos hashes cambian, es una decisión deliberada que debe registrarse (no un efecto colateral del v2)."""
    pins = {PKG / "gold" / "f1.py": "78ed4e2004bbb5d37088b1d2363d47c93f2e611a48bedfa28e2047964cf52512",
            PKG / "gold" / "rubric.py": "779cac7238de1e1ea7f92bf2fbff52059f3ae6aae67dd11f6304d9c4589f87f2",
            PKG / "gold" / "dataset.py": "98459ccf58ebaede5eedf49ad939396a25b85059d5e2c060010c4235beaa7e71",
            ROOT / "datasets" / "synthetic_profiles" / "gold-v1.jsonl": "3bc437678e71e94e58540c3406d3323e1d1383ea26828e3f6a6b2c65d66df288",
            RESULTS / "adaptation_swarm_sensitivity.json": "d59ff801b331286e952509da95418f8aaf717b2549942c22a061dd307261c906"}
    for path, sha in pins.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha, f"{path.name} cambió"
    src = "\n".join((PKG / "gold" / f).read_text(encoding="utf-8") for f in ("f1_multilabel.py", "rubric_v2.py", "labels_v2.py"))
    assert "open(" not in src and "write_text" not in src and "write_bytes" not in src                              # los módulos nuevos no escriben nada


# ── B: solo se aprueban reglas gold-v2 registradas; nunca las históricas ni las ad hoc ──────────────────────────────
def test_only_registered_gold_v2_rules_can_be_approved_and_the_set_is_still_empty():
    from adaptation_swarm.gold.rubric_v2 import is_approved, is_registered_v2, status_of
    assert APPROVED_RULE_VERSIONS == frozenset()                                                           # nadie aprobó nada: sigue vacío
    combos = [get_rule(g, i) for g in GOLD_RULES for i in INCLUSION_RULES]
    assert len(combos) == 12 and all(is_registered_v2(r) and not is_approved(r) and status_of(r) == "PROVISIONAL" for r in combos)
    assert not is_registered_v2(LegacyDominantRule())


def test_legacy_rule_can_never_be_approved_even_if_added_by_hand(monkeypatch):
    from adaptation_swarm.gold.rubric_v2 import is_approved, status_of
    legacy = LegacyDominantRule()
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({legacy.rule_version}))            # alguien intenta «aprobar» la definición histórica
    assert not is_approved(legacy) and status_of(legacy) == "PROVISIONAL"
    with pytest.raises(RuleNotApproved):
        require_approved(legacy)
    with pytest.raises(RuleNotApproved):
        multilabel_report(_hand_cases(), legacy, require_official=True)
    assert multilabel_report(_hand_cases(), legacy).status == "PROVISIONAL"                                # y su informe sigue marcado PROVISIONAL


def test_approving_a_version_string_does_not_approve_an_unregistered_or_altered_rule(monkeypatch):
    import dataclasses
    from adaptation_swarm.gold.rubric_v2 import InclusionRule, MultilabelRule, is_approved
    real = get_rule("gold-v2-cand-A", "incl-ge1")
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(real), "gold-v2-inventada+incl-ge1"}))
    assert is_approved(real)                                                                               # la registrada y aprobada sí
    altered_gold = dataclasses.replace(GOLD_RULES["gold-v2-cand-A"], description="alterada", expected_by_archetype={a: ALL_MODALITIES for a in Archetype})
    altered_incl = InclusionRule("incl-ge1", "threshold", 2, "mismo id, otro parámetro")
    invented = dataclasses.replace(GOLD_RULES["gold-v2-cand-A"], rule_version="gold-v2-inventada")
    fake = type("Fake", (), {"rule_version": real.rule_version, "expected_set": lambda *a, **k: None, "predicted_set": lambda *a, **k: frozenset(), "to_dict": lambda s: {}})()
    for bad in (MultilabelRule(altered_gold, INCLUSION_RULES["incl-ge1"]), MultilabelRule(GOLD_RULES["gold-v2-cand-A"], altered_incl),
                MultilabelRule(invented, INCLUSION_RULES["incl-ge1"]), fake):
        assert not is_approved(bad), bad
        with pytest.raises(RuleNotApproved):
            require_approved(bad)


def test_gold_status_agrees_with_is_approved(monkeypatch):
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({"gold-v2-cand-A"}))                # solo la versión «desnuda» del gold: no aprueba nada
    assert GOLD_RULES["gold-v2-cand-A"].status == "PROVISIONAL" and not rubric_v2.is_approved(get_rule("gold-v2-cand-A", "incl-ge1"))
    assert not rubric_v2.is_approved(get_rule("gold-v2-cand-A", "incl-ge1"))                              # gold+inclusión (P1/P2) SIN agregación ni panel (P3/P4): no aprueba nada
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({"gold-v2-cand-A+incl-ge1"}))
    assert not rubric_v2.is_approved(get_rule("gold-v2-cand-A", "incl-ge1"))
    monkeypatch.setattr(rubric_v2, "APPROVED_RULE_VERSIONS", frozenset({official_version(get_rule("gold-v2-cand-A", "incl-ge1"))}))
    assert GOLD_RULES["gold-v2-cand-A"].status == "OFICIAL" and GOLD_RULES["gold-v2-cand-B-tol0.05"].status == "PROVISIONAL"
    assert rubric_v2.is_approved(get_rule("gold-v2-cand-A", "incl-ge1")) and not rubric_v2.is_approved(get_rule("gold-v2-cand-A", "incl-ge2"))
