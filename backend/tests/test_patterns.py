"""
Tests for Pattern Detection — PatternDetector, PatternSignal.

Covers:
    - Trend detection (up/down)
    - Contradiction detection
    - Improvement detection
    - Degradation detection
    - Consistency detection
    - detect_all combined
    - Edge cases (empty, single record, flat trend)
    - Determinism (same inputs → same outputs)
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.memory.patterns import (
    PatternDetector,
    PatternSignal,
    PATTERN_TREND,
    PATTERN_CONTRADICTION,
    PATTERN_IMPROVEMENT,
    PATTERN_DEGRADATION,
    PATTERN_CONSISTENCY,
)
from app.models.shared_memory_record import SharedMemoryRecord


def _record(confidence=1.0, key="test:key", value=None, voter_name="v1",
            created_at=None, memory_type="observation"):
    if created_at is None:
        created_at = datetime.now(timezone.utc)
    if value is None:
        value = {"score": 0.5}
    return SharedMemoryRecord(
        voter_name=voter_name,
        memory_type=memory_type,
        key=key,
        value=value,
        confidence=confidence,
        created_at=created_at,
    )


class TestTrendDetection:
    def test_empty_records(self):
        d = PatternDetector()
        assert d.detect_trend([]) == []

    def test_single_record(self):
        d = PatternDetector()
        r = _record(confidence=0.5)
        assert d.detect_trend([r]) == []

    def test_upward_trend_confidence(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.3, created_at=now - timedelta(hours=4)),
            _record(confidence=0.5, created_at=now - timedelta(hours=2)),
            _record(confidence=0.9, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_trend(records, window=3)
        assert len(signals) >= 1
        assert signals[0].pattern_type == PATTERN_TREND
        assert signals[0].metadata["direction"] == "up"
        assert signals[0].strength > 0

    def test_downward_trend_confidence(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.9, created_at=now - timedelta(hours=4)),
            _record(confidence=0.6, created_at=now - timedelta(hours=2)),
            _record(confidence=0.2, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_trend(records, window=3)
        assert len(signals) >= 1
        assert signals[0].metadata["direction"] == "down"

    def test_trend_value_key(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 10}, created_at=now - timedelta(hours=4)),
            _record(value={"score": 20}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 30}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_trend(records, value_key="score", window=3)
        assert len(signals) >= 1

    def test_flat_no_trend(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.5, created_at=now - timedelta(hours=4)),
            _record(confidence=0.5, created_at=now - timedelta(hours=2)),
            _record(confidence=0.5, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_trend(records, window=3)
        assert len(signals) == 0

    def test_trend_with_gap(self):
        """Even with gaps in values, trend should detect if enough points."""
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.2, created_at=now - timedelta(hours=6)),
            _record(confidence=0.4, created_at=now - timedelta(hours=4)),
            _record(confidence=0.6, created_at=now - timedelta(hours=2)),
            _record(confidence=0.9, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_trend(records, window=3)
        assert len(signals) >= 1


class TestContradictionDetection:
    def test_no_contradiction_single(self):
        d = PatternDetector()
        r = _record(value={"color": "red"})
        assert d.detect_contradictions([r]) == []

    def test_no_contradiction_agreement(self):
        d = PatternDetector()
        r1 = _record(value={"color": "red"}, voter_name="v1")
        r2 = _record(value={"color": "red"}, voter_name="v2")
        signals = d.detect_contradictions([r1, r2])
        assert len(signals) == 0

    def test_contradiction_detected(self):
        d = PatternDetector()
        r1 = _record(key="color", value={"color": "red"}, voter_name="v1")
        r2 = _record(key="color", value={"color": "blue"}, voter_name="v2")
        signals = d.detect_contradictions([r1, r2])
        assert len(signals) >= 1
        assert signals[0].pattern_type == PATTERN_CONTRADICTION
        assert signals[0].metadata["key"] == "color"
        assert signals[0].metadata["unique_values"] >= 2

    def test_contradiction_strength(self):
        d = PatternDetector()
        records = [
            _record(key="k", value={"v": "a"}, voter_name="v1"),
            _record(key="k", value={"v": "b"}, voter_name="v2"),
            _record(key="k", value={"v": "c"}, voter_name="v3"),
            _record(key="k", value={"v": "d"}, voter_name="v4"),
        ]
        signals = d.detect_contradictions(records)
        assert len(signals) >= 1
        assert signals[0].strength > 0


class TestImprovementDetection:
    def test_empty(self):
        d = PatternDetector()
        assert d.detect_improvement([]) == []

    def test_single(self):
        d = PatternDetector()
        assert d.detect_improvement([_record()]) == []

    def test_improvement_detected(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 0.3}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 0.9}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_improvement(records, threshold=0.1)
        assert len(signals) >= 1
        assert signals[0].pattern_type == PATTERN_IMPROVEMENT
        assert signals[0].metadata["relative_change"] > 0

    def test_no_improvement(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 0.5}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 0.52}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_improvement(records, threshold=0.5)
        assert len(signals) == 0

    def test_improvement_default_key(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 0.2}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 0.8}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_improvement(records)
        assert len(signals) >= 1


class TestDegradationDetection:
    def test_degradation_detected(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 0.9}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 0.2}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_degradation(records, threshold=0.1)
        assert len(signals) >= 1
        assert signals[0].pattern_type == PATTERN_DEGRADATION
        assert signals[0].metadata["relative_change"] < 0

    def test_degradation_from_zero(self):
        """Degradation from zero should return empty (division by zero guard)."""
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(value={"score": 0}, created_at=now - timedelta(hours=2)),
            _record(value={"score": 0.5}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_degradation(records)
        assert len(signals) == 0


class TestConsistencyDetection:
    def test_empty(self):
        d = PatternDetector()
        assert d.detect_consistency([]) == []

    def test_single(self):
        d = PatternDetector()
        assert d.detect_consistency([_record()]) == []

    def test_high_consistency(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.5, created_at=now - timedelta(hours=3)),
            _record(confidence=0.51, created_at=now - timedelta(hours=2)),
            _record(confidence=0.49, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_consistency(records, tolerance=0.1)
        assert len(signals) >= 1
        assert signals[0].pattern_type == PATTERN_CONSISTENCY
        assert signals[0].strength > 0

    def test_low_consistency(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(confidence=0.1, created_at=now - timedelta(hours=3)),
            _record(confidence=0.9, created_at=now - timedelta(hours=2)),
            _record(confidence=0.2, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_consistency(records, tolerance=0.1)
        assert len(signals) == 0


class TestDetectAll:
    def test_runs_all_detectors(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(key="k1", value={"score": 0.3}, voter_name="v1",
                    created_at=now - timedelta(hours=3)),
            _record(key="k1", value={"score": 0.7}, voter_name="v1",
                    created_at=now - timedelta(hours=2)),
            _record(key="k1", value={"score": 0.9}, voter_name="v1",
                    created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_all(records)
        # Should find improvement at minimum
        assert any(s.pattern_type == PATTERN_IMPROVEMENT for s in signals)

    def test_detect_all_empty(self):
        d = PatternDetector()
        assert d.detect_all([]) == []

    def test_detect_all_dedup(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        # Create records that would trigger multiple similar patterns
        records = [
            _record(key="k1", value={"score": 0.2}, created_at=now - timedelta(hours=4)),
            _record(key="k1", value={"score": 0.4}, created_at=now - timedelta(hours=3)),
            _record(key="k1", value={"score": 0.6}, created_at=now - timedelta(hours=2)),
            _record(key="k1", value={"score": 0.8}, created_at=now - timedelta(hours=1)),
        ]
        signals = d.detect_all(records)
        # Should have exactly 1 improvement signal (deduped) + maybe other patterns
        improvement_signals = [s for s in signals if s.pattern_type == PATTERN_IMPROVEMENT]
        assert len(improvement_signals) == 1

    def test_deterministic(self):
        d = PatternDetector()
        now = datetime.now(timezone.utc)
        records = [
            _record(key="k", value={"score": 0.3}, created_at=now - timedelta(hours=2)),
            _record(key="k", value={"score": 0.8}, created_at=now - timedelta(hours=1)),
        ]
        s1 = d.detect_all(records)
        s2 = d.detect_all(records)
        assert len(s1) == len(s2)
        for a, b in zip(s1, s2):
            assert a.pattern_type == b.pattern_type
            assert a.strength == b.strength


class TestPatternSignal:
    def test_defaults(self):
        s = PatternSignal(pattern_type="test", strength=0.5, confidence=0.8)
        assert s.description == ""
        assert s.metadata == {}
        assert s.evidence == []

    def test_equality_not_required(self):
        s1 = PatternSignal("t", 0.5, 0.8)
        s2 = PatternSignal("t", 0.5, 0.8)
        # PatternSignals are not compared by value (no __eq__ needed)
        assert s1.pattern_type == s2.pattern_type
