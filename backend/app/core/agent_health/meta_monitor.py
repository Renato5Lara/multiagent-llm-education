from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal


@dataclass
class AnomalyOutcome:
    signal_id: str
    detector_name: str
    action_taken: bool
    health_improved: bool
    timestamp: float = field(default_factory=time.time)


@dataclass
class Intervention:
    action: str
    agent: str
    timestamp: float = field(default_factory=time.time)
    outcome: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "agent": self.agent,
            "timestamp": self.timestamp,
            "outcome": self.outcome,
        }


@dataclass
class MetaMonitorReport:
    false_positive_rate: float = 0.0
    false_positives_by_detector: dict[str, int] = field(default_factory=dict)
    overhead_ms: float = 0.0
    sampling_rate: float = 1.0
    amplification_risk: str = "none"
    amplification_loops_detected: int = 0
    total_interventions: int = 0
    disabled_detectors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "false_positive_rate": round(self.false_positive_rate, 4),
            "false_positives_by_detector": self.false_positives_by_detector,
            "overhead_ms": round(self.overhead_ms, 2),
            "sampling_rate": self.sampling_rate,
            "amplification_risk": self.amplification_risk,
            "amplification_loops_detected": self.amplification_loops_detected,
            "total_interventions": self.total_interventions,
            "disabled_detectors": self.disabled_detectors,
        }


class FalsePositiveTracker:
    def __init__(self, fp_threshold: float = 0.2, tracking_window: int = 100) -> None:
        self._fp_threshold = fp_threshold
        self._tracking_window = tracking_window
        self._outcomes: deque[AnomalyOutcome] = deque(maxlen=tracking_window)
        self._fp_counts: dict[str, int] = {}
        self._total_counts: dict[str, int] = {}
        self._disabled: set[str] = set()
        self._lock = Lock()

    def record_outcome(self, outcome: AnomalyOutcome) -> None:
        with self._lock:
            self._outcomes.append(outcome)
            detector = outcome.detector_name
            self._total_counts[detector] = self._total_counts.get(detector, 0) + 1
            if not outcome.health_improved and outcome.action_taken:
                self._fp_counts[detector] = self._fp_counts.get(detector, 0) + 1
            self._check_detector_fp_rate(detector)

    def _check_detector_fp_rate(self, detector: str) -> None:
        total = self._total_counts.get(detector, 0)
        fps = self._fp_counts.get(detector, 0)
        if total >= 10:
            rate = fps / total
            if rate > self._fp_threshold:
                self._disabled.add(detector)
            else:
                self._disabled.discard(detector)

    def is_disabled(self, detector_name: str) -> bool:
        with self._lock:
            return detector_name in self._disabled

    def get_fp_rate(self, detector_name: str) -> float:
        with self._lock:
            total = self._total_counts.get(detector_name, 0)
            if total == 0:
                return 0.0
            return self._fp_counts.get(detector_name, 0) / total

    def get_all_fp_rates(self) -> dict[str, float]:
        with self._lock:
            return {d: self.get_fp_rate(d) for d in self._total_counts}

    def reset(self) -> None:
        with self._lock:
            self._outcomes.clear()
            self._fp_counts.clear()
            self._total_counts.clear()
            self._disabled.clear()


class AdaptiveSampler:
    def __init__(
        self,
        max_rate: float = 1.0,
        min_rate: float = 0.1,
        reduction_factor: float = 0.8,
        increase_factor: float = 1.5,
        overhead_threshold_ms: float = 50.0,
    ) -> None:
        self._sampling_rate = max_rate
        self._max_rate = max_rate
        self._min_rate = min_rate
        self._reduction_factor = reduction_factor
        self._increase_factor = increase_factor
        self._overhead_threshold_ms = overhead_threshold_ms
        self._healthy_window = 0
        self._lock = Lock()

    def adjust(self, health_status: str, overhead_ms: float) -> float:
        with self._lock:
            if health_status in ("degraded", "critical"):
                self._sampling_rate = min(self._max_rate, self._sampling_rate * self._increase_factor)
                self._healthy_window = 0
            elif overhead_ms > self._overhead_threshold_ms:
                self._sampling_rate = max(self._min_rate, self._sampling_rate * self._reduction_factor)
                self._healthy_window = 0
            else:
                self._healthy_window += 1
                if self._healthy_window > 5 and self._sampling_rate > self._min_rate:
                    self._sampling_rate = max(self._min_rate, self._sampling_rate * self._reduction_factor)
            return self._sampling_rate

    def should_sample(self) -> bool:
        with self._lock:
            return hash(str(time.time())) % 1000 < self._sampling_rate * 1000

    @property
    def sampling_rate(self) -> float:
        with self._lock:
            return self._sampling_rate

    def reset(self) -> None:
        with self._lock:
            self._sampling_rate = self._max_rate
            self._healthy_window = 0


