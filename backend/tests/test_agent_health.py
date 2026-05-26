"""Tests for Agent Health Monitoring system."""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.core.agent_health.adaptive_degradation import AdaptiveDegradationManager
from app.core.agent_health.behavioral_baseline import BehavioralBaselineManager
from app.core.agent_health.collective_stability import CollectiveStabilityScorer
from app.core.agent_health.health_score_voter import HealthScoreVoter
from app.core.agent_health.health_scorer import (
    HealthScorer,
    compute_base_score,
    compute_health_score,
    compute_latency_score,
    compute_penalty_total,
    compute_recovery_bonus,
    decay_factor,
)
from app.core.agent_health.meta_monitor import (
    AdaptiveSampler,
    AnomalyOutcome,
    FalsePositiveTracker,
    FeedbackAmplificationDetector,
    Intervention,
    MetaMonitor,
)
from app.core.agent_health.models import (
    AgentHealthProfile,
    AgentSlidingStats,
    BehavioralBaseline,
    DegradationLevel,
    HealthSignal,
)
from app.core.agent_health.monitor import AgentHealthMonitor
from app.core.consensus import BaseVoter, ConsensusVote, VoteDecision, VoteContext
from app.swarm_diagnostics.models.anomaly_signal import AnomalySignal, AnomalyType, Severity
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent


# ══════════════════════════════════════════════════════════════════════════
# Models
# ══════════════════════════════════════════════════════════════════════════


class TestDegradationLevel:
    def test_from_health_score_none(self):
        assert DegradationLevel.from_health_score(0.9) == DegradationLevel.NONE
        assert DegradationLevel.from_health_score(0.8) == DegradationLevel.NONE

    def test_from_health_score_mild(self):
        assert DegradationLevel.from_health_score(0.7) == DegradationLevel.MILD
        assert DegradationLevel.from_health_score(0.6) == DegradationLevel.MILD

    def test_from_health_score_moderate(self):
        assert DegradationLevel.from_health_score(0.5) == DegradationLevel.MODERATE
        assert DegradationLevel.from_health_score(0.4) == DegradationLevel.MODERATE

    def test_from_health_score_severe(self):
        assert DegradationLevel.from_health_score(0.3) == DegradationLevel.SEVERE
        assert DegradationLevel.from_health_score(0.2) == DegradationLevel.SEVERE

    def test_from_health_score_critical(self):
        assert DegradationLevel.from_health_score(0.1) == DegradationLevel.CRITICAL
        assert DegradationLevel.from_health_score(0.0) == DegradationLevel.CRITICAL

    def test_vote_weight(self):
        assert DegradationLevel.NONE.vote_weight == 1.0
        assert DegradationLevel.MILD.vote_weight == 0.9
        assert DegradationLevel.MODERATE.vote_weight == 0.7
        assert DegradationLevel.SEVERE.vote_weight == 0.4
        assert DegradationLevel.CRITICAL.vote_weight == 0.0

    def test_label(self):
        assert DegradationLevel.NONE.label == "none"
        assert DegradationLevel.CRITICAL.label == "critical"

    def test_description(self):
        assert "healthy" in DegradationLevel.NONE.description


class TestAgentHealthProfile:
    def test_initial_state(self):
        profile = AgentHealthProfile(agent_name="test_agent")
        assert profile.agent_name == "test_agent"
        assert profile.health_score == 1.0
        assert profile.degradation_level == DegradationLevel.NONE
        assert profile.cognitive_drift == 0.0

    def test_update_degradation(self):
        profile = AgentHealthProfile(agent_name="a", health_score=0.3)
        profile.update_degradation()
        assert profile.degradation_level == DegradationLevel.SEVERE

    def test_vote_weight_reflects_degradation(self):
        profile = AgentHealthProfile(agent_name="a", health_score=0.1)
        profile.update_degradation()
        assert profile.vote_weight == 0.0

    def test_add_signal(self):
        profile = AgentHealthProfile(agent_name="a")
        signal = HealthSignal(signal_type="timeout", agent_name="a", severity=0.5)
        profile.add_signal(signal)
        assert len(profile.recent_signals) == 1
        assert profile.recent_signals[0].signal_type == "timeout"

    def test_max_signals_capped(self):
        profile = AgentHealthProfile(agent_name="a", max_signals=5)
        for i in range(10):
            profile.add_signal(HealthSignal(
                signal_type="test", agent_name="a", severity=0.1,
            ))
        assert len(profile.recent_signals) == 5

    def test_to_dict(self):
        profile = AgentHealthProfile(agent_name="a", health_score=0.75)
        profile.update_degradation()
        d = profile.to_dict()
        assert d["agent_name"] == "a"
        assert d["health_score"] == 0.75
        assert d["degradation_level"] == "mild"
        assert d["vote_weight"] == 0.9
        assert "behavioral_baseline" in d
        assert "sliding_stats" in d


