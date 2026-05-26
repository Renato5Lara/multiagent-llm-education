from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum
from typing import Any

from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal


class DegradationLevel(IntEnum):
    NONE = 0
    MILD = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4

    @classmethod
    def from_health_score(cls, score: float) -> DegradationLevel:
        if score >= 0.8:
            return cls.NONE
        if score >= 0.6:
            return cls.MILD
        if score >= 0.4:
            return cls.MODERATE
        if score >= 0.2:
            return cls.SEVERE
        return cls.CRITICAL

    @property
    def vote_weight(self) -> float:
        return {0: 1.0, 1: 0.9, 2: 0.7, 3: 0.4, 4: 0.0}[self.value]

    @property
    def label(self) -> str:
        return {0: "none", 1: "mild", 2: "moderate", 3: "severe", 4: "critical"}[self.value]

    @property
    def description(self) -> str:
        return {
            0: "Agent is healthy, full participation",
            1: "Slight degradation, increased monitoring",
            2: "Moderate issues, vote weight reduced",
            3: "Severe degradation, circuit breaker sensitivity increased",
            4: "Critical, agent quarantined",
        }[self.value]


@dataclass
class BehavioralBaseline:
    approval_rate: float = 0.5
    confidence_mean: float = 0.5
    confidence_std: float = 0.0
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    consistency_score: float = 1.0
    sample_count: int = 0
    window_minutes: int = 60

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_rate": self.approval_rate,
            "confidence_mean": self.confidence_mean,
            "confidence_std": self.confidence_std,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p95_ms": self.latency_p95_ms,
            "consistency_score": self.consistency_score,
            "sample_count": self.sample_count,
            "window_minutes": self.window_minutes,
        }


@dataclass
class AgentSlidingStats:
    recent_decisions: deque[tuple[str, float, datetime]] = field(default_factory=lambda: deque(maxlen=100))
    recent_latencies: deque[float] = field(default_factory=lambda: deque(maxlen=100))
    recent_errors: deque[str] = field(default_factory=lambda: deque(maxlen=50))
    recent_anomalies: deque[AnomalySignal] = field(default_factory=lambda: deque(maxlen=50))
    total_timeouts: int = 0
    total_cb_opens: int = 0
    total_votes: int = 0

    @property
    def error_rate(self) -> float:
        return len(self.recent_errors) / max(len(self.recent_latencies), 1)

    @property
    def p95_latency(self) -> float:
        if not self.recent_latencies:
            return 0.0
        sorted_vals = sorted(self.recent_latencies)
        idx = int(len(sorted_vals) * 0.95)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def p50_latency(self) -> float:
        if not self.recent_latencies:
            return 0.0
        sorted_vals = sorted(self.recent_latencies)
        idx = int(len(sorted_vals) * 0.5)
        return sorted_vals[min(idx, len(sorted_vals) - 1)]

    @property
    def approval_rate(self) -> float:
        if not self.recent_decisions:
            return 0.5
        approves = sum(1 for d, _, _ in self.recent_decisions if d == "approve")
        return approves / len(self.recent_decisions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_rate": self.error_rate,
            "p95_latency_ms": self.p95_latency,
            "p50_latency_ms": self.p50_latency,
            "approval_rate": self.approval_rate,
            "total_timeouts": self.total_timeouts,
            "total_cb_opens": self.total_cb_opens,
            "total_votes": self.total_votes,
            "recent_errors": list(self.recent_errors),
        }


@dataclass
class HealthSignal:
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type: str = ""
    agent_name: str = ""
    severity: float = 0.0
    metric_value: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "signal_type": self.signal_type,
            "agent_name": self.agent_name,
            "severity": self.severity,
            "metric_value": self.metric_value,
            "timestamp": self.timestamp.isoformat(),
            "evidence": self.evidence,
            "source": self.source,
        }


@dataclass
class AgentHealthProfile:
    agent_name: str
    health_score: float = 1.0
    degradation_level: DegradationLevel = DegradationLevel.NONE
    behavioral_baseline: BehavioralBaseline = field(default_factory=BehavioralBaseline)
    recent_signals: list[HealthSignal] = field(default_factory=list)
    sliding_stats: AgentSlidingStats = field(default_factory=AgentSlidingStats)
    cognitive_drift: float = 0.0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    max_signals: int = 100

    def update_degradation(self) -> None:
        self.degradation_level = DegradationLevel.from_health_score(self.health_score)

    def add_signal(self, signal: HealthSignal) -> None:
        self.recent_signals.append(signal)
        if len(self.recent_signals) > self.max_signals:
            self.recent_signals = self.recent_signals[-self.max_signals:]

    @property
    def vote_weight(self) -> float:
        return self.degradation_level.vote_weight

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "health_score": round(self.health_score, 4),
            "degradation_level": self.degradation_level.label,
            "vote_weight": self.vote_weight,
            "cognitive_drift": round(self.cognitive_drift, 4),
            "behavioral_baseline": self.behavioral_baseline.to_dict(),
            "sliding_stats": self.sliding_stats.to_dict(),
            "recent_signals": [s.to_dict() for s in self.recent_signals[-10:]],
            "last_updated": self.last_updated.isoformat(),
        }
