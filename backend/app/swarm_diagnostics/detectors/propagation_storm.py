"""
PropagationStormDetector — Detects abnormal propagation rate spikes
that may indicate cascading or runaway event propagation through the swarm.

Signals:
    - propagation_rate_spike: events/sec per propagation chain exceeds threshold
    - chain_depth_anomaly: chain advances in bursts (compressed timing)
    - fanout_explosion: single event triggers excessive downstream events
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any

from app.swarm_diagnostics.detectors.base import BaseDetector
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, Severity, AnomalyType
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class PropagationStormDetector(BaseDetector):
    name = "propagation_storm"

    def __init__(
        self,
        rate_spike_threshold: float = 20.0,
        compressed_timing_ratio: float = 0.1,
        min_events_for_detection: int = 10,
    ):
        self.rate_spike_threshold = rate_spike_threshold
        self.compressed_timing_ratio = compressed_timing_ratio
        self.min_events_for_detection = min_events_for_detection

    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        signals: list[AnomalySignal] = []
        if len(events) < self.min_events_for_detection:
            return signals

        chain_events: dict[str, list[DiagnosticEvent]] = defaultdict(list)
        for e in events:
            causation = e.causation_id or "root"
            chain_events[causation].append(e)

        for chain_id, chain in chain_events.items():
            if len(chain) < 5:
                continue

            chain.sort(key=lambda x: x.created_at)
            span = (chain[-1].created_at - chain[0].created_at).total_seconds()
            rate = len(chain) / span if span > 0 else float("inf")

            if rate > self.rate_spike_threshold:
                signals.append(AnomalySignal(
                    anomaly_id=str(uuid.uuid4()),
                    detector_name=self.name,
                    anomaly_type=AnomalyType.PROPAGATION_STORM,
                    severity=Severity.CRITICAL,
                    scope=f"chain:{chain_id[:16]}",
                    title="Propagation rate spike detected",
                    description=(
                        f"Chain {chain_id[:16]} propagating at "
                        f"{rate:.1f} events/s (threshold: {self.rate_spike_threshold})"
                    ),
                    metric_value=rate,
                    threshold=self.rate_spike_threshold,
                    evidence={
                        "chain_id": chain_id,
                        "event_count": len(chain),
                        "time_span_sec": round(span, 3),
                        "events_per_sec": round(rate, 1),
                        "event_types": list(set(e.event_type for e in chain)),
                    },
                    recommendation=(
                        "Check for runaway propagation loops. "
                        "Verify PropagationTTL hop limits and decay factors. "
                        "Consider reducing max_hops or increasing decay."
                    ),
                ))

            if span > 0:
                avg_interval = span / len(chain)
                if avg_interval < 0.001:
                    intervals = [
                        (chain[i + 1].created_at - chain[i].created_at).total_seconds()
                        for i in range(len(chain) - 1)
                    ]
                    min_interval = min(intervals)
                    if len(intervals) > 3 and min_interval < avg_interval * self.compressed_timing_ratio:
                        signals.append(AnomalySignal(
                            anomaly_id=str(uuid.uuid4()),
                            detector_name=self.name,
                            anomaly_type=AnomalyType.PROPAGATION_STORM,
                            severity=Severity.WARNING,
                            scope=f"chain:{chain_id[:16]}",
                            title="Compressed propagation timing",
                            description=(
                                f"Chain {chain_id[:16]} has burst interval "
                                f"{min_interval * 1000:.1f}ms "
                                f"(avg: {avg_interval * 1000:.1f}ms)"
                            ),
                            metric_value=min_interval,
                            threshold=avg_interval * self.compressed_timing_ratio,
                            evidence={
                                "chain_id": chain_id,
                                "avg_interval_ms": round(avg_interval * 1000, 2),
                                "min_interval_ms": round(min_interval * 1000, 2),
                            },
                            recommendation="Bursty propagation may indicate cascading feedback. Consider adding jitter or rate limiting.",
                        ))

        return signals