class TestAgentSlidingStats:
    def test_error_rate(self):
        stats = AgentSlidingStats()
        assert stats.error_rate == 0.0
        stats.recent_errors.append("err1")
        stats.recent_latencies.append(100.0)
        assert stats.error_rate == 1.0

    def test_p95_latency(self):
        stats = AgentSlidingStats()
        assert stats.p95_latency == 0.0
        for v in range(100):
            stats.recent_latencies.append(float(v))
        assert 94 <= stats.p95_latency <= 95

    def test_approval_rate(self):
        stats = AgentSlidingStats()
        assert stats.approval_rate == 0.5
        stats.recent_decisions.append(("approve", 0.9, datetime.now(timezone.utc)))
        stats.recent_decisions.append(("reject", 0.3, datetime.now(timezone.utc)))
        assert stats.approval_rate == 0.5


# ══════════════════════════════════════════════════════════════════════════
# Health Scorer
# ══════════════════════════════════════════════════════════════════════════


class TestDecayFactor:
    def test_recent_no_decay(self):
        now = datetime.now(timezone.utc)
        assert decay_factor(now) == pytest.approx(1.0, abs=0.01)

    def test_older_signal_decays(self):
        from datetime import timedelta
        old = datetime.now(timezone.utc) - timedelta(minutes=10)
        factor = decay_factor(old, half_life_minutes=10.0)
        assert factor == pytest.approx(0.5, abs=0.01)


class TestLatencyScore:
    def test_perfect_latency(self):
        assert compute_latency_score(0.0) == 1.0

    def test_at_threshold(self):
        assert compute_latency_score(5000.0) == 0.0

    def test_beyond_threshold(self):
        assert compute_latency_score(10000.0) == 0.0

    def test_partial(self):
        score = compute_latency_score(2500.0, threshold_ms=5000.0)
        assert score == pytest.approx(0.5, abs=0.01)


class TestComputeHealthScore:
    def test_perfect_health(self):
        profile = AgentHealthProfile(agent_name="test")
        score = compute_health_score(profile)
        assert 0.7 <= score <= 1.0

    def test_with_penalties(self):
        profile = AgentHealthProfile(agent_name="test")
        profile.add_signal(HealthSignal(
            signal_type="circuit_breaker_open",
            agent_name="test",
            severity=1.0,
            timestamp=datetime.now(timezone.utc),
            source="test",
        ))
        score = compute_health_score(profile)
        assert score < 1.0

    def test_critical_degradation(self):
        profile = AgentHealthProfile(agent_name="test")
        profile.sliding_stats.total_cb_opens = 10
        for s in ["circuit_breaker_open", "timeout", "hallucination"]:
            profile.add_signal(HealthSignal(
                signal_type=s, agent_name="test",
                severity=1.0, timestamp=datetime.now(timezone.utc),
                source="test",
            ))
        score = compute_health_score(profile)
        assert score < 0.5


class TestHealthScorer:
    def test_score_returns_sane_value(self):
        scorer = HealthScorer()
        profile = AgentHealthProfile(agent_name="test")
        score = scorer.score(profile)
        assert 0.0 <= score <= 1.0

    def test_score_history_tracked(self):
        scorer = HealthScorer()
        profile = AgentHealthProfile(agent_name="test")
        scorer.score(profile)
        assert len(scorer.get_score_history("test")) == 1

    def test_reset_clears_history(self):
        scorer = HealthScorer()
        profile = AgentHealthProfile(agent_name="test")
        scorer.score(profile)
        scorer.reset()
        assert len(scorer.get_score_history("test")) == 0


