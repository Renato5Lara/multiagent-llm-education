"""SwarmActivationMetrics — collects and exposes metrics for the full swarm activation lifecycle."""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


class SwarmActivationMetrics:
    """Thread-safe metrics collector for swarm activation.

    Tracks:
    - Per-phase duration, success/failure
    - Per-agent invocations, duration
    - Event propagation counts
    - Consensus vote distribution
    - Activation totals
    """

    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.activations: int = 0
            self.activation_successes: int = 0
            self.activation_failures: int = 0
            self.phase_metrics: dict[str, dict] = defaultdict(lambda: {
                "invocations": 0,
                "successes": 0,
                "failures": 0,
                "timeouts": 0,
                "total_duration_ms": 0.0,
                "min_duration_ms": float("inf"),
                "max_duration_ms": 0.0,
            })
            self.agent_metrics: dict[str, dict] = defaultdict(lambda: {
                "invocations": 0,
                "successes": 0,
                "failures": 0,
                "total_duration_ms": 0.0,
            })
            self.event_counts: dict[str, int] = defaultdict(int)
            self.propagation_counts: dict[str, int] = defaultdict(int)
            self.consensus_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
            self.anomaly_counts: dict[str, int] = defaultdict(int)
            self._started_at = datetime.now(timezone.utc)

    def record_activation(self, success: bool) -> None:
        with self._lock:
            self.activations += 1
            if success:
                self.activation_successes += 1
            else:
                self.activation_failures += 1

    def record_phase(
        self, phase: str, duration_ms: float, status: str,
    ) -> None:
        with self._lock:
            m = self.phase_metrics[phase]
            m["invocations"] += 1
            m["total_duration_ms"] += duration_ms
            if duration_ms < m["min_duration_ms"]:
                m["min_duration_ms"] = duration_ms
            if duration_ms > m["max_duration_ms"]:
                m["max_duration_ms"] = duration_ms
            if status == "completed":
                m["successes"] += 1
            elif status == "failed":
                m["failures"] += 1
            elif status == "timed_out":
                m["timeouts"] += 1

    def record_agent(
        self, agent_name: str, duration_ms: float, success: bool,
    ) -> None:
        with self._lock:
            m = self.agent_metrics[agent_name]
            m["invocations"] += 1
            m["total_duration_ms"] += duration_ms
            if success:
                m["successes"] += 1
            else:
                m["failures"] += 1

    def record_event(self, event_type: str, propagated: bool) -> None:
        with self._lock:
            self.event_counts[event_type] += 1
            if propagated:
                self.propagation_counts[event_type] += 1

    def record_consensus_vote(self, voter: str, decision: str) -> None:
        with self._lock:
            self.consensus_votes[voter][decision] += 1

    def record_anomaly(self, anomaly_type: str) -> None:
        with self._lock:
            self.anomaly_counts[anomaly_type] += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            phase_summary = {}
            for phase, m in self.phase_metrics.items():
                inv = m["invocations"]
                phase_summary[phase] = {
                    "invocations": inv,
                    "successes": m["successes"],
                    "failures": m["failures"],
                    "timeouts": m["timeouts"],
                    "avg_duration_ms": round(m["total_duration_ms"] / inv, 2) if inv else 0,
                    "min_duration_ms": m["min_duration_ms"] if inv else 0,
                    "max_duration_ms": m["max_duration_ms"],
                }

            agent_summary = {}
            for agent, m in self.agent_metrics.items():
                inv = m["invocations"]
                agent_summary[agent] = {
                    "invocations": inv,
                    "successes": m["successes"],
                    "failures": m["failures"],
                    "avg_duration_ms": round(m["total_duration_ms"] / inv, 2) if inv else 0,
                }

            event_summary = {}
            for et, count in self.event_counts.items():
                propagated = self.propagation_counts.get(et, 0)
                event_summary[et] = {
                    "total": count,
                    "propagated": propagated,
                    "propagation_rate": round(propagated / count, 2) if count else 0,
                }

            vote_summary = {}
            for voter, decisions in self.consensus_votes.items():
                vote_summary[voter] = dict(decisions)

            elapsed = (datetime.now(timezone.utc) - self._started_at).total_seconds()

            return {
                "activations": self.activations,
                "activation_successes": self.activation_successes,
                "activation_failures": self.activation_failures,
                "success_rate": round(
                    self.activation_successes / max(self.activations, 1), 4,
                ),
                "phases": phase_summary,
                "agents": agent_summary,
                "events": event_summary,
                "consensus_votes": vote_summary,
                "anomalies": dict(self.anomaly_counts),
                "uptime_seconds": round(elapsed, 2),
            }


# Module-level singleton
swarm_metrics = SwarmActivationMetrics()
