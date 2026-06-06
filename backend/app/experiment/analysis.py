"""
Statistical Analysis — hypothesis testing for the thesis baseline.
**Zero external dependencies** (stdlib-only: math + statistics).

Provides:
    - One-way ANOVA approximation across all conditions
    - Pairwise t-tests with Bonferroni / Holm-Bonferroni correction
    - Cohen's d effect size
    - Power analysis (required N per group, normal approximation)
    - Significance matrix (formatted table)
    - Confidence calibration statistics

All functions work on dict[str, list[float]] where keys are condition names.

Note on scipy:
    This module implements approximate versions of t-test, ANOVA, and
    power analysis using only the standard library.  For publication-grade
    p-values, install scipy and use the functions in `analysis_scipy.py`.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Any


# ── Helpers ──────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _var(values: list[float], ddof: int = 1) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return statistics.variance(values) if ddof == 1 else statistics.pvariance(values)
    except statistics.StatisticsError:
        return 0.0


def _normal_cdf(x: float) -> float:
    """Standard normal CDF using Abramowitz & Stegun approximation.

    Accuracy: ±7.5e-8  (close to double precision).
    """
    if x < 0:
        return 1 - _normal_cdf(-x)
    # Constants
    p = 0.2316419
    b1 = 0.319381530
    b2 = -0.356563782
    b3 = 1.781477937
    b4 = -1.821255978
    b5 = 1.330274429
    t = 1.0 / (1.0 + p * x)
    phi = math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)
    return 1.0 - phi * (b1 * t + b2 * t ** 2 + b3 * t ** 3 + b4 * t ** 4 + b5 * t ** 5)


def _normal_ppf(p: float) -> float:
    """Standard normal quantile function (inverse CDF).

    Uses the Hastings rational approximation (Moro 1995).
    Max absolute error < 4.5e-4 — more than adequate for power analysis.
    """
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")

    # Hastings coefficients
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308

    # For p < 0.5, use symmetry
    if p < 0.5:
        return -_normal_ppf(1.0 - p)

    # Upper tail approximation
    t = math.sqrt(-2.0 * math.log(1.0 - p))
    z = t - (c0 + c1 * t + c2 * t ** 2) / (1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return z


def _t_test_ind(a: list[float], b: list[float]) -> tuple[float, float]:
    """Approximate independent two-tailed t-test (Welch's).

    Returns (t_statistic, p_value).
    p_value is approximate using normal CDF (conservative for small n).
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0, 1.0
    m1, m2 = _mean(a), _mean(b)
    v1, v2 = _var(a), _var(b)
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return 0.0, 1.0
    t = (m1 - m2) / se

    # Welch-Satterthwaite df
    num = (v1 / n1 + v2 / n2) ** 2
    den = (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    df = num / den if den > 0 else 1.0

    # Two-tailed p-value using t-distribution approximation
    # For large df, t ≈ normal. For small df, we use a conservative
    # approximation via the normal CDF (slightly anti-conservative).
    p = 2.0 * (1.0 - _normal_cdf(abs(t)))
    return t, min(p, 1.0)


def _f_oneway(*groups: list[float]) -> tuple[float, float]:
    """Approximate one-way ANOVA F-test.

    Returns (F_statistic, p_value).
    """
    if len(groups) < 2:
        return 0.0, 1.0

    k = len(groups)
    all_data = [x for g in groups for x in g]
    grand_mean = _mean(all_data)
    n_total = len(all_data)

    ss_between = 0.0
    ss_within = 0.0
    for g in groups:
        gm = _mean(g)
        ss_between += len(g) * (gm - grand_mean) ** 2
        ss_within += sum((x - gm) ** 2 for x in g)

    df_between = k - 1
    df_within = n_total - k

    ms_between = ss_between / df_between if df_between > 0 else 0.0
    ms_within = ss_within / df_within if df_within > 0 else 1.0

    if ms_within == 0:
        return 0.0, 1.0
    f = ms_between / ms_within

    # Approximate p-value using F-distribution via normal approximation
    # χ² approximation: for large df, use chi2 CDF approximation
    p = 1.0 - _normal_cdf((f - 1) * math.sqrt(df_within / (2 * df_between)))
    return f, min(p, 1.0)


# ── Data structures ──────────────────────────────────────────────


@dataclass
class PairwiseTest:
    """Result of a single pairwise comparison."""

    group_a: str
    group_b: str
    statistic: float
    p_value: float
    corrected_p: float
    cohens_d: float
    significant: bool
    method: str
    n_a: int
    n_b: int

    def summary(self) -> str:
        if self.p_value < 0.001:
            sig = "***"
        elif self.p_value < 0.01:
            sig = "**"
        elif self.p_value < 0.05:
            sig = "*"
        else:
            sig = "ns"
        return (
            f"{self.group_a:22s} vs {self.group_b:22s}  "
            f"t={self.statistic:+.3f}  p={self.p_value:.4f}  "
            f"p_corr={self.corrected_p:.4f}  d={self.cohens_d:.3f}  {sig}"
        )


@dataclass
class ANOVA:
    """Result of one-way ANOVA."""

    f_statistic: float
    p_value: float
    df_between: int
    df_within: int
    groups: list[str]
    n_groups: int
    significant: bool

    def summary(self) -> str:
        if self.p_value < 0.001:
            sig = "***"
        elif self.p_value < 0.01:
            sig = "**"
        elif self.p_value < 0.05:
            sig = "*"
        else:
            sig = "ns"
        return (
            f"ANOVA: F({self.df_between},{self.df_within}) = {self.f_statistic:.4f}, "
            f"p = {self.p_value:.4f}  {sig}"
        )


# ── Cohen's d ────────────────────────────────────────────────────


def cohens_d(
    a: list[float],
    b: list[float],
) -> float:
    """Cohen's d effect size (pooled standard deviation).

    Interpretation:
        d ≈ 0.2  → small
        d ≈ 0.5  → medium
        d ≈ 0.8  → large
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return 0.0
    s1 = _var(a)
    s2 = _var(b)
    pooled = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled == 0:
        return 0.0
    return (_mean(a) - _mean(b)) / pooled


# ── One-way ANOVA ────────────────────────────────────────────────


def compute_anova(
    groups: dict[str, list[float]],
) -> ANOVA:
    """One-way ANOVA across all groups.

    Returns ANOVA result including F-statistic, p-value, and significance.
    Null hypothesis: all group means are equal.

    Raises:
        ValueError: if fewer than 2 groups.
    """
    if len(groups) < 2:
        raise ValueError(f"Need ≥2 groups, got {len(groups)}")
    names = list(groups.keys())
    data = [groups[n] for n in names]
    f_stat, p_val = _f_oneway(*data)
    n_groups = len(names)
    n_total = sum(len(d) for d in data)
    return ANOVA(
        f_statistic=float(f_stat),
        p_value=float(p_val),
        df_between=n_groups - 1,
        df_within=n_total - n_groups,
        groups=names,
        n_groups=n_groups,
        significant=bool(p_val < 0.05),
    )


# ── Pairwise tests with correction ──────────────────────────────


def pairwise_t_tests(
    groups: dict[str, list[float]],
    *,
    correction: str = "bonferroni",
    alpha: float = 0.05,
) -> list[PairwiseTest]:
    """Run pairwise independent t-tests with multiple comparison correction.

    Args:
        groups: Dict mapping condition name → list of metric values.
        correction: "bonferroni" or "holm".
        alpha: Family-wise significance level.

    Returns:
        List of PairwiseTest results, sorted by p-value ascending.
    """
    names = list(groups.keys())
    results: list[PairwiseTest] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a_name, b_name = names[i], names[j]
            a_data, b_data = groups[a_name], groups[b_name]
            if len(a_data) < 2 or len(b_data) < 2:
                continue

            t_stat, p_val = _t_test_ind(a_data, b_data)
            d = cohens_d(a_data, b_data)

            results.append(PairwiseTest(
                group_a=a_name,
                group_b=b_name,
                statistic=float(t_stat),
                p_value=float(p_val),
                corrected_p=float(p_val),
                cohens_d=d,
                significant=False,
                method=correction,
                n_a=len(a_data),
                n_b=len(b_data),
            ))

    # Apply correction
    m = len(results)
    if correction == "bonferroni":
        for r in results:
            r.corrected_p = min(r.p_value * m, 1.0)
            r.significant = r.corrected_p < alpha
    elif correction == "holm":
        results.sort(key=lambda r: r.p_value)
        for k, r in enumerate(results):
            r.corrected_p = min(r.p_value * (m - k), 1.0)
            r.significant = r.corrected_p < alpha
    else:
        raise ValueError(f"Unknown correction: {correction}")

    return results


def pairwise_bonferroni(
    groups: dict[str, list[float]],
    alpha: float = 0.05,
) -> list[PairwiseTest]:
    """Pairwise t-tests with Bonferroni correction."""
    return pairwise_t_tests(groups, correction="bonferroni", alpha=alpha)


def pairwise_holm(
    groups: dict[str, list[float]],
    alpha: float = 0.05,
) -> list[PairwiseTest]:
    """Pairwise t-tests with Holm-Bonferroni correction (more power)."""
    return pairwise_t_tests(groups, correction="holm", alpha=alpha)


# ── Power analysis ───────────────────────────────────────────────


def power_analysis(
    effect_size: float,
    alpha: float = 0.05,
    power: float = 0.80,
    n_groups: int = 2,
) -> int:
    """Estimate required sample size per group using two-tailed t-test.

    Uses the normal approximation:
        n ≈ 2 * ((z_alpha/2 + z_beta) / d)²

    Args:
        effect_size: Cohen's d.
        alpha: Significance level.
        power: Desired statistical power.
        n_groups: Number of groups (for Bonferroni correction).

    Returns:
        Required sample size PER GROUP.

    Reference:
        Cohen, J. (1988). Statistical Power Analysis for the Behavioral Sciences.
    """
    if effect_size <= 0:
        return 0

    corrected_alpha = alpha / n_groups if n_groups > 1 else alpha
    z_alpha = _normal_ppf(1 - corrected_alpha / 2)
    z_beta = _normal_ppf(power)

    n = int(math.ceil(2 * ((z_alpha + z_beta) / effect_size) ** 2))
    return max(n, 3)


# ── Significance matrix ─────────────────────────────────────────


def significance_matrix(
    results: list[PairwiseTest],
) -> str:
    """Format pairwise test results as a readable matrix."""
    names = sorted(set(
        [r.group_a for r in results] + [r.group_b for r in results]
    ))
    lines = ["Pairwise comparison matrix (corrected p-values):", ""]
    header = f"{'':22s}" + "".join(f"{name:22s}" for name in names)
    lines.append(header)
    lines.append("-" * len(header))

    for i, name_a in enumerate(names):
        row = f"{name_a:22s}"
        for j, name_b in enumerate(names):
            if i == j:
                row += f"{'—':22s}"
            elif i > j:
                row += f"{'':22s}"
            else:
                match = next(
                    (r for r in results
                     if (r.group_a == name_a and r.group_b == name_b)
                     or (r.group_a == name_b and r.group_b == name_a)),
                    None,
                )
                if match:
                    if match.corrected_p < 0.001:
                        sig = "***"
                    elif match.corrected_p < 0.01:
                        sig = "**"
                    elif match.corrected_p < 0.05:
                        sig = "*"
                    else:
                        sig = "ns"
                    val = f"{match.corrected_p:.4f} {sig}"
                    row += f"{val:22s}"
                else:
                    row += f"{'?':22s}"
        lines.append(row)

    lines.append("")
    lines.append("  * p<0.05  ** p<0.01  *** p<0.001  ns = not significant")
    return "\n".join(lines)


# ── Full report ──────────────────────────────────────────────────


def generate_statistical_report(
    groups: dict[str, list[float]],
    metric_name: str = "accuracy",
    alpha: float = 0.05,
) -> str:
    """Generate a complete statistical report for a given metric.

    Includes:
        - Descriptive statistics per group
        - One-way ANOVA
        - Pairwise comparisons with Bonferroni and Holm correction
        - Cohen's d effect sizes
        - Power analysis
        - Significance matrix
    """
    lines = [
        f"Statistical Report: {metric_name}",
        "=" * 60,
        "",
    ]

    # Descriptive
    lines.append("Descriptive Statistics:")
    lines.append("-" * 40)
    for name in sorted(groups.keys()):
        data = groups[name]
        if not data:
            continue
        m = _mean(data)
        s = _var(data) ** 0.5 if len(data) > 1 else 0.0
        lines.append(
            f"  {name:22s}  n={len(data):>4}  "
            f"M={m:.4f}  SD={s:.4f}"
        )
    lines.append("")

    # ANOVA
    try:
        anova = compute_anova(groups)
        lines.append(anova.summary())
        lines.append("")
    except (ValueError, Exception) as e:
        lines.append(f"ANOVA skipped: {e}")
        lines.append("")

    # Pairwise Bonferroni
    lines.append("Pairwise comparisons (Bonferroni correction):")
    lines.append("-" * 60)
    bonf = pairwise_bonferroni(groups, alpha=alpha)
    for r in bonf:
        lines.append(f"  {r.summary()}")
    lines.append("")

    # Pairwise Holm
    lines.append("Pairwise comparisons (Holm-Bonferroni correction):")
    lines.append("-" * 60)
    holm = pairwise_holm(groups, alpha=alpha)
    for r in holm:
        lines.append(f"  {r.summary()}")
    lines.append("")

    # Power analysis
    lines.append(f"Power Analysis (α={alpha:.2f}, power=0.80):")
    lines.append("-" * 40)
    for r in bonf:
        if r.p_value < 0.05:
            n_req = power_analysis(abs(r.cohens_d), alpha=alpha, n_groups=len(groups))
            lines.append(
                f"  {r.group_a} vs {r.group_b}: d={abs(r.cohens_d):.3f} → "
                f"need n={n_req} per group"
            )
    lines.append("")

    # Significance matrix
    lines.append(significance_matrix(bonf))

    return "\n".join(lines)