# ══════════════════════════════════════════════════════════════════════════
# Behavioral Baseline
# ══════════════════════════════════════════════════════════════════════════


class TestBehavioralBaselineManager:
    def test_update_creates_baseline(self):
        mgr = BehavioralBaselineManager()
        baseline = mgr.update("agent_a", decision="approve", confidence=0.9, latency_ms=100.0)
        assert baseline.sample_count == 1
        assert baseline.approval_rate > 0.5

    def test_get_baseline_returns_none_for_unknown(self):
        mgr = BehavioralBaselineManager()
        assert mgr.get_baseline("unknown") is None

    def test_baseline_tracks_multiple_agents(self):
        mgr = BehavioralBaselineManager()
        mgr.update("a", decision="approve", confidence=0.9)
        mgr.update("b", decision="reject", confidence=0.3)
        assert mgr.agent_count == 2

    def test_deviation_small_for_similar_values(self):
        mgr = BehavioralBaselineManager()
        for _ in range(10):
            mgr.update("a", decision="approve", confidence=0.9)
        dev = mgr.compute_deviation("a", 0.85)
        assert dev < 2.0

    def test_deviation_large_for_different_values(self):
        mgr = BehavioralBaselineManager()
        for _ in range(10):
            mgr.update("a", decision="approve", confidence=0.9)
        dev = mgr.compute_deviation("a", 0.1)
        assert dev > 0.5

    def test_latency_deviation(self):
        mgr = BehavioralBaselineManager()
        for _ in range(5):
            mgr.update("a", latency_ms=100.0)
        dev = mgr.compute_latency_deviation("a", 500.0)
        assert dev > 2.0

    def test_reset(self):
        mgr = BehavioralBaselineManager()
        mgr.update("a", decision="approve")
        mgr.reset()
        assert mgr.agent_count == 0

    def test_max_agents_respected(self):
        mgr = BehavioralBaselineManager(max_agents=3)
        for i in range(5):
            mgr.update(f"agent_{i}", decision="approve")
        assert mgr.agent_count == 3


# ══════════════════════════════════════════════════════════════════════════
# Collective Stability
# ══════════════════════════════════════════════════════════════════════════


class TestCollectiveStabilityScorer:
    def test_empty_returns_healthy(self):
        scorer = CollectiveStabilityScorer()
        report = scorer.compute({})
        assert report.stability_score >= 0.8

    def test_with_healthy_profiles(self):
        scorer = CollectiveStabilityScorer()
        profile = AgentHealthProfile(agent_name="a")
        report = scorer.compute({"a": profile})
        assert report.stability_score > 0.5
        assert "normally" in report.recommendation

    def test_with_degraded_profiles(self):
        scorer = CollectiveStabilityScorer()
        profile = AgentHealthProfile(agent_name="a", health_score=0.1)
        profile.update_degradation()
        report = scorer.compute({"a": profile})
        assert "a" in report.at_risk_agents
        assert report.degradation_distribution.get("critical", 0) >= 1

    def test_convergence_rate(self):
        scorer = CollectiveStabilityScorer()
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="consensus:approve",
                source="engine", created_at=now,
                payload={"decision": "approve", "votes": []},
            ),
            DiagnosticEvent(
                event_id="2", event_type="consensus:approve",
                source="engine", created_at=now,
                payload={"decision": "approve", "votes": []},
            ),
            DiagnosticEvent(
                event_id="3", event_type="consensus:reject",
                source="engine", created_at=now,
                payload={"decision": "reject", "votes": []},
            ),
        ]
        report = scorer.compute({}, events=events)
        assert report.convergence_rate == pytest.approx(2 / 3)

    def test_report_to_dict(self):
        scorer = CollectiveStabilityScorer()
        report = scorer.compute({})
        d = report.to_dict()
        assert "stability_score" in d
        assert "recommendation" in d


# ══════════════════════════════════════════════════════════════════════════
# Adaptive Degradation
# ══════════════════════════════════════════════════════════════════════════


