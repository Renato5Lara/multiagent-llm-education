from __future__ import annotations

import math
from collections import defaultdict
from threading import Lock

from app.core.agent_health.models import BehavioralBaseline


class BehavioralBaselineManager:
    def __init__(
        self,
        alpha_approval: float = 0.05,
        alpha_latency: float = 0.1,
        alpha_confidence: float = 0.05,
        max_agents: int = 50,
    ) -> None:
        self._baselines: dict[str, BehavioralBaseline] = {}
        self._alpha_approval = alpha_approval
        self._alpha_latency = alpha_latency
        self._alpha_confidence = alpha_confidence
        self._max_agents = max_agents
        self._lock = Lock()

    def update(
        self,
        agent_name: str,
        decision: str | None = None,
        confidence: float | None = None,
        latency_ms: float | None = None,
    ) -> BehavioralBaseline:
        with self._lock:
            baseline = self._baselines.get(agent_name)
            if baseline is None:
                if len(self._baselines) >= self._max_agents:
                    oldest = min(self._baselines.keys(), key=lambda k: self._baselines[k].sample_count)
                    del self._baselines[oldest]
                baseline = BehavioralBaseline()
                self._baselines[agent_name] = baseline

            baseline.sample_count += 1

            if decision is not None:
                is_approve = 1.0 if decision == "approve" else 0.0
                baseline.approval_rate = (
                    self._ema(baseline.approval_rate, is_approve, self._alpha_approval)
                )

            if confidence is not None:
                prev_mean = baseline.confidence_mean
                baseline.confidence_mean = self._ema(prev_mean, confidence, self._alpha_confidence)
                if baseline.sample_count > 1:
                    diff = confidence - prev_mean
                    baseline.confidence_std = math.sqrt(
                        (1 - self._alpha_confidence) * (baseline.confidence_std ** 2)
                        + self._alpha_confidence * diff * diff
                    )

            if latency_ms is not None:
                baseline.latency_p50_ms = self._ema(
                    baseline.latency_p50_ms, latency_ms, self._alpha_latency
                )
                if latency_ms > baseline.latency_p95_ms:
                    baseline.latency_p95_ms = self._ema(
                        baseline.latency_p95_ms, latency_ms, self._alpha_latency * 2
                    )
                else:
                    baseline.latency_p95_ms = self._ema(
                        baseline.latency_p95_ms, latency_ms, self._alpha_latency * 0.5
                    )

            return baseline

    def get_baseline(self, agent_name: str) -> BehavioralBaseline | None:
        with self._lock:
            return self._baselines.get(agent_name)

    def compute_deviation(self, agent_name: str, current_approval: float) -> float:
        baseline = self.get_baseline(agent_name)
        if baseline is None or baseline.sample_count < 5:
            return 0.0
        if baseline.confidence_std < 0.01:
            return abs(current_approval - baseline.approval_rate)
        return abs(current_approval - baseline.approval_rate) / max(baseline.confidence_std, 0.01)

    def compute_latency_deviation(self, agent_name: str, current_latency: float) -> float:
        baseline = self.get_baseline(agent_name)
        if baseline is None or baseline.sample_count < 3 or baseline.latency_p50_ms <= 0:
            return 0.0
        return current_latency / max(baseline.latency_p50_ms, 0.1)

    def reset(self) -> None:
        with self._lock:
            self._baselines.clear()

    def reset_agent(self, agent_name: str) -> None:
        with self._lock:
            self._baselines.pop(agent_name, None)

    @staticmethod
    def _ema(prev: float, current: float, alpha: float) -> float:
        return alpha * current + (1 - alpha) * prev

    @property
    def agent_count(self) -> int:
        with self._lock:
            return len(self._baselines)