class FeedbackAmplificationDetector:
    def __init__(
        self,
        cascade_threshold: int = 3,
        time_window_seconds: float = 60.0,
        max_interventions_per_window: int = 5,
    ) -> None:
        self._cascade_threshold = cascade_threshold
        self._time_window_seconds = time_window_seconds
        self._max_interventions_per_window = max_interventions_per_window
        self._intervention_log: deque[Intervention] = deque(maxlen=200)
        self._lock = Lock()
        self._loop_count = 0

    def record_intervention(self, intervention: Intervention) -> None:
        with self._lock:
            self._intervention_log.append(intervention)

    def detect_amplification(self) -> tuple[str, int]:
        with self._lock:
            now = time.time()
            cutoff = now - self._time_window_seconds
            recent = [i for i in self._intervention_log if i.timestamp >= cutoff]

            if len(recent) < self._cascade_threshold:
                return "none", 0

            agents_involved = len(set(i.agent for i in recent))
            same_agent_count = sum(
                1 for i in recent if i.agent == recent[-1].agent
            )

            if agents_involved >= self._cascade_threshold and len(recent) >= self._cascade_threshold * 2:
                self._loop_count += 1
                return "cascading", self._loop_count

            if same_agent_count >= self._cascade_threshold:
                self._loop_count += 1
                return "repeated_intervention", self._loop_count

            return "none", self._loop_count

    def reset(self) -> None:
        with self._lock:
            self._intervention_log.clear()
            self._loop_count = 0


class MetaMonitor:
    def __init__(
        self,
        fp_threshold: float = 0.2,
        cascade_threshold: int = 3,
        overhead_threshold_ms: float = 50.0,
    ) -> None:
        self.false_positive_tracker = FalsePositiveTracker(fp_threshold=fp_threshold)
        self.adaptive_sampler = AdaptiveSampler(overhead_threshold_ms=overhead_threshold_ms)
        self.feedback_detector = FeedbackAmplificationDetector(
            cascade_threshold=cascade_threshold,
        )
        self._cycle_times: deque[float] = deque(maxlen=100)
        self._lock = Lock()

    def record_cycle_time(self, duration_ms: float) -> None:
        with self._lock:
            self._cycle_times.append(duration_ms)

    @property
    def avg_cycle_time_ms(self) -> float:
        with self._lock:
            if not self._cycle_times:
                return 0.0
            return sum(self._cycle_times) / len(self._cycle_times)

    def get_report(self) -> MetaMonitorReport:
        fp_rate = 0.0
        fp_by_detector = {}
        total_fp = 0
        total_outcomes = 0
        for detector, count in self.false_positive_tracker._fp_counts.items():
            fp_by_detector[detector] = count
            total_fp += count
        for detector, count in self.false_positive_tracker._total_counts.items():
            total_outcomes += count
        if total_outcomes > 0:
            fp_rate = total_fp / total_outcomes

        amplification_risk, loops = self.feedback_detector.detect_amplification()

        return MetaMonitorReport(
            false_positive_rate=fp_rate,
            false_positives_by_detector=fp_by_detector,
            overhead_ms=self.avg_cycle_time_ms,
            sampling_rate=self.adaptive_sampler.sampling_rate,
            amplification_risk=amplification_risk,
            amplification_loops_detected=loops,
            total_interventions=total_outcomes,
            disabled_detectors=list(self.false_positive_tracker._disabled),
        )

    def reset(self) -> None:
        self.false_positive_tracker.reset()
        self.adaptive_sampler.reset()
        self.feedback_detector.reset()
        with self._lock:
            self._cycle_times.clear()
