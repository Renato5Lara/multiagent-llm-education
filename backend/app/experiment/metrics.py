"""
Experimental Metrics — extract quantifiable measures from consensus results
for cross-condition comparison.  Zero external dependencies (stdlib only).

Metrics collected:
    - Decision accuracy (vs ground truth)
    - Confidence calibration (ECE, MCE)
    - Latency (per-voter, total)
    - Voter agreement / disagreement rate
    - Weight entropy (adaptive vs uniform)
    - Trust score variance
    - Specialization affinity spread
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import ConsensusResult, VoteDecision


@dataclass
class PerRunMetrics:
    """Metrics extracted from a single consensus run."""

    condition_name: str
    run_index: int

    # Decision
    decision: str
    confidence: float
    correct: bool | None  # None if no ground truth available
    unanimous: bool

    # Latency
    total_latency_ms: float
    voter_latencies_ms: list[float]
    latency_variance: float
    min_voter_latency_ms: float
    max_voter_latency_ms: float

    # Votes
    num_voters: int
    approvals: int
    rejections: int
    abstentions: int
    disagreement: bool

    # Weights (adaptive conditions only)
    weight_entropy: float | None
    trust_variance: float | None
    affinity_variance: float | None

    # Timing info
    timed_out_voters: int = 0
    degraded: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition": self.condition_name,
            "run": self.run_index,
            "decision": self.decision,
            "confidence": self.confidence,
            "correct": self.correct,
            "unanimous": self.unanimous,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "latency_variance": round(self.latency_variance, 4),
            "num_voters": self.num_voters,
            "approvals": self.approvals,
            "rejections": self.rejections,
            "abstentions": self.abstentions,
            "disagreement": self.disagreement,
            "weight_entropy": round(self.weight_entropy, 4) if self.weight_entropy is not None else None,
            "trust_variance": round(self.trust_variance, 6) if self.trust_variance is not None else None,
            "affinity_variance": round(self.affinity_variance, 6) if self.affinity_variance is not None else None,
            "timed_out_voters": self.timed_out_voters,
            "degraded": self.degraded,
        }


def compute_entropy(weights: dict[str, float]) -> float:
    """Shannon entropy of a weight distribution.

    Entropy = 0 means a single voter has all weight (dictatorship).
    Entropy = log(n) means uniform distribution.
    """
    values = list(weights.values())
    total = sum(values)
    if total == 0:
        return 0.0
    probs = [v / total for v in values]
    return -sum(p * math.log(p) for p in probs if p > 0)


def compute_variance(values: list[float]) -> float:
    """Sample variance (ddof=1)."""
    if len(values) < 2:
        return 0.0
    try:
        return statistics.variance(values)
    except statistics.StatisticsError:
        return 0.0


def extract_metrics(
    result: ConsensusResult,
    condition_name: str,
    run_index: int,
    ground_truth: VoteDecision | None = None,
) -> PerRunMetrics:
    """Extract all metrics from a single ConsensusResult."""
    correct: bool | None = None
    if ground_truth is not None:
        correct = result.decision == ground_truth

    latencies = [t.get("duration_ms", 0.0) for t in result.voter_timings]

    # Weight entropy (if weights were computed)
    weight_entropy: float | None = None
    if result.weights_used:
        weight_entropy = compute_entropy(result.weights_used)

    trust_variance: float | None = None
    if result.trust_scores:
        trust_variance = compute_variance(list(result.trust_scores.values()))

    affinity_variance: float | None = None
    if result.specialization_affinities:
        affinity_variance = compute_variance(
            list(result.specialization_affinities.values())
        )

    timeout_info = result.timeout_info or {}
    timed_out: int = 0
    degraded: bool = False
    if isinstance(timeout_info, dict):
        timed_out = timeout_info.get("timed_out_voters", 0)
        degraded = timeout_info.get("degraded", False)

    return PerRunMetrics(
        condition_name=condition_name,
        run_index=run_index,
        decision=result.decision.value,
        confidence=result.confidence,
        correct=correct,
        unanimous=_is_unanimous(result),
        total_latency_ms=sum(latencies),
        voter_latencies_ms=latencies,
        latency_variance=compute_variance(latencies),
        min_voter_latency_ms=min(latencies) if latencies else 0.0,
        max_voter_latency_ms=max(latencies) if latencies else 0.0,
        num_voters=len(result.votes),
        approvals=sum(1 for v in result.votes if v.decision == VoteDecision.APPROVE),
        rejections=sum(1 for v in result.votes if v.decision == VoteDecision.REJECT),
        abstentions=sum(1 for v in result.votes if v.decision == VoteDecision.ABSTAIN),
        disagreement=(
            result.decision == VoteDecision.APPROVE
            and any(v.decision == VoteDecision.REJECT for v in result.votes)
        ),
        weight_entropy=weight_entropy,
        trust_variance=trust_variance,
        affinity_variance=affinity_variance,
        timed_out_voters=timed_out,
        degraded=degraded,
    )


def _is_unanimous(result: ConsensusResult) -> bool:
    """Check if all votes agree with the final decision."""
    return all(v.decision == result.decision for v in result.votes)


# ── Aggregation ──────────────────────────────────────────────────


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stdev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    try:
        return statistics.stdev(values)
    except statistics.StatisticsError:
        return 0.0


def _norm_ci(data: list[float], confidence: float = 0.95) -> tuple[float, float, float, float]:
    """Compute mean, stdev, and approximate confidence interval (t-distribution)."""
    n = len(data)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    mean = _mean(data)
    std = _stdev(data)
    # t-value approximation for 95% CI
    t_val = 1.96 if n >= 120 else _t_value(n - 1, confidence)
    h = std * t_val / math.sqrt(n) if std > 0 else 0.0
    return mean, std, mean - h, mean + h


def _t_value(df: int, confidence: float = 0.95) -> float:
    """Approximate t critical value using normal approximation.

    For df >= 30, t ≈ z.  For small df, use conservative approximation.
    This avoids importing scipy.
    """
    if df >= 120:
        return 1.96 if confidence == 0.95 else 2.576
    # Conservative approximation for small df
    approx = {
        1: 12.71, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
        6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
        16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
        21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
        26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    }
    return approx.get(df, 2.0)


def _ece(confidences: list[float], correct: list[bool], n_bins: int = 10) -> float:
    """Expected Calibration Error — stdlib-only implementation."""
    if not confidences:
        return 0.0
    n = len(confidences)
    bin_edges = [i / n_bins for i in range(n_bins + 1)]

    total_ece = 0.0
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        # Gather samples in this bin (last bin includes hi)
        bin_confs: list[float] = []
        bin_correct: list[bool] = []
        for j in range(n):
            c = confidences[j]
            if lo <= c < hi or (i == n_bins - 1 and c == hi):
                bin_confs.append(c)
                bin_correct.append(correct[j])
        if not bin_confs:
            continue
        bin_conf = _mean(bin_confs)
        bin_acc = _mean([1.0 if x else 0.0 for x in bin_correct])
        weight = len(bin_confs) / n
        total_ece += abs(bin_conf - bin_acc) * weight
    return total_ece


def _mce(confidences: list[float], correct: list[bool], n_bins: int = 10) -> float:
    """Maximum Calibration Error — stdlib-only."""
    if not confidences:
        return 0.0
    n = len(confidences)
    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    max_err = 0.0
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        bin_confs: list[float] = []
        bin_correct: list[bool] = []
        for j in range(n):
            c = confidences[j]
            if lo <= c < hi or (i == n_bins - 1 and c == hi):
                bin_confs.append(c)
                bin_correct.append(correct[j])
        if not bin_confs:
            continue
        bin_conf = _mean(bin_confs)
        bin_acc = _mean([1.0 if x else 0.0 for x in bin_correct])
        max_err = max(max_err, abs(bin_conf - bin_acc))
    return max_err


@dataclass
class AggregatedMetrics:
    """Aggregate statistics across multiple runs of the same condition."""

    condition_name: str
    n_runs: int

    # Decision accuracy
    accuracy: float = 0.0
    accuracy_std: float = 0.0
    accuracy_ci95_low: float = 0.0
    accuracy_ci95_high: float = 0.0

    # Confidence calibration
    avg_confidence: float = 0.0
    confidence_std: float = 0.0
    ece: float = 0.0
    mce: float = 0.0

    # Latency
    avg_latency_ms: float = 0.0
    latency_std: float = 0.0

    # Agreement
    unanimous_rate: float = 0.0
    disagreement_rate: float = 0.0

    # Weight dynamics
    avg_weight_entropy: float | None = None
    avg_trust_variance: float | None = None
    avg_affinity_variance: float | None = None

    # Timing
    avg_timed_out: float = 0.0
    degraded_rate: float = 0.0

    @property
    def summary(self) -> str:
        parts = [
            f"{self.condition_name} (n={self.n_runs})",
            f"  Accuracy: {self.accuracy:.3f} ± {self.accuracy_std:.3f}",
            f"  Confidence: {self.avg_confidence:.3f} ± {self.confidence_std:.3f}",
            f"  ECE: {self.ece:.4f}",
            f"  Latency: {self.avg_latency_ms:.1f}ms",
            f"  Unanimous: {self.unanimous_rate:.1%}",
        ]
        if self.avg_weight_entropy is not None:
            parts.append(f"  Weight entropy: {self.avg_weight_entropy:.4f}")
        return "\n".join(parts)


def aggregate_metrics(metrics: list[PerRunMetrics]) -> AggregatedMetrics:
    """Aggregate per-run metrics into summary statistics."""
    if not metrics:
        return AggregatedMetrics(condition_name="empty", n_runs=0)

    condition = metrics[0].condition_name
    n = len(metrics)

    accuracies = [1.0 if m.correct else 0.0 for m in metrics if m.correct is not None]
    confidences = [m.confidence for m in metrics]
    latencies = [m.total_latency_ms for m in metrics]
    unanimous_vals = [m.unanimous for m in metrics]
    disagreement_vals = [m.disagreement for m in metrics]

    # Accuracy
    acc_mean, acc_std, acc_low, acc_high = _norm_ci(accuracies)

    # Confidence calibration (requires correctness labels)
    correct_bool = [m.correct for m in metrics if m.correct is not None]
    conf_filtered = [m.confidence for m in metrics if m.correct is not None]
    cal_ece = _ece(conf_filtered, correct_bool) if conf_filtered else 0.0
    cal_mce = _mce(conf_filtered, correct_bool) if conf_filtered else 0.0

    # Weight entropy (only for conditions that compute weights)
    weight_entropies = [m.weight_entropy for m in metrics if m.weight_entropy is not None]
    trust_vars = [m.trust_variance for m in metrics if m.trust_variance is not None]
    affinity_vars = [m.affinity_variance for m in metrics if m.affinity_variance is not None]

    return AggregatedMetrics(
        condition_name=condition,
        n_runs=n,
        accuracy=acc_mean,
        accuracy_std=acc_std,
        accuracy_ci95_low=acc_low,
        accuracy_ci95_high=acc_high,
        avg_confidence=_mean(confidences),
        confidence_std=_stdev(confidences),
        ece=cal_ece,
        mce=cal_mce,
        avg_latency_ms=_mean(latencies),
        latency_std=_stdev(latencies),
        unanimous_rate=sum(unanimous_vals) / n,
        disagreement_rate=sum(disagreement_vals) / n,
        avg_weight_entropy=_mean(weight_entropies) if weight_entropies else None,
        avg_trust_variance=_mean(trust_vars) if trust_vars else None,
        avg_affinity_variance=_mean(affinity_vars) if affinity_vars else None,
        avg_timed_out=_mean([m.timed_out_voters for m in metrics]),
        degraded_rate=sum(m.degraded for m in metrics) / n,
    )