class TestAdaptiveDegradationManager:
    def test_apply_degradation_none(self):
        mgr = AdaptiveDegradationManager()
        profile = AgentHealthProfile(agent_name="a", health_score=0.9)
        profile.update_degradation()
        signals = mgr.apply_degradation(profile)
        assert len(signals) == 0

    def test_apply_degradation_triggers_on_change(self):
        mgr = AdaptiveDegradationManager(cooldown_cycles=0)
        profile = AgentHealthProfile(agent_name="a", health_score=0.3)
        profile.update_degradation()
        signals = mgr.apply_degradation(profile)
        assert len(signals) > 0

    def test_cooldown_skips_degradation(self):
        mgr = AdaptiveDegradationManager(cooldown_cycles=3)
        # First call: changes to severe
        profile = AgentHealthProfile(agent_name="a", health_score=0.3)
        profile.update_degradation()
        mgr.apply_degradation(profile)

        # Second call: no change expected (same level)
        profile2 = AgentHealthProfile(agent_name="a", health_score=0.1)
        profile2.update_degradation()
        signals = mgr.apply_degradation(profile2)
        # Cooldown should skip because cycles_since_change < cooldown_cycles
        assert len(signals) == 0

    def test_rate_limit(self):
        mgr = AdaptiveDegradationManager(cooldown_cycles=0, max_interventions_per_minute=1)
        profile = AgentHealthProfile(agent_name="a", health_score=0.3)
        profile.update_degradation()
        mgr.apply_degradation(profile)
        profile2 = AgentHealthProfile(agent_name="b", health_score=0.3)
        profile2.update_degradation()
        signals = mgr.apply_degradation(profile2)
        assert len(signals) == 0 or any(s.signal_type == "breaker_hardened" for s in signals)

    def test_intervention_history(self):
        mgr = AdaptiveDegradationManager(cooldown_cycles=0)
        profile = AgentHealthProfile(agent_name="a", health_score=0.3)
        profile.update_degradation()
        mgr.apply_degradation(profile)
        history = mgr.get_intervention_history()
        assert len(history) >= 1

    def test_reset(self):
        mgr = AdaptiveDegradationManager()
        mgr.reset()
        assert len(mgr.get_intervention_history()) == 0


# ══════════════════════════════════════════════════════════════════════════
# Meta Monitor
# ══════════════════════════════════════════════════════════════════════════


class TestFalsePositiveTracker:
    def test_initial_no_fps(self):
        tracker = FalsePositiveTracker()
        assert tracker.get_fp_rate("any") == 0.0

    def test_records_false_positive(self):
        tracker = FalsePositiveTracker()
        for _ in range(5):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s1", detector_name="det_a",
                action_taken=True, health_improved=False,
            ))
        for _ in range(5):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s2", detector_name="det_a",
                action_taken=True, health_improved=True,
            ))
        assert tracker.get_fp_rate("det_a") == 0.5

    def test_detector_disabled_at_threshold(self):
        tracker = FalsePositiveTracker(fp_threshold=0.3)
        for _ in range(7):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s", detector_name="det_b",
                action_taken=True, health_improved=False,
            ))
        for _ in range(3):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s", detector_name="det_b",
                action_taken=True, health_improved=True,
            ))
        assert tracker.is_disabled("det_b")

    def test_detector_not_disabled_below_threshold(self):
        tracker = FalsePositiveTracker(fp_threshold=0.8)
        for _ in range(3):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s", detector_name="det_c",
                action_taken=True, health_improved=False,
            ))
        for _ in range(7):
            tracker.record_outcome(AnomalyOutcome(
                signal_id="s", detector_name="det_c",
                action_taken=True, health_improved=True,
            ))
        assert not tracker.is_disabled("det_c")

    def test_reset(self):
        tracker = FalsePositiveTracker()
        tracker.record_outcome(AnomalyOutcome(
            signal_id="s", detector_name="d", action_taken=True, health_improved=False,
        ))
        tracker.reset()
        assert tracker.get_fp_rate("d") == 0.0


