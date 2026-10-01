"""`analysis/assumptions.py` y `analysis/hypothesis.py`: reportan sin interpretar, exigen la unidad experimental, eligen la prueba por el diseño y registran siempre H0/H1/α/prueba/estadístico/p/efecto/IC.
Datos SINTÉTICOS de distribución conocida (solo prueban el código; no son resultados del estudio)."""

import numpy as np
import pytest

from adaptation_swarm.analysis import assumptions as A
from adaptation_swarm.analysis import hypothesis as H

REQUIRED = {"design", "unit", "alpha", "alternative", "null_hypothesis", "alternative_hypothesis", "academic_label", "test", "statistic", "p_value", "effect_size", "ci95", "status", "selection_rationale"}


def test_normality_requires_unit_and_never_declares_normal():
    with pytest.raises(ValueError):
        A.normality([1, 2, 3], unit="")
    r = A.normality(np.random.default_rng(0).normal(0, 1, 40), unit="profile_mean")
    assert r["status"] == "ok" and r["unit"] == "profile_mean" and r["interpretation"] == "left_to_statistical_phase"
    assert "is_normal" not in r and isinstance(r["shapiro_rejects_normality"], bool) and r["descriptives"]["n"] == 40
    assert A.normality(np.random.default_rng(1).exponential(1, 80), unit="u")["shapiro_rejects_normality"] is True


def test_normality_edge_cases_and_large_n():
    assert A.normality([1, 2], unit="u")["status"] == "not_testable_n_lt_3"
    assert A.normality([5.0] * 10, unit="u")["status"] == "undefined_constant_sample"
    big = A.normality(np.random.default_rng(2).normal(0, 1, 6000), unit="u")
    assert big["shapiro_n_gt_5000"] is True and "dagostino_p" in big


def test_outliers_are_identified_not_removed():
    x = [1.0, 1.1, 0.9, 1.0, 1.05, 0.95, 50.0]
    o = A.iqr_outliers(x)
    assert o["n_outliers"] == 1 and o["indices"] == [6] and len(x) == 7
    assert A.iqr_outliers([1, 2, 3])["status"] == "not_testable_n_lt_4"


def test_one_sample_selects_t_or_wilcoxon_by_normality_and_records_everything():
    rng = np.random.default_rng(3)
    from scipy import stats
    t = H.one_sample(82 + 6 * stats.norm.ppf((np.arange(30) + 0.5) / 30), 75.0, unit="participant")      # cuantiles normales: determinista y sin azar de muestreo
    assert t["test"] == "student_t_one_sample" and t["significant"] is True and t["effect_size"]["name"] == "cohens_d_one_sample" and len(t["ci95"]) == 2 and REQUIRED <= set(t)
    w = H.one_sample(rng.exponential(1, 60) + 74.5, 75.0, unit="participant")
    assert w["test"] == "wilcoxon_signed_rank" and w["effect_size"]["name"] == "rank_biserial_one_sample" and REQUIRED <= set(w)
    assert t["null_hypothesis"] == "la ubicación de la variable = 75.0" and t["academic_label"] is None
    assert H.one_sample([80.0] * 12, 75.0, unit="u")["status"] == "undefined_constant_sample" and H.one_sample([80.0] * 12, 75.0, unit="u")["p_value"] is None


def test_every_design_returns_the_audit_record():
    rng = np.random.default_rng(4)
    ids = [f"p{i:02d}" for i in range(30)]
    base = rng.normal(10, 2, 30)
    a = dict(zip(ids, base + 2 + rng.normal(0, .3, 30)))
    b = dict(zip(ids, base))
    c = dict(zip(ids, base + 1 + rng.normal(0, .3, 30)))
    recs = [H.run("paired", a=a, b=b, unit="profile_mean"), H.run("independent", a=list(a.values()), b=[v + 5 for v in b.values()], unit="batch"),
            H.run("k_paired", values={"x": a, "y": b, "z": c}, unit="profile_mean"), H.run("k_independent", groups={"x": list(a.values()), "y": list(b.values()), "z": [v + 9 for v in c.values()]}, unit="batch")]
    for r in recs:
        assert REQUIRED <= set(r), r["design"]
        assert r["alpha"] == 0.05 and r["null_hypothesis"] and r["alternative_hypothesis"] and r["selection_rationale"]
    assert recs[0]["significant"] and recs[1]["significant"] and recs[2]["significant"] and recs[3]["significant"]
    assert recs[0]["effect_size"]["name"] == "cohens_dz_paired" and recs[1]["effect_size"]["name"] == "cliffs_delta" and recs[2]["post_hoc"] and recs[3]["post_hoc"]
    rows = [{"f": lv, "profile_id": i, "m": 1.0 + (3 if lv == "B" else 0) + rng.normal(0, .1)} for lv in ("A", "B") for i in ids]
    fa = H.run("factorial", runs=rows, factors=["f"], metric="m", unit="profile_mean")
    assert fa["main_effects"]["f"]["pairwise"]["A__vs__B"]["significant"] is True and fa["assumptions"]["interactions"] == "not_estimated"
    with pytest.raises(ValueError):
        H.run("anova_magica")
