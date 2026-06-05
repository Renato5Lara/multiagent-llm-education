from __future__ import annotations

import math
from statistics import mean, pstdev

from app.benchmark.schemas import StatisticalComparison


def compare_metric(metric: str, baseline_name: str, treatment_name: str, baseline: list[float], treatment: list[float]) -> StatisticalComparison:
    b_mean = mean(baseline) if baseline else 0.0
    t_mean = mean(treatment) if treatment else 0.0
    u = mann_whitney_u(baseline, treatment)
    rb = rank_biserial(u, len(baseline), len(treatment))
    delta = t_mean - b_mean
    ci_low, ci_high = mean_difference_ci(baseline, treatment)
    return StatisticalComparison(
        metric=metric,
        baseline=baseline_name,
        treatment=treatment_name,
        baseline_mean=round(b_mean, 4),
        treatment_mean=round(t_mean, 4),
        delta=round(delta, 4),
        mann_whitney_u=round(u, 4),
        mann_whitney_p=round(mann_whitney_p_value(u, len(baseline), len(treatment)), 6),
        rank_biserial=round(rb, 4),
        cohens_d=round(cohens_d(baseline, treatment), 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
    )


def mann_whitney_u(x: list[float], y: list[float]) -> float:
    combined = sorted([(value, "x") for value in x] + [(value, "y") for value in y], key=lambda item: item[0])
    ranks: list[tuple[float, str]] = []
    index = 0
    while index < len(combined):
        end = index + 1
        while end < len(combined) and combined[end][0] == combined[index][0]:
            end += 1
        avg_rank = (index + 1 + end) / 2
        ranks.extend((avg_rank, group) for _, group in combined[index:end])
        index = end
    rank_x = sum(rank for rank, group in ranks if group == "x")
    return rank_x - (len(x) * (len(x) + 1) / 2)


def mann_whitney_p_value(u: float, n1: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 1.0
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma == 0:
        return 1.0
    z = abs((u - mu) / sigma)
    return max(0.0, min(1.0, math.erfc(z / math.sqrt(2))))


def rank_biserial(u: float, n1: int, n2: int) -> float:
    if n1 == 0 or n2 == 0:
        return 0.0
    return (2 * u / (n1 * n2)) - 1


def cohens_d(x: list[float], y: list[float]) -> float:
    if not x or not y:
        return 0.0
    pooled = math.sqrt((pstdev(x) ** 2 + pstdev(y) ** 2) / 2)
    return 0.0 if pooled == 0 else (mean(y) - mean(x)) / pooled


def mean_difference_ci(x: list[float], y: list[float], z: float = 1.96) -> tuple[float, float]:
    if not x or not y:
        return 0.0, 0.0
    diff = mean(y) - mean(x)
    se = math.sqrt((pstdev(x) ** 2 / len(x)) + (pstdev(y) ** 2 / len(y)))
    return diff - z * se, diff + z * se


def mcnemar(baseline_success: list[bool], treatment_success: list[bool]) -> tuple[float, float]:
    b = sum(1 for left, right in zip(baseline_success, treatment_success) if left and not right)
    c = sum(1 for left, right in zip(baseline_success, treatment_success) if not left and right)
    if b + c == 0:
        return 0.0, 1.0
    chi2 = (abs(b - c) - 1) ** 2 / (b + c)
    return chi2, math.erfc(math.sqrt(chi2 / 2))