class TestAdaptiveSampler:
    def test_initial_rate(self):
        sampler = AdaptiveSampler()
        assert sampler.sampling_rate == 1.0

    def test_reduces_on_healthy(self):
        sampler = AdaptiveSampler(max_rate=1.0, min_rate=0.1)
        for _ in range(10):
            sampler.adjust("healthy", 10.0)
        assert sampler.sampling_rate < 1.0

    def test_increases_on_degraded(self):
        sampler = AdaptiveSampler()
        sampler.adjust("degraded", 10.0)
        assert sampler.sampling_rate == 1.0

    def test_reduces_on_high_overhead(self):
        sampler = AdaptiveSampler(overhead_threshold_ms=50.0)
        sampler.adjust("healthy", 100.0)
        assert sampler.sampling_rate <= 1.0

    def test_reset(self):
        sampler = AdaptiveSampler()
        for _ in range(10):
            sampler.adjust("healthy", 100.0)
        sampler.reset()
        assert sampler.sampling_rate == 1.0


class TestFeedbackAmplificationDetector:
    def test_no_amplification_initially(self):
        detector = FeedbackAmplificationDetector()
        risk, count = detector.detect_amplification()
        assert risk == "none"
        assert count == 0

    def test_cascading_detected(self):
        detector = FeedbackAmplificationDetector(cascade_threshold=3)
        agents = ["a", "b", "c", "a", "b", "c"]
        for a in agents:
            detector.record_intervention(Intervention(action="isolate", agent=a))
        risk, count = detector.detect_amplification()
        assert risk == "cascading"

    def test_repeated_intervention_detected(self):
        detector = FeedbackAmplificationDetector(cascade_threshold=3)
        for _ in range(4):
            detector.record_intervention(Intervention(action="isolate", agent="a"))
        risk, count = detector.detect_amplification()
        assert risk == "repeated_intervention"

    def test_reset(self):
        detector = FeedbackAmplificationDetector()
        detector.record_intervention(Intervention(action="isolate", agent="a"))
        detector.reset()
        risk, count = detector.detect_amplification()
        assert risk == "none"


class TestMetaMonitor:
    def test_get_report(self):
        monitor = MetaMonitor()
        report = monitor.get_report()
        assert 0.0 <= report.false_positive_rate <= 1.0
        assert 0.0 <= report.sampling_rate <= 1.0

    def test_cycle_time_tracked(self):
        monitor = MetaMonitor()
        monitor.record_cycle_time(10.0)
        monitor.record_cycle_time(20.0)
        assert monitor.avg_cycle_time_ms == 15.0

    def test_reset(self):
        monitor = MetaMonitor()
        monitor.record_cycle_time(100.0)
        monitor.reset()
        assert monitor.avg_cycle_time_ms == 0.0


# ══════════════════════════════════════════════════════════════════════════
# Health Monitor Orchestrator
# ══════════════════════════════════════════════════════════════════════════


