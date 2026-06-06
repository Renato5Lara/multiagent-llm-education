"""
Benchmark Statistics — Pruebas estadísticas académicas completas.

Implementa:
  - Mann-Whitney U (independiente)
  - McNemar (pareado, dicotómico)
  - Cohen's d (tamaño del efecto)
  - Rank-Biserial (correlación)
  - Intervalos de confianza (95%)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HypothesisTest:
    """Resultado de una prueba de hipótesis."""

    test_name: str
    statistic: float
    p_value: float
    significant: bool
    alpha: float = 0.05
    effect_size: float = 0.0
    effect_size_label: str = ""
    n1: int = 0
    n2: int = 0
    ci_lower: float = 0.0
    ci_upper: float = 0.0

    def summary(self) -> str:
        sig = "✅" if self.significant else "❌"
        return (
            f"{sig} {self.test_name}: {self.statistic:.4f} "
            f"(p={self.p_value:.4f}, d={self.effect_size:.3f})"
        )


@dataclass
class StatisticalReport:
    """Reporte estadístico completo del benchmark."""

    condition_a: str
    condition_b: str
    tests: list[HypothesisTest] = field(default_factory=list)
    metric_summaries: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comparison": f"{self.condition_a} vs {self.condition_b}",
            "tests": [
                {
                    "test": t.test_name,
                    "statistic": round(t.statistic, 4),
                    "p_value": round(t.p_value, 4),
                    "significant": t.significant,
                    "effect_size": round(t.effect_size, 4),
                    "effect_size_label": t.effect_size_label,
                    "ci_95": [round(t.ci_lower, 4), round(t.ci_upper, 4)],
                }
                for t in self.tests
            ],
            "metric_summaries": self.metric_summaries,
        }


# ── Helper functions (stdlib-only, no scipy) ────────────────────


def _normal_cdf(x: float) -> float:
    """CDF normal estándar (Abramowitz & Stegun approximation)."""
    if x < 0:
        return 1.0 - _normal_cdf(-x)
    b0, b1, b2, b3, b4, b5 = (
        0.2316419, 0.319381530, -0.356563782,
        1.781477937, -1.821255978, 1.330274429,
    )
    t = 1.0 / (1.0 + b0 * x)
    poly = b1 + t * (b2 + t * (b3 + t * (b4 + t * b5)))
    return 1.0 - 0.398942280 * math.exp(-0.5 * x * x) * poly


def _normal_ppf(p: float) -> float:
    """Percentil normal estándar (Moro's rational approximation)."""
    if p < 0.5:
        return -_normal_ppf(1.0 - p)
    a0, a1, a2 = 2.50662823884, -18.61500062529, 41.39119773534
    b0, b1, b2, b3 = -8.47351093090, 23.08336743743, -21.06224101826, 3.13082909833
    c0, c1, c2, c3, c4, c5, c6, c7 = (
        0.3374754822726147, 0.9761690190917186,
        0.1607979714918209, 0.0276438810333863,
        0.0038405729373609, 0.0003951896511919,
        0.0000321767881768, 0.0000002888167364,
    )
    q = p - 0.5
    if abs(q) <= 0.42:
        r = q * q
        y = q * (((a2 * r + a1) * r + a0) / (((b3 * r + b2) * r + b1) * r + b0 * r + 1.0))
    else:
        r = p if q > 0 else 1.0 - p
        r = math.sqrt(-math.log(r))
        y = (((((c7 * r + c6) * r + c5) * r + c4) * r + c3) * r + c2) * r + c1
        y = y * r + c0
        if q < 0:
            y = -y
    return y


def _t_cdf(t: float, df: int) -> float:
    """CDF t de Student usando relación con beta incompleta regularizada."""
    x = df / (df + t * t)
    if t >= 0:
        return 1.0 - 0.5 * _betai(df / 2.0, 0.5, x)
    return 0.5 * _betai(df / 2.0, 0.5, x)


def _betai(a: float, b: float, x: float) -> float:
    """Beta incompleta regularizada (método de continued fractions)."""
    if x < 0.0 or x > 1.0:
        return 0.0
    if x == 0.0 or x == 1.0:
        return x
    lbeta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1.0 - x) * b - lbeta) / a
    f, c, d = 1.0, 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / d if abs(d) > 1e-30 else 1.0 / 1e-30
    f *= d
    for m in range(1, 201):
        nu = m * (b - m) * x / ((a + 2.0 * m - 1.0) * (a + 2.0 * m))
        d = 1.0 + nu * d
        d = d if abs(d) > 1e-30 else 1e-30
        c = 1.0 + nu / c
        c = c if abs(c) > 1e-30 else 1e-30
        d = 1.0 / d
        f *= d * c
        nu = -(a + m) * (a + b + m) * x / ((a + 2.0 * m) * (a + 2.0 * m + 1.0))
        d = 1.0 + nu * d
        d = d if abs(d) > 1e-30 else 1e-30
        c = 1.0 + nu / c
        c = c if abs(c) > 1e-30 else 1e-30
        d = 1.0 / d
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-10:
            break
    return front * f


