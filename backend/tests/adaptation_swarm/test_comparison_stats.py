"""`analysis/comparison.py`: el protocolo de comparación (pareado por perfil, Shapiro → t/Wilcoxon, Holm, sin falsos positivos con muestras constantes). Datos SINTÉTICOS de distribución conocida
(solo para probar el código; no son resultados del estudio)."""

import numpy as np
import pytest

from adaptation_swarm.analysis import comparison as cmp


def _ids(n):
    return [f"p{i:03d}" for i in range(n)]


def test_profile_means_averages_replicates_per_profile():
    m = cmp.profile_means([("a", 1.0), ("a", 3.0), ("b", 5.0)])
    assert m == {"a": 2.0, "b": 5.0}


def test_holm_is_monotone_and_bounded():
    adj = cmp.holm({"x": 0.01, "y": 0.04, "z": 0.03})
    assert adj["x"] == pytest.approx(0.03) and adj["z"] == pytest.approx(0.06) and adj["y"] == pytest.approx(0.06)
    assert all(0 <= v <= 1 for v in adj.values())


def test_normal_differences_use_paired_t_and_detect_effect():
    rng = np.random.default_rng(1)
    base = rng.normal(100, 10, 60)
    a = {i: float(v - 5 + rng.normal(0, 1)) for i, v in zip(_ids(60), base)}
    b = {i: float(v) for i, v in zip(_ids(60), base)}
    r = cmp.paired_comparison(a, b)
    assert r["status"] == "ok" and r["normal"] and r["test"] == "student_t_paired" and r["significant"] and r["mean_diff"] < 0
    lo, hi = r["diff_ci95_bootstrap"]
    assert lo < r["mean_diff"] < hi and r["effect_size_dz"] < -1


def test_skewed_differences_use_wilcoxon():
    rng = np.random.default_rng(2)
    b = {i: 0.0 for i in _ids(80)}
    a = {i: float(v) for i, v in zip(_ids(80), rng.exponential(1.0, 80))}
    r = cmp.paired_comparison(a, b, alternative="greater")
    assert r["test"] == "wilcoxon_signed_rank" and not r["normal"] and r["significant"]


def test_constant_differences_are_undefined_not_significant():
    a = {i: 2.0 for i in _ids(10)}
    b = {i: 1.0 for i in _ids(10)}
    r = cmp.paired_comparison(a, b)
    assert r["status"] == "undefined_constant_differences" and r["p_value"] is None and r["significant"] is None


def test_no_difference_is_not_significant():
    rng = np.random.default_rng(3)
    base = rng.normal(0, 1, 50)
    a = {i: float(v + rng.normal(0, 0.5)) for i, v in zip(_ids(50), base)}
    b = {i: float(v + rng.normal(0, 0.5)) for i, v in zip(_ids(50), base)}
    assert cmp.paired_comparison(a, b)["significant"] is False


def test_paired_comparison_validates_inputs():
    with pytest.raises(ValueError):
        cmp.paired_comparison({"a": 1.0, "b": 2.0, "c": 3.0}, {"a": 1.0, "b": 2.0, "x": 3.0})
    with pytest.raises(ValueError):
        cmp.paired_comparison({"a": 1.0, "b": 2.0}, {"a": 1.0, "b": 2.0})
    with pytest.raises(ValueError):
        cmp.paired_comparison({i: 1.0 for i in _ids(5)}, {i: 2.0 for i in _ids(5)}, alternative="x")


def test_multi_condition_friedman_and_holm():
    rng = np.random.default_rng(4)
    ids = _ids(40)
    base = rng.normal(10, 2, 40)
    vals = {"c0": {i: float(v) for i, v in zip(ids, base)},
            "c1": {i: float(v + 3 + rng.normal(0, .3)) for i, v in zip(ids, base)},
            "c2": {i: float(v + rng.normal(0, .3)) for i, v in zip(ids, base)}}
    r = cmp.multi_condition_comparison(vals)
    assert r["friedman"]["significant"] and len(r["pairwise"]) == 3
    assert r["pairwise"]["c0__vs__c1"]["significant_holm"] is True and r["pairwise"]["c0__vs__c2"]["significant_holm"] is False
    same = {c: dict(vals["c0"]) for c in ("a", "b", "c")}
    assert cmp.multi_condition_comparison(same)["friedman"]["status"] == "undefined_identical_conditions"


def test_factor_main_effects_marginalize_other_factors():
    rng = np.random.default_rng(5)
    rows = []
    for dispatch in ("batch", "sequential"):
        for bc in (True, False):
            for pid in _ids(30):
                rows.append({"dispatch": dispatch, "broadcast": bc, "profile_id": pid,
                             "t_conv_ms": 50 + (40 if dispatch == "sequential" else 0) + rng.normal(0, 2)})
    r = cmp.factor_main_effects(rows, ["dispatch", "broadcast"], "t_conv_ms")
    assert r["dispatch"]["pairwise"]["batch__vs__sequential"]["significant"] is True
    assert r["broadcast"]["pairwise"]["False__vs__True"]["significant"] is False


def test_spearman_and_cliffs_delta():
    assert cmp.spearman([1, 2, 3, 4], [2, 4, 6, 8])["rho"] == pytest.approx(1.0)
    assert cmp.spearman([1, 1, 1], [1, 2, 3])["status"] == "undefined_constant_variable"
    assert cmp.cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0 and cmp.cliffs_delta([1, 2], [1, 2]) == 0.0


def test_independent_comparison_normal_welch_and_skewed_mannwhitney():
    rng = np.random.default_rng(6)
    r = cmp.independent_comparison(rng.normal(10, 1, 30), rng.normal(13, 1, 30))
    assert r["test"] == "welch_t" and r["significant"] and r["cliffs_delta"] < -0.8
    r2 = cmp.independent_comparison(rng.exponential(1, 40), rng.exponential(1, 40) + 3)
    assert r2["test"] == "mann_whitney_u" and r2["significant"]
    assert cmp.independent_comparison([1, 2], [1, 2, 3])["status"] == "not_testable_n_lt_3"
    assert cmp.independent_comparison([5, 5, 5], [5, 5, 5])["status"] == "undefined_identical_constant_groups"


def test_independent_multi_kruskal_and_holm():
    rng = np.random.default_rng(7)
    g = {"c1": rng.normal(40, 2, 10), "c10": rng.normal(41, 2, 10), "c100": rng.normal(60, 2, 10)}
    r = cmp.independent_multi_comparison(g)
    assert r["kruskal"]["significant"] and r["pairwise"]["c1__vs__c100"]["significant_holm"] is True
    assert r["pairwise"]["c1__vs__c10"]["significant_holm"] is False