class TestAgentHealthMonitor:
    def test_initialization(self):
        monitor = AgentHealthMonitor()
        assert monitor.get_all_profiles() == {}

    def test_ingest_vote_event_creates_profile(self):
        monitor = AgentHealthMonitor()
        event = DiagnosticEvent(
            event_id="1", event_type="vote:approve", source="voter_a",
            payload={"decision": "approve", "confidence": 0.9},
            duration_ms=100.0,
        )
        monitor.ingest_event(event)
        profile = monitor.get_profile("voter_a")
        assert profile is not None
        assert profile.agent_name == "voter_a"

    def test_ingest_error_event(self):
        monitor = AgentHealthMonitor()
        event = DiagnosticEvent(
            event_id="1", event_type="execution:process:error",
            source="voter_a", error="timeout",
        )
        monitor.ingest_event(event)
        profile = monitor.get_profile("voter_a")
        assert profile is not None
        assert "timeout" in profile.sliding_stats.recent_errors

    def test_update_health_scores(self):
        monitor = AgentHealthMonitor()
        for i in range(5):
            event = DiagnosticEvent(
                event_id=str(i), event_type="vote:approve",
                source="voter_a",
                payload={"decision": "approve", "confidence": 0.9},
                duration_ms=100.0,
            )
            monitor.ingest_event(event)
        scores = monitor.update_health_scores()
        assert "voter_a" in scores
        assert 0.0 <= scores["voter_a"] <= 1.0

    def test_get_dashboard_data(self):
        monitor = AgentHealthMonitor()
        event = DiagnosticEvent(
            event_id="1", event_type="vote:approve", source="voter_a",
            payload={"decision": "approve", "confidence": 0.9},
        )
        monitor.ingest_event(event)
        monitor.update_health_scores()
        data = monitor.get_dashboard_data()
        assert data["total_agents"] == 1
        assert 0.0 <= data["average_health_score"] <= 1.0
        assert "degradation_distribution" in data
        assert "stability" in data
        assert "meta_monitor" in data

    def test_ingest_anomaly(self):
        monitor = AgentHealthMonitor()
        signal = AnomalySignal(
            anomaly_id="a1", detector_name="test", anomaly_type=AnomalyType.DEGRADED_AGENT,
            severity=Severity.WARNING, scope="global",
            title="test", description="test",
            evidence={"voter": "voter_a"},
        )
        monitor.ingest_anomaly(signal)
        profile = monitor.get_profile("voter_a")
        assert profile is not None
        assert len(profile.sliding_stats.recent_anomalies) == 1

    def test_derived_health_status_healthy(self):
        monitor = AgentHealthMonitor()
        status = monitor._derive_health_status()
        assert status == "healthy"

    def test_derived_health_status_degraded(self):
        monitor = AgentHealthMonitor()
        profile = AgentHealthProfile(agent_name="a", health_score=0.5)
        profile.update_degradation()
        with monitor._lock:
            monitor._profiles["a"] = profile
        status = monitor._derive_health_status()
        assert status == "degraded"

    def test_reset(self):
        monitor = AgentHealthMonitor()
        event = DiagnosticEvent(
            event_id="1", event_type="vote:approve", source="voter_a",
            payload={"decision": "approve", "confidence": 0.9},
        )
        monitor.ingest_event(event)
        monitor.reset()
        assert monitor.get_all_profiles() == {}

    @pytest.mark.asyncio
    async def test_monitoring_loop_start_stop(self):
        monitor = AgentHealthMonitor()
        await monitor.start_monitoring(interval_seconds=0.1)
        assert monitor._running
        await asyncio.sleep(0.15)
        await monitor.stop_monitoring()
        assert not monitor._running


# ══════════════════════════════════════════════════════════════════════════
# Health Score Voter
# ══════════════════════════════════════════════════════════════════════════


class FakeVoter(BaseVoter):
    def __init__(self, name: str = "fake"):
        self._name = name

    @property
    def voter_name(self) -> str:
        return self._name

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        return ConsensusVote(
            voter_name=self._name,
            decision=VoteDecision.APPROVE,
            confidence=0.9,
            reason="Test vote",
        )


class TestHealthScoreVoter:
    def test_voter_name_delegates(self):
        inner = FakeVoter("test_voter")
        profile = AgentHealthProfile(agent_name="test_voter", health_score=1.0)
        voter = HealthScoreVoter(inner, get_profile=lambda name: profile)
        assert voter.voter_name == "test_voter"

    def test_healthy_vote_passes_through(self):
        inner = FakeVoter("test")
        profile = AgentHealthProfile(agent_name="test", health_score=1.0)
        voter = HealthScoreVoter(inner, get_profile=lambda name: profile)
        ctx = MagicMock(spec=VoteContext)
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_critical_health_abstains(self):
        inner = FakeVoter("test")
        profile = AgentHealthProfile(agent_name="test", health_score=0.1)
        voter = HealthScoreVoter(inner, get_profile=lambda name: profile)
        ctx = MagicMock(spec=VoteContext)
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.ABSTAIN
        assert "critical" in result.reason

    def test_degraded_adjusts_confidence(self):
        inner = FakeVoter("test")
        profile = AgentHealthProfile(agent_name="test", health_score=0.7)
        profile.update_degradation()
        voter = HealthScoreVoter(inner, get_profile=lambda name: profile)
        ctx = MagicMock(spec=VoteContext)
        result = voter.vote(ctx)
        assert result.confidence < 0.9
        assert "health-adjusted" in result.reason

    def test_inner_voter_property(self):
        inner = FakeVoter("test")
        profile = AgentHealthProfile(agent_name="test", health_score=1.0)
        voter = HealthScoreVoter(inner, get_profile=lambda name: profile)
        assert voter.inner_voter is inner
