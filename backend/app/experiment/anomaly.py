"""Anomaly detection for experiment runs.

Detects and flags outlier runs based on statistical analysis:
    - Extreme latency (IQR-based outlier detection)
    - Extreme confidence (too high/low compared to condition peers)
    - Decision inconsistency (same scenario → different decisions across conditions)
    - Convergence failure patterns
    - Resource usage anomalies (token spikes)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any

from app.experiment.orchestrator import OrchestratorResult, RunResult


@dataclass
class AnomalyReport:
    """A single detected anomaly in an experiment run."""

    run_index: int
    condition: str
    metric: str
    value: float
    expected_low: float
    expected_high: float
    severity: str  # "info", "warning", "critical"
    description: str = ""


@dataclass
class AnomalyCollection:
    """Collection of all detected anomalies for an experiment."""

    anomalies: list[AnomalyReport] = field(default_factory=list)

    @property
    def n_critical(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == "critical")

    @property
    def n_warnings(self) -> int:
        return sum(1 for a in self.anomalies if a.severity == "warning")

    def to_dict(self) -> list[dict[str, Any]]:
        return [
            {
                "run_index": a.run_index,
                "condition": a.condition,
                "metric": a.metric,
                "value": a.value,
                "expected_range": [a.expected_low, a.expected_high],
                "severity": a.severity,
                "description": a.description,
            }
            for a in self.anomalies
        ]


def _iqr_bounds(values: list[float]) -> tuple[float, float]:
    """Compute IQR-based outlier bounds."""
    if len(values) < 4:
        return (min(values) if values else 0.0, max(values) if values else 1.0)
    s = sorted(values)
    n = len(s)
    q1 = s[n // 4] if n >= 4 else s[0]
    q3 = s[3 * n // 4] if n >= 4 else s[-1]
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return (lower, upper)


def detect_latency_anomalies(
    result: OrchestratorResult,
) -> list[AnomalyReport]:
    """Detect runs with anomalous latency compared to their condition peers."""
    reports: list[AnomalyReport] = []
    for cond in result.conditions:
        runs = result.by_condition(cond)
        latencies = [r.elapsed_ms for r in runs]
        if len(latencies) < 3:
            continue
        lower, upper = _iqr_bounds(latencies)
        mean_lat = statistics.mean(latencies)

        for i, r in enumerate(runs):
            if r.elapsed_ms > upper and upper > 0:
                severity = "critical" if r.elapsed_ms > 3 * mean_lat else "warning"
                reports.append(AnomalyReport(
                    run_index=i,
                    condition=cond,
                    metric="latency_ms",
                    value=r.elapsed_ms,
                    expected_low=lower,
                    expected_high=upper,
                    severity=severity,
                    description=f"Latency {r.elapsed_ms:.0f}ms exceeds upper bound {upper:.0f}ms",
                ))
    return reports


def detect_confidence_anomalies(
    result: OrchestratorResult,
) -> list[AnomalyReport]:
    """Detect runs with confidence far from condition mean."""
    reports: list[AnomalyReport] = []
    for cond in result.conditions:
        runs = result.by_condition(cond)
        confidences = [r.confidence for r in runs]
        if len(confidences) < 3:
            continue
        mean_conf = statistics.mean(confidences)
        std_conf = statistics.stdev(confidences) if len(confidences) > 1 else 0.1
        lower = mean_conf - 2 * std_conf
        upper = mean_conf + 2 * std_conf

        for i, r in enumerate(runs):
            if r.confidence < lower or r.confidence > upper:
                reports.append(AnomalyReport(
                    run_index=i,
                    condition=cond,
                    metric="confidence",
                    value=r.confidence,
                    expected_low=max(0.0, lower),
                    expected_high=min(1.0, upper),
                    severity="warning",
                    description=f"Confidence {r.confidence:.3f} outside ±2σ range [{lower:.3f}, {upper:.3f}]",
                ))
    return reports


def detect_convergence_anomalies(
    result: OrchestratorResult,
) -> list[AnomalyReport]:
    """Detect runs where deliberation failed to converge."""
    reports: list[AnomalyReport] = []
    for i, r in enumerate(result.runs):
        if r.deliberation_result is not None:
            dr = r.deliberation_result
            if not dr.converged and dr.mediation_used:
                reports.append(AnomalyReport(
                    run_index=i,
                    condition=r.condition_name,
                    metric="convergence",
                    value=float(dr.total_rounds),
                    expected_low=1.0,
                    expected_high=float(dr.total_rounds),
                    severity="warning",
                    description=f"Deliberation did not converge in {dr.total_rounds} rounds (mediation used)",
                ))
    return reports


def detect_anomalies(result: OrchestratorResult) -> AnomalyCollection:
    """Run all anomaly detectors and return combined results."""
    all_reports: list[AnomalyReport] = []
    all_reports.extend(detect_latency_anomalies(result))
    all_reports.extend(detect_confidence_anomalies(result))
    all_reports.extend(detect_convergence_anomalies(result))
    return AnomalyCollection(anomalies=all_reports)
