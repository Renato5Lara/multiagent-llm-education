"""Tests for app/services/research_statistics.py — ANOVA, pairwise tests,
Cohen's d, power analysis.

Extraído de TestAnalysis en test_experimental_baseline.py (ADR-0017, Fase
1) junto con el módulo que prueba: es el único componente de
app/experiment/ con uso de investigación activo (Iteración 6.2,
2026-08-05), y el resto de test_experimental_baseline.py se retira en
fases posteriores de la misma ADR.
"""

from __future__ import annotations

import pytest

from app.services.research_statistics import (
    cohens_d,
    compute_anova,
    generate_statistical_report,
    pairwise_bonferroni,
    pairwise_holm,
    power_analysis,
    significance_matrix,
)


class TestAnalysis:
    """Verify statistical analysis functions."""

    def test_cohens_d_identical(self):
        d = cohens_d([1.0, 1.0, 1.0], [1.0, 1.0, 1.0])
        assert d == 0.0

    def test_cohens_d_different(self):
        # Data with non-zero variance
        d = cohens_d([0.1, 0.2, 0.3], [0.8, 0.9, 1.0])
        assert abs(d) > 1.0  # large effect

    def test_cohens_d_small_sample(self):
        d = cohens_d([1.0], [2.0])
        assert d == 0.0

    def test_cohens_d_zero_variance(self):
        d = cohens_d([1.0, 1.0], [1.0, 1.0])
        assert d == 0.0

    def test_anova_two_groups(self):
        groups = {"A": [0.5, 0.6, 0.7], "B": [0.8, 0.9, 1.0]}
        result = compute_anova(groups)
        assert result.n_groups == 2
        assert result.f_statistic > 0

    def test_anova_identical_groups(self):
        groups = {"A": [0.5, 0.5, 0.5], "B": [0.5, 0.5, 0.5]}
        result = compute_anova(groups)
        assert result.f_statistic == pytest.approx(0.0, abs=0.01)

    def test_anova_fewer_than_two(self):
        with pytest.raises(ValueError):
            compute_anova({"A": [1.0, 2.0]})

    def test_pairwise_bonferroni(self):
        groups = {
            "A": [0.5, 0.6, 0.7],
            "B": [0.8, 0.9, 1.0],
            "C": [0.4, 0.5, 0.6],
        }
        results = pairwise_bonferroni(groups, alpha=0.10)
        assert len(results) == 3  # 3 choose 2
        for r in results:
            assert r.method == "bonferroni"
            assert r.n_a == 3
            assert r.n_b == 3

    def test_pairwise_holm(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        results = pairwise_holm(groups)
        assert len(results) == 3
        # Holm sorts by p-value; first should have lowest p
        assert results[0].p_value <= results[1].p_value

    def test_pairwise_holm_vs_bonferroni(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        bonf = pairwise_bonferroni(groups)
        holm = pairwise_holm(groups)
        # Holm corrected p-values should be ≤ Bonferroni corrected p-values
        for br, hr in zip(bonf, holm):
            if hr.group_a == br.group_a and hr.group_b == br.group_b:
                assert hr.corrected_p <= br.corrected_p or abs(hr.corrected_p - br.corrected_p) < 0.001

    def test_power_analysis(self):
        n = power_analysis(effect_size=0.5, alpha=0.05, power=0.80)
        assert n >= 3

    def test_power_analysis_large_effect(self):
        n = power_analysis(effect_size=1.0, alpha=0.05, power=0.80)
        small = power_analysis(effect_size=0.2, alpha=0.05, power=0.80)
        assert n < small  # larger effect → smaller sample needed

    def test_power_analysis_zero_effect(self):
        n = power_analysis(effect_size=0.0)
        assert n == 0

    def test_power_analysis_with_correction(self):
        # Use a smaller effect size so the correction has visible impact
        n_one = power_analysis(0.2, n_groups=1)
        n_five = power_analysis(0.2, n_groups=5)
        # More groups → stricter correction → larger sample
        assert n_five >= n_one

    def test_regression_analysis_deterministic(self):
        groups = {"A": [0.6, 0.7], "B": [0.8, 0.9]}
        r1 = pairwise_bonferroni(groups)
        r2 = pairwise_bonferroni(groups)
        assert r1[0].p_value == r2[0].p_value
        assert r1[0].cohens_d == r2[0].cohens_d

    def test_significance_matrix(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9], "C": [0.4, 0.5]}
        results = pairwise_bonferroni(groups)
        matrix = significance_matrix(results)
        assert "A" in matrix
        assert "B" in matrix
        assert "C" in matrix
        assert "ns" in matrix or "*" in matrix

    def test_statistical_report(self):
        groups = {"A": [0.5, 0.6], "B": [0.8, 0.9]}
        report = generate_statistical_report(groups, metric_name="accuracy")
        assert "ANOVA" in report
        assert "Bonferroni" in report
        assert "Holm" in report
        assert "Power" in report
        assert "matrix" in report

    def test_statistical_report_single_group(self):
        # Single group: ANOVA raises, report handles gracefully
        report = generate_statistical_report({"A": [0.5, 0.6]})
        assert "ANOVA skipped" in report or "ANOVA" in report
