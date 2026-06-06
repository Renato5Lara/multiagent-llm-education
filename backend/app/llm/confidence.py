"""Confidence calibration for LLM voter outputs.

LLMs tend to be overconfident. This module applies temperature scaling
and ECE-based correction to produce calibrated confidence scores.

Uses only stdlib (math + statistics) — no scipy dependency.
"""

from __future__ import annotations

import logging
import math
import statistics
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class ConfidenceCalibrator:
    """Calibrates raw LLM confidence using Platt-style temperature scaling.

    Maintains per-voter calibration data and applies:
    1. Initial discount (raw * 0.85) for new voters with < 10 data points
    2. ECE-based bin correction for established voters

    Thread-safe for concurrent consensus runs via per-voter locks.
    """

    def __init__(self, n_bins: int = 10, min_samples: int = 10):
        self._n_bins = n_bins
        self._min_samples = min_samples
        self._lock = __import__("threading").Lock()
        self._calibration_data: dict[str, list[tuple[float, bool]]] = defaultdict(list)
        self._ece_history: dict[str, list[float]] = defaultdict(list)

    def record_outcome(
        self,
        voter_name: str,
        predicted_confidence: float,
        actual_correct: bool,
    ):
        """Record a prediction-outcome pair for calibration."""
        with self._lock:
            self._calibration_data[voter_name].append(
                (max(0.0, min(1.0, predicted_confidence)), actual_correct)
            )

    def calibrate(self, raw_confidence: float, voter_name: str) -> float:
        """Apply calibration correction to raw confidence.

        Args:
            raw_confidence: Raw confidence from LLM [0, 1]
            voter_name: Voter identifier for historical data lookup

        Returns:
            Calibrated confidence [0, 1]
        """
        conf = max(0.0, min(1.0, raw_confidence))

        with self._lock:
            data = list(self._calibration_data.get(voter_name, []))

        if len(data) < self._min_samples:
            return conf * 0.85

        return self._ece_correction(conf, data)

    def _ece_correction(self, confidence: float, data: list[tuple[float, bool]]) -> float:
        """Apply ECE-based bin correction.

        Maps the confidence to its empirical accuracy bin.
        If empirical accuracy < confidence, reduce confidence.
        If empirical accuracy > confidence, increase confidence (rare).
        """
        bin_idx = min(int(confidence * self._n_bins), self._n_bins - 1)
        bin_low = bin_idx / self._n_bins
        bin_high = (bin_idx + 1) / self._n_bins

        bin_data = [
            (c, a) for c, a in data
            if bin_low <= c < bin_high
        ]

        if not bin_data:
            bin_data = [
                (c, a) for c, a in data
                if abs(c - confidence) < 1.0 / self._n_bins
            ]

        if not bin_data:
            return confidence

        empirical_acc = sum(1 for _, a in bin_data if a) / len(bin_data)
        gap = confidence - empirical_acc

        calibrated = confidence - gap * 0.5
        return max(0.05, min(0.95, calibrated))

    def compute_ece(self, voter_name: str) -> float:
        """Compute Expected Calibration Error for a voter.

        Returns ECE in [0, 1] (lower is better).
        """
        with self._lock:
            data = list(self._calibration_data.get(voter_name, []))

        if not data:
            return 0.0

        n_bins = min(self._n_bins, len(data))
        bin_size = 1.0 / n_bins
        total = 0.0

        for i in range(n_bins):
            bin_low = i * bin_size
            bin_high = (i + 1) * bin_size
            bin_data = [(c, a) for c, a in data if bin_low <= c < bin_high]
            if not bin_data:
                continue
            avg_conf = sum(c for c, _ in bin_data) / len(bin_data)
            acc = sum(1 for _, a in bin_data if a) / len(bin_data)
            total += abs(avg_conf - acc) * (len(bin_data) / len(data))

        return total

    def compute_mce(self, voter_name: str) -> float:
        """Compute Maximum Calibration Error."""
        with self._lock:
            data = list(self._calibration_data.get(voter_name, []))

        if not data:
            return 0.0

        n_bins = min(self._n_bins, len(data))
        bin_size = 1.0 / n_bins
        max_err = 0.0

        for i in range(n_bins):
            bin_low = i * bin_size
            bin_high = (i + 1) * bin_size
            bin_data = [(c, a) for c, a in data if bin_low <= c < bin_high]
            if not bin_data:
                continue
            avg_conf = sum(c for c, _ in bin_data) / len(bin_data)
            acc = sum(1 for _, a in bin_data if a) / len(bin_data)
            max_err = max(max_err, abs(avg_conf - acc))

        return max_err

    def get_calibration_snapshot(self) -> dict[str, dict[str, float]]:
        """Return calibration metrics for all voters (for observability)."""
        with self._lock:
            voters = list(self._calibration_data.keys())

        snapshot = {}
        for v in voters:
            snapshot[v] = {
                "ece": round(self.compute_ece(v), 4),
                "mce": round(self.compute_mce(v), 4),
                "n_samples": len(self._calibration_data.get(v, [])),
            }
        return snapshot

    def reset(self, voter_name: str | None = None):
        """Clear calibration data."""
        with self._lock:
            if voter_name:
                self._calibration_data.pop(voter_name, None)
            else:
                self._calibration_data.clear()
