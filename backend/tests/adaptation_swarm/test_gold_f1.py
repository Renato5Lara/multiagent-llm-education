"""Gold preregistrado (independiente de W), regla de desempate, matriz 4×4 y F1 (DECISION-CLOSURE §7)."""

import ast
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from adaptation_swarm.gold import rubric
from adaptation_swarm.gold.dataset import gold_for
from adaptation_swarm.gold.f1 import bootstrap_ci, confusion_matrix, f1_report, report_from_matrix
from adaptation_swarm.gold.rubric import GOLD_TABLE, dominant_modality, expected_dominant, predicted_dominant
from adaptation_swarm.profiles.models import Archetype, Difficulty, ModalityWeights, ProfileRequest


def test_gold_table_has_20_cells_with_declared_rule():
    assert len(GOLD_TABLE) == 20
    for d in Difficulty:
        assert expected_dominant(Archetype.VISUAL_DOMINANT, d) == "diagram"
        assert expected_dominant(Archetype.LOGICAL_SYNTACTIC, d) == "code"
        assert expected_dominant(Archetype.EXPLANATORY_CONCEPTUAL, d) == "text"
        assert expected_dominant(Archetype.BALANCED_MULTIMODAL, d) == "code"   # empate ⇒ código > diagrama > texto > audio


def test_tie_rule_priority_and_tau():
    assert dominant_modality([2, 2, 0, 0]) == "code"
    assert dominant_modality([0, 2, 2, 2]) == "diagram"
    assert dominant_modality([0, 0, 2, 2]) == "text"
    assert dominant_modality([0, 0, 0, 2]) == "audio"
    assert dominant_modality([1.00, 1.04, 0.0, 0.0]) == "code"        # diferencia 0.04 < τ=0.05 ⇒ empate ⇒ prioridad
    assert dominant_modality([1.00, 1.06, 0.0, 0.0]) == "diagram"     # 0.06 ≥ τ ⇒ gana el máximo
    assert predicted_dominant((1, 2, 1, 0)) == "diagram"
    assert predicted_dominant((1, 1, 1, 1)) == "code"


def test_gold_is_independent_of_W():
    base = dict(profile_id="p", nivel=0.5, tasa_error_previa=0.2, concept_id="c",
                archetype=Archetype.VISUAL_DOMINANT, difficulty=Difficulty.REPETITIVE)
    g1 = gold_for(ProfileRequest(estilo=ModalityWeights(w_v=0.1, w_a=0.1, w_t=0.1, w_c=0.7), **base))
    g2 = gold_for(ProfileRequest(estilo=ModalityWeights(w_v=0.7, w_a=0.1, w_t=0.1, w_c=0.1), **base))
    assert g1.expected_dominant == g2.expected_dominant == "diagram"


def test_rubric_module_does_not_import_fitness_or_w_rules():
    tree = ast.parse(inspect.getsource(rubric))
    imported = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not any("fitness" in m or "w_mapping" in m or "agents" in m for m in imported)


def test_confusion_matrix_and_scores_by_hand():
    pairs = [("code", "code")] * 5 + [("code", "diagram")] * 1 + [("diagram", "diagram")] * 4 \
        + [("diagram", "code")] * 2 + [("text", "text")] * 3 + [("text", "audio")] * 1
    cm = confusion_matrix(pairs)
    assert cm.tolist() == [[5, 1, 0, 0], [2, 4, 0, 0], [0, 0, 3, 1], [0, 0, 0, 0]]
    rep = report_from_matrix(cm)
    assert rep.per_class["code"].precision == pytest.approx(5 / 7) and rep.per_class["code"].recall == pytest.approx(5 / 6)
    assert rep.per_class["diagram"].precision == pytest.approx(4 / 5) and rep.per_class["diagram"].recall == pytest.approx(4 / 6)
    assert rep.per_class["text"].precision == pytest.approx(1.0) and rep.per_class["text"].recall == pytest.approx(3 / 4)
    assert rep.per_class["audio"].precision == pytest.approx(0.0) and rep.per_class["audio"].recall is None
    f1c = 2 * (5 / 7) * (5 / 6) / ((5 / 7) + (5 / 6))
    f1d = 2 * 0.8 * (4 / 6) / (0.8 + 4 / 6)
    f1t = 2 * 1.0 * 0.75 / 1.75
    assert rep.per_class["code"].f1 == pytest.approx(f1c)
    assert rep.macro_f1_all4 == pytest.approx((f1c + f1d + f1t + 0.0) / 4)
    assert rep.accuracy == pytest.approx(12 / 16)


def test_f1_perfect_and_worst_and_undefined_class_reporting():
    perfect = f1_report([("code", "code"), ("diagram", "diagram"), ("text", "text")])
    assert perfect.f1_adapt == 1.0 and perfect.macro_f1_defined == 1.0
    assert perfect.per_class["audio"].f1 is None and perfect.macro_f1_all4 == pytest.approx(0.75)   # 0/0 ≠ 1 artificial
    wrong = f1_report([("code", "diagram"), ("diagram", "text"), ("text", "code")])
    assert wrong.f1_adapt == 0.0
    mixed = f1_report([("code", "code"), ("code", "diagram"), ("diagram", "diagram"), ("text", "text")])
    assert 0.0 < mixed.f1_adapt < 1.0                                  # F1 no es una constante