def _t_ppf(p: float, df: int) -> float:
    """Percentil t de Student (búsqueda binaria sobre CDF)."""
    if p <= 0.0:
        return -float("inf")
    if p >= 1.0:
        return float("inf")
    lo, hi = -8.0, 8.0
    for _ in range(50):
        mid = (lo + hi) / 2.0
        cdf_mid = _t_cdf(mid, df)
        if abs(cdf_mid - p) < 1e-10:
            return mid
        if cdf_mid < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


# ── Statistical Tests ──────────────────────────────────────────


def _rank_values(a: list[float]) -> list[float]:
    """Asigna ranks (con manejo de empates)."""
    n = len(a)
    indexed = sorted(enumerate(a), key=lambda x: x[1])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and abs(indexed[j][1] - indexed[i][1]) < 1e-12:
            j += 1
        rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def mann_whitney_u(
    a: list[float],
    b: list[float],
    alpha: float = 0.05,
) -> HypothesisTest:
    """Mann-Whitney U test para dos muestras independientes."""
    n1, n2 = len(a), len(b)
    combined = a + b
    ranks = _rank_values(combined)
    r1 = sum(ranks[:n1])
    u1 = r1 - (n1 * (n1 + 1)) / 2.0
    u2 = n1 * n2 - u1
    u = min(u1, u2)
    mu = n1 * n2 / 2.0
    n = n1 + n2
    tie_correction = sum(
        t ** 3 - t
        for t in [
            list(combined).count(v)
            for v in set(combined)
            if list(combined).count(v) > 1
        ]
    )
    sigma = math.sqrt(
        (n1 * n2 / (n * (n - 1)))
        * ((n ** 3 - n - tie_correction) / 12.0)
    )
    if sigma == 0:
        z = 0.0
    else:
        z = (u - mu) / sigma
    p = 2.0 * (1.0 - _normal_cdf(abs(z)))
    r = u / (n1 * n2)
    return HypothesisTest(
        test_name="Mann-Whitney U",
        statistic=u,
        p_value=min(p, 1.0),
        significant=bool(p < alpha),
        alpha=alpha,
        effect_size=r,
        effect_size_label=_rank_biserial_label(r),
        n1=n1,
        n2=n2,
        ci_lower=mu - 1.96 * sigma,
        ci_upper=mu + 1.96 * sigma,
    )


def _rank_biserial_label(r: float) -> str:
    abs_r = abs(r)
    if abs_r >= 0.5:
        return "large"
    if abs_r >= 0.3:
        return "medium"
    if abs_r >= 0.1:
        return "small"
    return "negligible"


def mcnemar_test(
    a_correct: list[bool],
    b_correct: list[bool],
    alpha: float = 0.05,
) -> HypothesisTest:
    """McNemar test para proporciones pareadas (dicotómicas)."""
    n = len(a_correct)
    b = sum(1 for i in range(n) if a_correct[i] and not b_correct[i])
    c = sum(1 for i in range(n) if not a_correct[i] and b_correct[i])
    total_discordant = b + c
    if total_discordant == 0:
        chi2 = 0.0
        p = 1.0
    else:
        chi2 = (abs(b - c) - 1) ** 2 / total_discordant
        p = 1.0 - _chi2_cdf(chi2, 1)
    w = (b - c) / math.sqrt(b + c) if (b + c) > 0 else 0.0
    return HypothesisTest(
        test_name="McNemar",
        statistic=chi2,
        p_value=min(p, 1.0),
        significant=bool(p < alpha),
        alpha=alpha,
        effect_size=abs(w) / n / 2 if n > 0 else 0.0,
        effect_size_label="large" if abs(w) / max(n, 1) > 0.5 else "medium" if abs(w) / max(n, 1) > 0.3 else "small",
        n1=n,
        n2=n,
        ci_lower=(b - c) / n - 1.96 * math.sqrt((b + c)) / n,
        ci_upper=(b - c) / n + 1.96 * math.sqrt((b + c)) / n,
    )


def _chi2_cdf(x: float, df: int) -> float:
    """CDF chi-cuadrado (usando distribución gamma incompleta regularizada)."""
    if x <= 0:
        return 0.0
    return _gammainc(df / 2.0, x / 2.0)


def _gammainc(a: float, x: float) -> float:
    """Gamma incompleta regularizada P(a,x) usando series."""
    if x < 0 or a <= 0:
        return 0.0
    if x == 0:
        return 0.0
    series = 1.0 / a
    term = 1.0 / a
    for n in range(1, 200):
        term *= x / (a + n)
        series += term
        if abs(term) < 1e-14:
            break
    return series * math.exp(-x + a * math.log(x) - math.lgamma(a))


