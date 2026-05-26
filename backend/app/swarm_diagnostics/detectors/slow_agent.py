from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType


class SlowAgentDetector(BaseDetector):
    name = "slow_agent"

    def __init__(
        self,
        latency_p95_threshold_ms: float = 5000.0,
        min_samples: int = 5,
        trend_window: int = 20,
        timeout_rate_threshold: float = 0.3,
    ) -> None:
        self.latency_p95_threshold_ms = latency_p95_threshold_ms
        self.min_samples = min_samples
        self.trend_window = trend_window
        self.timeout_rate_threshold = timeout_rate_threshold

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics=None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []

        agent_latencies: dict[str, list[float]] = defaultdict(list)
        agent_timeouts: dict[str, int] = defaultdict(int)
        agent_vote_counts: dict[str, int] = defaultdict(int)

        for e in events:
            agent = e.source or "unknown"

            if e.event_type.startswith("vote:") or e.event_type.startswith("execution:"):
                if e.duration_ms is not None:
                    agent_latencies[agent].append(e.duration_ms)
                agent_vote_counts[agent] += 1

            if e.event_type.startswith("consensus:") and e.payload.get("timeout_info"):
                agent_timeouts[agent] += 1
                timeout_info = e.payload.get("timeout_info", {})
                if isinstance(timeout_info, dict):
                    for voter_key in ("voter", "agent", "voter_name"):
                        voter = timeout_info.get(voter_key)
                        if voter:
                            agent_timeouts[str(voter)] = agent_timeouts.get(str(voter), 0) + 1

        now = datetime.now(timezone.utc)

        for agent, latencies in agent_latencies.items():
            if len(latencies) < self.min_samples:
                continue

            sorted_lat = sorted(latencies)
            p95_idx = int(len(sorted_lat) * 0.95)
            p95_latency = sorted_lat[min(p95_idx, len(sorted_lat) - 1)]
            p50_latency = sorted_lat[int(len(sorted_lat) * 0.5)]

            total_votes = agent_vote_counts.get(agent, 0)
            timeouts = agent_timeouts.get(agent, 0)
            timeout_rate = timeouts / max(total_votes, 1)

            if timeout_rate >= self.timeout_rate_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.SLOW_AGENT,
                    severity=Severity.WARNING,
                    scope="global",
                    title=f"High timeout rate: {agent}",
                    description=(
                        f"{agent} has {timeout_rate:.0%} timeout rate "
                        f"({timeouts}/{total_votes} votes)"
                    ),
                    metric_value=timeout_rate,
                    threshold=self.timeout_rate_threshold,
                    evidence={
                        "agent": agent,
                        "timeout_rate": timeout_rate,
                        "timeouts": timeouts,
                        "total_votes": total_votes,
                    },
                    recommendation=(
                        f"Check {agent} response times and resource allocation."
                    ),
                ))

            if p95_latency >= self.latency_p95_threshold_ms:
                severity = (
                    Severity.CRITICAL
                    if p95_latency >= self.latency_p95_threshold_ms * 2
                    else Severity.WARNING
                )
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.SLOW_AGENT,
                    severity=severity,
                    scope="global",
                    title=f"Slow agent: {agent}",
                    description=(
                        f"{agent} P95 latency {p95_latency:.0f}ms exceeds "
                        f"threshold {self.latency_p95_threshold_ms:.0f}ms "
                        f"(P50: {p50_latency:.0f}ms, samples: {len(latencies)})"
                    ),
                    metric_value=p95_latency,
                    threshold=self.latency_p95_threshold_ms,
                    evidence={
                        "agent": agent,
                        "p95_latency_ms": p95_latency,
                        "p50_latency_ms": p50_latency,
                        "sample_count": len(latencies),
                        "threshold_ms": self.latency_p95_threshold_ms,
                    },
                    recommendation=(
                        f"Investigate {agent} performance. Consider increasing timeout or optimizing queries."
                    ),
                ))

            if len(latencies) >= self.trend_window:
                recent = latencies[-self.trend_window:]
                half = self.trend_window // 2
                first_half_avg = sum(recent[:half]) / half
                second_half_avg = sum(recent[half:]) / (self.trend_window - half)
                trend = second_half_avg - first_half_avg

                if trend >= 500:
                    signals.append(AnomalySignal(
                        anomaly_id=str(uuid.uuid4()),
                        detector_name=self.name,
                        anomaly_type=AnomalyType.SLOW_AGENT,
                        severity=Severity.WARNING,
                        scope="global",
                        title=f"Latency increasing: {agent}",
                        description=(
                            f"{agent} latency increased by {trend:.0f}ms over "
                            f"last {self.trend_window} samples"
                        ),
                        metric_value=trend,
                        threshold=500.0,
                        evidence={
                            "agent": agent,
                            "latency_trend_ms": trend,
                            "first_half_avg_ms": first_half_avg,
                            "second_half_avg_ms": second_half_avg,
                            "window": self.trend_window,
                        },
                        recommendation=(
                            f"Monitor {agent} for progressive slowdown."
                        ),
                    ))

        return signals