def test_f1_never_constant_over_random_pairings():
    rng = np.random.default_rng(1)
    classes = ["code", "diagram", "text", "audio"]
    vals = {round(f1_report([(classes[rng.integers(0, 3)], classes[rng.integers(0, 4)]) for _ in range(40)]).f1_adapt, 4) for _ in range(30)}
    assert len(vals) > 10


def test_bootstrap_ci_reproducible_and_brackets_point_estimate():
    pairs = [("code", "code")] * 40 + [("diagram", "diagram")] * 30 + [("diagram", "code")] * 10 + [("text", "text")] * 20
    point = f1_report(pairs).f1_adapt
    lo1, hi1 = bootstrap_ci(pairs, np.random.default_rng(3), n_boot=500)
    lo2, hi2 = bootstrap_ci(pairs, np.random.default_rng(3), n_boot=500)
    assert (lo1, hi1) == (lo2, hi2) and lo1 <= point <= hi1 and lo1 < hi1


# ── casos límite y evaluación contra el gold versionado ──────────────────────────────────────────────────────────────
GOLD_V1 = Path(__file__).resolve().parents[3] / "datasets" / "synthetic_profiles" / "gold-v1.jsonl"


def _gold_v1() -> list[dict]:
    return [json.loads(line) for line in GOLD_V1.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_class_without_any_case_has_undefined_scores_not_zero():
    """TP = FP = FN = 0 ⇒ Precision, Recall y F1 indefinidas (None), no 0 ni 1; no entran en el macro-F1 principal."""
    rep = f1_report([("code", "code"), ("text", "text")])
    for c in ("diagram", "audio"):
        s = rep.per_class[c]
        assert (s.precision, s.recall, s.f1, s.support) == (None, None, None, 0)
    assert rep.f1_adapt == 1.0 and rep.macro_f1_all4 == pytest.approx(0.5)


def test_zero_precision_and_zero_recall_are_zero_and_the_other_side_undefined_is_reported():
    only_fp = f1_report([("code", "audio")]).per_class["audio"]                         # TP=0, FP=1, FN=0
    assert (only_fp.precision, only_fp.recall, only_fp.f1) == (0.0, None, 0.0)
    only_fn = f1_report([("code", "audio")]).per_class["code"]                          # TP=0, FP=0, FN=1
    assert (only_fn.precision, only_fn.recall, only_fn.f1) == (None, 0.0, 0.0)
    both = f1_report([("code", "diagram"), ("diagram", "code")]).per_class["code"]     # TP=0, FP=1, FN=1 ⇒ P+R=0
    assert (both.precision, both.recall, both.f1) == (0.0, 0.0, 0.0)


def test_empty_cases_raise_instead_of_returning_a_misleading_zero():
    with pytest.raises(ValueError, match="sin casos"):
        f1_report([])
    with pytest.raises(ValueError, match="sin casos"):
        report_from_matrix(np.zeros((4, 4), dtype=int))
    with pytest.raises(ValueError, match="sin pares"):
        bootstrap_ci([], np.random.default_rng(0))


def test_f1_against_versioned_gold_v1_keeps_the_case_unit_and_the_declared_supports():
    gold = _gold_v1()
    assert len(gold) == 100 and len({g["profile_id"] for g in gold}) == 100          # unidad de análisis: 1 caso = 1 (perfil, concepto)
    assert all(g["concept_id"] for g in gold) and {g["rule_version"] for g in gold} == {"gold-v1"}
    perfect = f1_report([(g["expected_dominant"], g["expected_dominant"]) for g in gold])
    assert perfect.f1_adapt == 1.0 and perfect.accuracy == 1.0
    assert {c: s.support for c, s in perfect.per_class.items()} == {"code": 50, "diagram": 25, "text": 25, "audio": 0}
    assert perfect.per_class["audio"].f1 is None and perfect.macro_f1_all4 == pytest.approx(0.75)


def test_f1_against_gold_v1_is_reproducible_with_the_same_seed_and_sensitive_to_it():
    gold = _gold_v1()

    def evaluate(seed: int):
        rng = np.random.default_rng(seed)
        classes = ["code", "diagram", "text", "audio"]
        pairs = [(g["expected_dominant"], classes[rng.integers(0, 4)] if rng.random() < 0.3 else g["expected_dominant"]) for g in gold]
        return f1_report(pairs), bootstrap_ci(pairs, np.random.default_rng(seed), n_boot=300)

    (a, ci_a), (b, ci_b) = evaluate(11), evaluate(11)
    assert a.to_dict() == b.to_dict() and ci_a == ci_b
    assert 0.0 < a.f1_adapt < 1.0 and ci_a[0] <= a.f1_adapt <= ci_a[1]
    assert evaluate(12)[0].to_dict() != a.to_dict()
