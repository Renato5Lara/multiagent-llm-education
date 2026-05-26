from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from app.core.agent_health.models import (
    AgentHealthProfile,
    BehavioralBaseline,
    DegradationLevel,
    HealthSignal,
)


SIGNAL_PENALTY_WEIGHTS: dict[str, float] = {
    "circuit_breaker_open": 0.30,
    "timeout": 0.25,
    "hallucination": 0.35,
    "divergence": 0.20,
    "slow_response": 0.15,
    "consensus_instability": 0.25,
    "cognitive_drift": 0.20,
    "propagation_anomaly": 0.15,
    "degraded_agent": 0.30,
    "error_burst": 0.20,
    "overconfidence": 0.35,
    "decision_flipping": 0.20,
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "consensus_reliability": 0.35,
    "latency_score": 0.20,
    "consistency_score": 0.25,
    "calibration_score": 0.20,
}


def decay_factor(timestamp: datetime, half_life_minutes: float = 10.0) -> float:
    elapsed = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60.0
    return 2.0 ** (-elapsed / half_life_minutes)


def compute_latency_score(p95_ms: float, threshold_ms: float = 5000.0) -> float:
    if p95_ms <= 0:
        return 1.0
    if p95_ms >= threshold_ms:
        return 0.0
    return 1.0 - (p95_ms / threshold_ms)


def compute_consistency_score(sliding_stats: Any) -> float:
    if not sliding_stats.recent_decisions:
        return 1.0
    decisions = [d for d, _, _ in sliding_stats.recent_decisions]
    if len(decisions) < 2:
        return 1.0
    flips = sum(1 for i in range(1, len(decisions)) if decisions[i] != decisions[i - 1])
    flip_rate = flips / (len(decisions) - 1)
    return 1.0 - flip_rate


def compute_calibration_score(profile: AgentHealthProfile) -> float:
    stats = profile.sliding_stats
    baseline = profile.behavioral_baseline
    if not stats.recent_decisions or baseline.sample_count < 5:
        return 1.0
    recent_confidences = [c for _, c, _ in stats.recent_decisions]
    if not recent_confidences:
        return 1.0
    mean_confidence = sum(recent_confidences) / len(recent_confidences)
    approval = stats.approval_rate
    calibration_error = abs(mean_confidence - approval)
    return max(0.0, 1.0 - calibration_error * 2.0)


def compute_base_score(
    profile: AgentHealthProfile,
    weights: dict[str, float] | None = None,
) -> float:
    w = weights or DEFAULT_WEIGHTS

    reliability = profile.sliding_stats.approval_rate
    latency = compute_latency_score(profile.sliding_stats.p95_latency)
    consistency = compute_consistency_score(profile.sliding_stats)
    calibration = compute_calibration_score(profile)

    score = (
        w["consensus_reliability"] * reliability
        + w["latency_score"] * latency
        + w["consistency_score"] * consistency
        + w["calibration_score"] * calibration
    )
    return max(0.0, min(1.0, score))


def compute_penalty_total(profile: AgentHealthProfile) -> float:
    total = 0.0
    cutoff = time.time() - 1800
    for signal in profile.recent_signals:
        if signal.timestamp.timestamp() < cutoff:
            continue
        decay = decay_factor(signal.timestamp)
        weight = SIGNAL_PENALTY_WEIGHTS.get(signal.signal_type, 0.15)
        total += signal.severity * weight * decay
    return min(total, 1.0)


def compute_recovery_bonus(profile: AgentHealthProfile, recovery_rate: float = 0.1) -> float:
    if not profile.recent_signals:
        return 0.0
    last_signal = max(s.timestamp for s in profile.recent_signals)
    elapsed_minutes = (datetime.now(timezone.utc) - last_signal).total_seconds() / 60.0
    return min(recovery_rate * elapsed_minutes / 10.0, 0.2)


def compute_health_score(
    profile: AgentHealthProfile,
    weights: dict[str, float] | None = None,
) -> float:
    base = compute_base_score(profile, weights)
    penalty = compute_penalty_total(profile)
    bonus = compute_recovery_bonus(profile)
    score = base - penalty + bonus
    return max(0.0, min(1.0, score))


class HealthScorer:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._lock = Lock()
        self._score_history: dict[str, list[tuple[float, float]]] = {}

    def score(self, profile: AgentHealthProfile) -> float:
        score = compute_health_score(profile, self._weights)
        with self._lock:
            history = self._score_history.setdefault(profile.agent_name, [])
            history.append((time.time(), score))
            if len(history) > 100:
                self._score_history[profile.agent_name] = history[-100:]
        return score

    def get_score_history(self, agent_name: str, limit: int = 50) -> list[tuple[float, float]]:
        with self._lock:
            return list(self._score_history.get(agent_name, []))[-limit:]

    def reset(self) -> None:
        with self._lock:
            self._score_history.clear()
