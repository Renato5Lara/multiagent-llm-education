"""
Pattern Detection — Longitudinal pattern detection in shared memory.

Detects trends, contradictions, improvements, degradations, and
consistency signals from accumulated collective memory. All
detection is deterministic and explainable.

Each detector returns a list of PatternSignal objects that describe
what was found, how strong the evidence is, and which records
support the conclusion.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ── Pattern Types ────────────────────────────────────────────────

PATTERN_TREND = "trend"
PATTERN_CONTRADICTION = "contradiction"
PATTERN_IMPROVEMENT = "improvement"
PATTERN_DEGRADATION = "degradation"
PATTERN_CONSISTENCY = "consistency"
PATTERN_CYCLICAL = "cyclical"


@dataclass
class PatternSignal:
    """A detected pattern in collective memory.

    Attributes:
        pattern_type: One of PATTERN_* constants.
        strength: Signal strength in [0, 1] (1 = strongest).
        confidence: How confident we are in the detection.
        evidence: List of supporting record objects.
        description: Human-readable description.
        metadata: Additional context (values, slopes, etc.).
    """

    pattern_type: str
    strength: float
    confidence: float
    evidence: list = field(default_factory=list)
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Pattern Detector ─────────────────────────────────────────────


class PatternDetector:
    """Deterministic pattern detection on shared memory records.

    All methods are pure functions that take record lists and return
    PatternSignal lists. No state is mutated.

    Usage:
        detector = PatternDetector()
        signals = detector.detect_all(records)
        for s in signals:
            print(f"{s.pattern_type}: {s.description}")
    """

    # ── Trend Detection ─────────────────────────────────────────

    def detect_trend(
        self,
        records: list,
        value_key: str | None = None,
        window: int = 3,
    ) -> list[PatternSignal]:
        """Detect monotonic trends in a sequence of records.

        Looks for consecutive increases or decreases in confidence
        or a specific value_key within the value JSON.

        Args:
            records: Chronologically ordered records (oldest first).
            value_key: If set, extract numeric value from record.value[value_key].
                       If None, use record.confidence.
            window: Number of consecutive points needed to confirm a trend.

        Returns:
            List of PatternSignal (trend_up or trend_down).
        """
        if len(records) < window:
            return []

        sorted_recs = sorted(records, key=lambda r: r.created_at)
        values = []
        for r in sorted_recs:
            if value_key is not None:
                val = r.value.get(value_key) if isinstance(r.value, dict) else None
            else:
                val = r.confidence
            if val is not None and isinstance(val, (int, float)):
                values.append(val)

        if len(values) < window:
            return []

        signals: list[PatternSignal] = []

        # Upward trend
        up_count = 0
        for i in range(1, len(values)):
            if values[i] > values[i - 1]:
                up_count += 1
            else:
                up_count = 0
            if up_count >= window - 1:
                # Confirmed
                segment = sorted_recs[i - window + 1 : i + 1]
                slope = (values[i] - values[i - window + 1]) / max(window - 1, 1)
                strength = min(1.0, slope * 5.0)  # normalize
                signals.append(PatternSignal(
                    pattern_type=PATTERN_TREND,
                    strength=max(0.0, strength),
                    confidence=0.5 + 0.5 * (up_count / len(values)),
                    evidence=list(segment),
                    description=f"Upward trend detected over {window} records "
                                f"(slope={slope:.4f})",
                    metadata={"direction": "up", "slope": slope, "window": window},
                ))
                break

        # Downward trend
        down_count = 0
        for i in range(1, len(values)):
            if values[i] < values[i - 1]:
                down_count += 1
            else:
                down_count = 0
            if down_count >= window - 1:
                segment = sorted_recs[i - window + 1 : i + 1]
                slope = (values[i - window + 1] - values[i]) / max(window - 1, 1)
                strength = min(1.0, slope * 5.0)
                signals.append(PatternSignal(
                    pattern_type=PATTERN_TREND,
                    strength=max(0.0, strength),
                    confidence=0.5 + 0.5 * (down_count / len(values)),
                    evidence=list(segment),
                    description=f"Downward trend detected over {window} records "
                                f"(slope={slope:.4f})",
                    metadata={"direction": "down", "slope": slope, "window": window},
                ))
                break

        return signals

    # ── Contradiction Detection ─────────────────────────────────

    def detect_contradictions(
        self,
        records: list,
    ) -> list[PatternSignal]:
        """Detect contradictions where different voters disagree.

        Groups records by key and looks for conflicting values.

        Args:
            records: List of records to analyze.

        Returns:
            List of PatternSignal with type=contradiction.
        """
        from collections import defaultdict

        signals: list[PatternSignal] = []

        # Group by key
        by_key: dict[str, list] = defaultdict(list)
        for r in records:
            by_key[r.key].append(r)

        for key, group in by_key.items():
            if len(group) < 2:
                continue

            # Check for value disagreement
            unique_values = set()
            for r in group:
                v = r.value
                if isinstance(v, dict):
                    unique_values.add(
                        tuple(sorted(v.items()))
                    )
                else:
                    unique_values.add(str(v))

            if len(unique_values) >= 2:
                # Contradiction found
                avg_conf = sum(r.confidence for r in group) / len(group)
                # Stronger contradiction when more unique values
                strength = min(1.0, len(unique_values) / 5.0)
                signals.append(PatternSignal(
                    pattern_type=PATTERN_CONTRADICTION,
                    strength=strength,
                    confidence=avg_conf,
                    evidence=list(group),
                    description=f"Contradiction on '{key}': "
                                f"{len(unique_values)} distinct values from "
                                f"{len(group)} records",
                    metadata={
                        "key": key,
                        "unique_values": len(unique_values),
                        "total_records": len(group),
                    },
                ))

        return signals

    # ── Improvement / Degradation Detection ─────────────────────

    def detect_improvement(
        self,
        records: list,
        value_key: str = "score",
        threshold: float = 0.1,
    ) -> list[PatternSignal]:
        """Detect improvement patterns (significant positive changes).

        Compares first vs last values in a sequence.

        Args:
            records: Chronologically ordered records.
            value_key: Key in record.value dict to extract.
            threshold: Minimum relative improvement to qualify.

        Returns:
            List of PatternSignal.
        """
        return self._detect_change(
            records, value_key, threshold, direction="up",
            pattern_type=PATTERN_IMPROVEMENT,
            desc_prefix="Improvement",
        )

    def detect_degradation(
        self,
        records: list,
        value_key: str = "score",
        threshold: float = 0.1,
    ) -> list[PatternSignal]:
        """Detect degradation patterns (significant negative changes)."""
        return self._detect_change(
            records, value_key, threshold, direction="down",
            pattern_type=PATTERN_DEGRADATION,
            desc_prefix="Degradation",
        )

    def _detect_change(
        self,
        records: list,
        value_key: str,
        threshold: float,
        direction: str,
        pattern_type: str,
        desc_prefix: str,
    ) -> list[PatternSignal]:
        if len(records) < 2:
            return []

        sorted_recs = sorted(records, key=lambda r: r.created_at)
        values = []
        for r in sorted_recs:
            val = r.value.get(value_key) if isinstance(r.value, dict) else None
            if val is not None and isinstance(val, (int, float)):
                values.append(val)

        if len(values) < 2:
            return []

        first = values[0]
        last = values[-1]
        if first == 0:
            return []

        change = (last - first) / abs(first)

        if direction == "up" and change >= threshold:
            strength = min(1.0, change / 2.0)
            return [PatternSignal(
                pattern_type=pattern_type,
                strength=strength,
                confidence=min(1.0, 0.5 + strength * 0.5),
                evidence=list(sorted_recs),
                description=f"{desc_prefix} from {first:.3f} to {last:.3f} "
                            f"(change={change:+.1%})",
                metadata={
                    "first_value": first,
                    "last_value": last,
                    "relative_change": change,
                },
            )]
        elif direction == "down" and change <= -threshold:
            strength = min(1.0, abs(change) / 2.0)
            return [PatternSignal(
                pattern_type=pattern_type,
                strength=strength,
                confidence=min(1.0, 0.5 + strength * 0.5),
                evidence=list(sorted_recs),
                description=f"{desc_prefix} from {first:.3f} to {last:.3f} "
                            f"(change={change:+.1%})",
                metadata={
                    "first_value": first,
                    "last_value": last,
                    "relative_change": change,
                },
            )]

        return []

    # ── Consistency Detection ───────────────────────────────────

    def detect_consistency(
        self,
        records: list,
        tolerance: float = 0.1,
    ) -> list[PatternSignal]:
        """Detect high consistency (low variance in values).

        Args:
            records: List of records.
            tolerance: Max relative std dev to qualify as consistent.

        Returns:
            List of PatternSignal.
        """
        if len(records) < 2:
            return []

        sorted_recs = sorted(records, key=lambda r: r.created_at)
        values = [r.confidence for r in sorted_recs]

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        rel_std = std_dev / max(mean, 0.001)

        if rel_std <= tolerance:
            strength = max(0.0, 1.0 - rel_std / tolerance)
            return [PatternSignal(
                pattern_type=PATTERN_CONSISTENCY,
                strength=min(1.0, strength),
                confidence=0.5 + 0.5 * (1.0 - rel_std),
                evidence=list(sorted_recs),
                description=f"High consistency: std={std_dev:.4f}, "
                            f"rel_std={rel_std:.2%}",
                metadata={
                    "mean": mean,
                    "std_dev": std_dev,
                    "relative_std": rel_std,
                    "num_records": len(records),
                },
            )]

        return []

    # ── Run All Detectors ───────────────────────────────────────

    def detect_all(
        self,
        records: list,
    ) -> list[PatternSignal]:
        """Run all pattern detectors on the given records.

        Args:
            records: List of SharedMemoryRecord.

        Returns:
            Combined, deduplicated list of PatternSignal.
        """
        signals: list[PatternSignal] = []

        signals.extend(self.detect_trend(records))
        signals.extend(self.detect_contradictions(records))
        signals.extend(self.detect_improvement(records))
        signals.extend(self.detect_degradation(records))
        signals.extend(self.detect_consistency(records))

        # Deduplicate: keep the strongest signal per (type, key/description)
        seen: set[tuple[str, str]] = set()
        deduped: list[PatternSignal] = []
        for s in sorted(signals, key=lambda x: x.strength, reverse=True):
            dedup_key = (s.pattern_type, s.metadata.get("key", s.description[:50]))
            if dedup_key not in seen:
                seen.add(dedup_key)
                deduped.append(s)

        return deduped
