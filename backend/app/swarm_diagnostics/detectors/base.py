"""
BaseDetector — Abstract base for all swarm anomaly detectors.

Each detector implements analyze() which receives the current event
window and returns a list of AnomalySignal if thresholds are breached.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal
from app.swarm_diagnostics.pipeline.metrics import SwarmMetricsCollector


class BaseDetector(ABC):
    """Override name, analyze(), and optionally reset()."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def analyze(
        self,
        events: list[DiagnosticEvent],
        *,
        metrics: SwarmMetricsCollector | None = None,
    ) -> list[AnomalySignal]:
        ...

    def reset(self) -> None:
        pass