def cohens_d(
    a: list[float],
    b: list[float],
    alpha: float = 0.05,
) -> HypothesisTest:
    """Cohen's d: tamaño del efecto entre dos grupos independientes."""
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return HypothesisTest(
            test_name="Cohen's d", statistic=0.0, p_value=1.0,
            significant=False, alpha=alpha, effect_size=0.0,
            effect_size_label="undefined", n1=n1, n2=n2,
        )
    m1, m2 = sum(a) / n1, sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    pooled = math.sqrt(((n1 - 1) * v1 + (n2 - 1) * v2) / (n1 + n2 - 2))
    if pooled == 0:
        d = 0.0
    else:
        d = (m1 - m2) / pooled
    se = math.sqrt((n1 + n2) / (n1 * n2) + d ** 2 / (2 * (n1 + n2)))
    t_stat = d / se if se > 0 else 0.0
    df = n1 + n2 - 2
    p = 2.0 * (1.0 - _t_cdf(abs(t_stat), df))
    ci_lower = d - 1.96 * se
    ci_upper = d + 1.96 * se
    label = "large" if abs(d) >= 0.8 else "medium" if abs(d) >= 0.5 else "small" if abs(d) >= 0.2 else "negligible"
    return HypothesisTest(
        test_name="Cohen's d",
        statistic=d,
        p_value=min(p, 1.0),
        significant=bool(p < alpha),
        alpha=alpha,
        effect_size=d,
        effect_size_label=label,
        n1=n1,
        n2=n2,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
    )


def confidence_interval(
    values: list[float],
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """Intervalo de confianza para la media."""
    n = len(values)
    if n < 2:
        return (0.0, 0.0, 0.0)
    m = sum(values) / n
    v = sum((x - m) ** 2 for x in values) / (n - 1)
    se = math.sqrt(v / n)
    alpha = 1.0 - confidence
    t_val = _t_ppf(1.0 - alpha / 2.0, n - 1)
    return (m, m - t_val * se, m + t_val * se)


class StatisticalTestSuite:
    """Suite completa de tests estadísticos para comparar dos condiciones."""

    def __init__(self, alpha: float = 0.05):
        self.alpha = alpha

    def compare_conditions(
        self,
        results_a: list,
        results_b: list,
        label_a: str,
        label_b: str,
    ) -> StatisticalReport:
        """Compara dos condiciones en todas las métricas."""
        metrics_keys = [
            "pass_at_1", "correction_rate", "grounding_score",
            "misconception_coverage", "bloom_alignment", "adaptation_impact",
            "hallucination_reduction", "sandbox_validation_success",
            "execution_success", "consensus_confidence",
            "retrieval_confidence", "prompt_grounding_score",
            "personalization_impact",
        ]
        tests: list[HypothesisTest] = []
        summaries: dict[str, dict[str, float]] = {}

        for key in metrics_keys:
            vals_a = [getattr(r.metrics, key, 0.0) for r in results_a]
            vals_b = [getattr(r.metrics, key, 0.0) for r in results_b]

            mw = mann_whitney_u(vals_a, vals_b, self.alpha)
            cd = cohens_d(vals_a, vals_b, self.alpha)
            ci_a = confidence_interval(vals_a, 0.95)
            ci_b = confidence_interval(vals_b, 0.95)

            if all(
                isinstance(v, bool) for v in vals_a + vals_b
            ) or all(
                v in (0.0, 1.0) for v in vals_a + vals_b
            ):
                mn = mcnemar_test(
                    [bool(v) for v in vals_a],
                    [bool(v) for v in vals_b],
                    self.alpha,
                )
                tests.append(mn)
                label = f"McNemar ({key})"
                mn.test_name = label

            tests.append(mw)
            tests.append(cd)

            summaries[key] = {
                "mean_a": round(sum(vals_a) / len(vals_a), 4) if vals_a else 0.0,
                "mean_b": round(sum(vals_b) / len(vals_b), 4) if vals_b else 0.0,
                "ci95_a": [round(ci_a[1], 4), round(ci_a[2], 4)],
                "ci95_b": [round(ci_b[1], 4), round(ci_b[2], 4)],
                "mw_statistic": round(mw.statistic, 4),
                "mw_p": round(mw.p_value, 4),
                "mw_sig": mw.significant,
                "cohens_d": round(cd.effect_size, 4),
                "cohens_d_label": cd.effect_size_label,
            }

        return StatisticalReport(
            condition_a=label_a,
            condition_b=label_b,
            tests=tests,
            metric_summaries=summaries,
        )
