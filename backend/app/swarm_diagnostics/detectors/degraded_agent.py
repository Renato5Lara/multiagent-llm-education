from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


class DegradedAgentDetector(BaseDetector):
    name = "degraded_agent"

    def __init__(
        self,
        health_threshold: float = 0.4,
        min_window_events: int = 5,
        window_seconds: float = 300.0,
        cb_open_threshold: int = 3,
        timeout_threshold: int = 3,
    ) -> None:
        self.health_threshold = health_threshold
        self.min_window_events = min_window_events
        self.window_seconds = window_seconds
        self.cb_open_threshold = cb_open_threshold
        self.timeout_threshold = timeout_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics=None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - self.window_seconds

        window = [e for e in events if e.created_at and e.created_at.timestamp() >= cutoff]

        agent_breaker_events: dict[str, int] = defaultdict(int)
        agent_timeout_events: dict[str, int] = defaultdict(int)
        agent_error_events: dict[str, int] = defaultdict(int)
        agent_total_events: dict[str, int] = defaultdict(int)

        for e in window:
            agent = e.source or "unknown"
            agent_total_events[agent] += 1

            if e.event_type.startswith("breaker."):
                agent_breaker_events[agent] += 1

            if e.event_type.startswith("consensus:") and e.payload.get("timeout_info"):
                agent_timeout_events[agent] += 1

            if e.error:
                agent_error_events[agent] += 1

            if e.event_type.startswith("execution:") and ":error" in e.event_type:
                agent_error_events[agent] += 1

        for agent in agent_total_events:
            if agent_total_events[agent] < self.min_window_events:
                continue

            cb_opens = agent_breaker_events.get(agent, 0)
            timeouts = agent_timeout_events.get(agent, 0)
            errors = agent_error_events.get(agent, 0)
            total = agent_total_events[agent]

            severity_score = 0.0
            reasons: list[str] = []

            if cb_opens >= self.cb_open_threshold:
                severity_score += 0.4
                reasons.append(f"{cb_opens} circuit breaker opens")

            if timeouts >= self.timeout_threshold:
                severity_score += 0.3
                reasons.append(f"{timeouts} timeouts")

            error_rate = errors / total if total > 0 else 0
            if error_rate > 0.5:
                severity_score += 0.4
                reasons.append(f"error rate {error_rate:.0%}")

            if severity_score >= 0.4:
                severity = Severity.CRITICAL if severity_score >= 0.7 else Severity.WARNING
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.DEGRADED_AGENT,
                    severity=severity,
                    scope="global",
                    title=f"Degraded agent: {agent}",
                    description=f"Agent {agent} shows degradation: {', '.join(reasons)}",
                    metric_value=severity_score,
                    threshold=self.health_threshold,
                    evidence={
                        "agent": agent,
                        "circuit_breaker_opens": cb_opens,
                        "timeouts": timeouts,
                        "errors": errors,
                        "total_events": total,
                        "error_rate": error_rate,
                        "severity_score": severity_score,
                    },
                    recommendation=(
                        f"Review agent {agent} configuration. "
                        "Consider increasing circuit breaker sensitivity or reducing load."
                    ),
                ))

        return signals
