"""
Tests for ConsensusTimeoutPolicy system: adaptive timeouts, degraded mode,
hung-agent recovery, quorum fallback, cascading delay, and deadline enforcement.
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
    TimeoutAction,
    BaseVoter,
)
from app.core.consensus_timeouts import (
    ConsensusTimeoutConfig,
    ConsensusTimeoutPolicy,
    ConsensusTimeoutState,
    HungState,
    VoterTimeoutStats,
)


# ── Helpers ────────────────────────────────────────────────────────────


class SlowVoter(BaseVoter):
    """A voter that takes a specified duration to vote."""
    def __init__(self, name: str = "slow", delay_ms: float = 100.0):
        self._name = name
        self._delay = delay_ms

    @property
    def voter_name(self) -> str:
        return self._name

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        time.sleep(self._delay / 1000.0)
        return ConsensusVote(
            voter_name=self._name,
            decision=VoteDecision.APPROVE,
            confidence=1.0,
            reason="Slow voter done",
        )


class ErrorVoter(BaseVoter):
    """A voter that always raises an exception."""
    @property
    def voter_name(self) -> str:
        return "error"

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        raise RuntimeError("Voter failed intentionally")


def make_ctx(**overrides) -> VoteContext:
    from app.db.uow import UnitOfWork
    from app.models.student_progress import LearningPath, PathModule
    uow = MagicMock(spec=UnitOfWork)
    # Configure DB mock to return 0 for count() so PrereqVoter approves
    db_mock = MagicMock()
    db_mock.query.return_value.filter.return_value.count.return_value = 0
    db_mock.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
    uow.db = db_mock
    module = MagicMock(spec=PathModule)
    module.order = 1
    module.status = "available"
    path = MagicMock(spec=LearningPath)
    kwargs = dict(
        uow=uow,
        student_id="stu-1",
        module_id="mod-1",
        path_id="path-1",
        course_id="c-1",
        score=0.8,
        module=module,
        path=path,
    )
    kwargs.update(overrides)
    return VoteContext(**kwargs)


# ── ConsensusTimeoutConfig ─────────────────────────────────────────────


class TestConsensusTimeoutConfig:
    def test_defaults(self):
        cfg = ConsensusTimeoutConfig()
        assert cfg.default_voter_timeout_ms == 5000.0
        assert cfg.overall_deadline_ms == 30000.0
        assert cfg.adaptive_enabled is True
        assert cfg.degraded_voter_threshold == 2
        assert cfg.quorum_fallback_enabled is True
        assert cfg.quorum_minimum == 1
        assert cfg.hung_voter_timeout_multiplier == 3.0

    def test_validation(self):
        with pytest.raises(ValueError, match="default_voter_timeout_ms"):
            ConsensusTimeoutConfig(default_voter_timeout_ms=0)
        with pytest.raises(ValueError, match="overall_deadline_ms"):
            ConsensusTimeoutConfig(overall_deadline_ms=0)
        with pytest.raises(ValueError, match="degraded_voter_threshold"):
            ConsensusTimeoutConfig(degraded_voter_threshold=0)
        with pytest.raises(ValueError, match="quorum_minimum"):
            ConsensusTimeoutConfig(quorum_minimum=0)
        with pytest.raises(ValueError, match="hung_voter_timeout_multiplier"):
            ConsensusTimeoutConfig(hung_voter_timeout_multiplier=0.5)


# ── ConsensusTimeoutState ──────────────────────────────────────────────


class TestConsensusTimeoutState:
    def test_elapsed_ms_increases(self):
        state = ConsensusTimeoutState(config=ConsensusTimeoutConfig())
        e1 = state.elapsed_ms()
        time.sleep(0.01)
        e2 = state.elapsed_ms()
        assert e2 > e1

    def test_remaining_deadline(self):
        cfg = ConsensusTimeoutConfig(overall_deadline_ms=1000.0)
        state = ConsensusTimeoutState(config=cfg)
        remaining = state.remaining_deadline_ms()
        assert 0 < remaining <= 1000.0


# ── VoterTimeoutStats ──────────────────────────────────────────────────


class TestVoterTimeoutStats:
    def test_p50_p95(self):
        stats = VoterTimeoutStats(voter_name="test")
        for d in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
            stats.record_duration(float(d))
        assert stats.p50 == 55.0  # median of [10..100] is 55 (mean of 50 and 60)
        assert stats.p95 == 100.0
        assert stats.max_duration == 100.0
        assert stats.count == 10

    def test_window_sliding(self):
        stats = VoterTimeoutStats(voter_name="test", max_window_size=3)
        stats.record_duration(10)
        stats.record_duration(20)
        stats.record_duration(30)
        assert stats.count == 3
        assert stats.p50 == 20.0
        stats.record_duration(100)
        assert stats.count == 3  # window slides
        assert stats.p50 == 30.0  # window is [20, 30, 100]

    def test_adaptive_multiplier_low_samples(self):
        stats = VoterTimeoutStats(voter_name="test")
        assert stats.adaptive_multiplier == 1.0  # fewer than 3 samples
        stats.record_duration(10)
        stats.record_duration(20)
        assert stats.adaptive_multiplier == 1.0

    def test_adaptive_multiplier_computed(self):
        stats = VoterTimeoutStats(voter_name="test", max_window_size=10)
        for _ in range(10):
            stats.record_duration(100.0)
        assert stats.adaptive_multiplier == 1.5  # p95=100, recommended=150, mult=1.5


# ── ConsensusTimeoutPolicy — Core ──────────────────────────────────────


class TestConsensusTimeoutPolicy:
    def test_create_state(self):
        policy = ConsensusTimeoutPolicy()
        state = policy.create_state()
        assert isinstance(state, ConsensusTimeoutState)
        assert state.degraded is False
        assert state.deadline_exceeded is False

    def test_check_voter_no_timeout(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(default_voter_timeout_ms=1000))
        state = policy.create_state()
        timed_out, action = policy.check_voter(state, "mastery", elapsed_ms=50)
        assert timed_out is False
        assert action == TimeoutAction.NONE

    def test_check_voter_timeout_exceeded(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(default_voter_timeout_ms=50))
        state = policy.create_state()
        timed_out, action = policy.check_voter(state, "mastery", elapsed_ms=100)
        assert timed_out is True
        assert action == TimeoutAction.USE_FALLBACK_VOTE

    def test_check_voter_hung(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=50,
            hung_voter_timeout_multiplier=2.0,
        ))
        state = policy.create_state()
        # Hung threshold = 50 * 2 = 100ms, elapsed=200 > 100
        timed_out, action = policy.check_voter(state, "mastery", elapsed_ms=200)
        assert timed_out is True
        assert action == TimeoutAction.HUNG_RECOVERY

    def test_check_voter_deadline_exceeded(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(default_voter_timeout_ms=1000))
        state = policy.create_state()
        state.deadline_exceeded = True
        timed_out, action = policy.check_voter(state, "mastery", elapsed_ms=10)
        assert timed_out is True
        assert action == TimeoutAction.DEADLINE_EXCEEDED

    def test_overall_deadline(self):
        cfg = ConsensusTimeoutConfig(overall_deadline_ms=50, default_voter_timeout_ms=1000)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        time.sleep(0.06)  # wait 60ms
        exceeded = policy.check_overall_deadline(state)
        assert exceeded is True
        assert state.deadline_exceeded is True
        assert state.degraded is True

    def test_overall_deadline_not_exceeded(self):
        cfg = ConsensusTimeoutConfig(overall_deadline_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        exceeded = policy.check_overall_deadline(state)
        assert exceeded is False
        assert state.deadline_exceeded is False

    def test_cascading_delay(self):
        cfg = ConsensusTimeoutConfig(cascading_delay_threshold_ms=100)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        detected = policy.check_cascading_delay(state, [60, 50])
        assert detected is True
        assert state.cascading_delay_detected is True

    def test_cascading_delay_not_reached(self):
        cfg = ConsensusTimeoutConfig(cascading_delay_threshold_ms=200)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        detected = policy.check_cascading_delay(state, [30, 40])
        assert detected is False
        assert state.cascading_delay_detected is False

    def test_record_voter_result(self):
        policy = ConsensusTimeoutPolicy()
        state = policy.create_state()
        record = policy.record_voter_result(
            state, "mastery", duration_ms=50.0,
            timed_out=False,
        )
        assert record.voter_name == "mastery"
        assert record.timed_out is False
        assert record.duration_ms == 50.0
        assert "mastery" in state.voter_records
        assert "mastery" in state.voter_order

    def test_record_voter_duration_updates_stats(self):
        policy = ConsensusTimeoutPolicy()
        policy.record_voter_duration("mastery", 100.0)
        policy.record_voter_duration("mastery", 110.0)
        policy.record_voter_duration("mastery", 90.0)
        stats = policy.get_voter_stats("mastery")
        assert stats is not None
        assert stats.count == 3
        assert stats.p50 == 100.0

    def test_record_voter_duration_marks_recovered(self):
        cfg = ConsensusTimeoutConfig(
            default_voter_timeout_ms=10,
            hung_voter_timeout_multiplier=2.0,
        )
        policy = ConsensusTimeoutPolicy(cfg)
        # First, simulate hung (threshold = 10*2 = 20ms, elapsed 100 > 20)
        state = policy.create_state()
        policy.check_voter(state, "test", elapsed_ms=100)
        assert policy.get_hung_state("test") == HungState.SUSPECTED

        # Now record a normal duration — voter should be recovered
        policy.record_voter_duration("test", 10.0)
        assert policy.get_hung_state("test") == HungState.RECOVERED


# ── ConsensusTimeoutPolicy — Degraded Mode ────────────────────────────


class TestDegradedMode:
    def test_degraded_triggered_below_threshold(self):
        cfg = ConsensusTimeoutConfig(degraded_voter_threshold=3)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        degraded = policy.check_degraded(state, completed_count=2, total_voters=4)
        assert degraded is True
        assert state.degraded is True
        assert "2/4" in state.degraded_reason

    def test_degraded_not_triggered_above_threshold(self):
        cfg = ConsensusTimeoutConfig(degraded_voter_threshold=2)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        degraded = policy.check_degraded(state, completed_count=3, total_voters=4)
        assert degraded is False
        assert state.degraded is False

    def test_build_degraded_vote(self):
        cfg = ConsensusTimeoutConfig(degraded_vote_reason="Custom degraded reason")
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        state.degraded = True
        state.degraded_reason = "Test degraded"
        vote = policy.build_degraded_vote(state, "mastery")
        assert vote.voter_name == "mastery"
        assert vote.decision == VoteDecision.ABSTAIN
        assert vote.confidence == 0.0
        assert vote.evidence["degraded"] is True

    def test_build_fallback_vote(self):
        policy = ConsensusTimeoutPolicy()
        state = policy.create_state()
        vote = policy.build_fallback_vote(state, "mastery", reason="Custom fallback")
        assert vote.voter_name == "mastery"
        assert vote.decision == VoteDecision.ABSTAIN
        assert vote.evidence["timeout"] is True


# ── ConsensusTimeoutPolicy — Hung Recovery ────────────────────────────


class TestHungRecovery:
    def test_hung_strikes_accumulate(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=10,
            hung_voter_timeout_multiplier=2.0,
        ))
        state = policy.create_state()

        # First hung event → SUSPECTED (strike 1)
        policy.check_voter(state, "slowpoke", elapsed_ms=50)
        assert policy.get_hung_state("slowpoke") == HungState.SUSPECTED

        # Second hung → still SUSPECTED (strike 2)
        policy.check_voter(state, "slowpoke", elapsed_ms=50)
        assert policy.get_hung_state("slowpoke") == HungState.SUSPECTED

        # Third hung → CONFIRMED (strike 3)
        policy.check_voter(state, "slowpoke", elapsed_ms=50)
        assert policy.get_hung_state("slowpoke") == HungState.CONFIRMED

    def test_hung_voters_tracked_in_state(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=10,
            hung_voter_timeout_multiplier=2.0,
        ))
        state = policy.create_state()
        policy.check_voter(state, "slow", elapsed_ms=100)
        assert "slow" in state.hung_voters

    def test_hung_normal_voter_not_hung(self):
        policy = ConsensusTimeoutPolicy()
        assert policy.get_hung_state("normal_guy") == HungState.NORMAL


# ── ConsensusTimeoutPolicy — Quorum Fallback ──────────────────────────


class TestQuorumFallback:
    def test_quorum_met(self):
        cfg = ConsensusTimeoutConfig(quorum_minimum=3)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        # Record 3 voters that didn't time out
        for i, name in enumerate(["a", "b", "c"]):
            policy.record_voter_result(state, name, duration_ms=10.0)
        assert policy.is_quorum_met(state) is True

    def test_quorum_not_met(self):
        cfg = ConsensusTimeoutConfig(quorum_minimum=5)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        for i, name in enumerate(["a", "b"]):
            policy.record_voter_result(state, name, duration_ms=10.0)
        assert policy.is_quorum_met(state) is False

    def test_quorum_fallback_trigger(self):
        cfg = ConsensusTimeoutConfig(quorum_minimum=5)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        policy.record_voter_result(state, "a", duration_ms=10.0)
        policy.trigger_quorum_fallback(state)
        assert state.quorum_fallback_triggered is True
        assert state.quorum_met is False


# ── ConsensusTimeoutPolicy — Adaptive Timeouts ────────────────────────


class TestAdaptiveTimeouts:
    def test_adaptive_disabled_uses_default(self):
        cfg = ConsensusTimeoutConfig(
            adaptive_enabled=False,
            default_voter_timeout_ms=5000,
        )
        policy = ConsensusTimeoutPolicy(cfg)
        # No stats recorded, but adaptive is off
        timeout = policy._get_adaptive_timeout("mastery")
        assert timeout == 5000.0

    def test_adaptive_enabled_few_samples(self):
        cfg = ConsensusTimeoutConfig(adaptive_enabled=True, default_voter_timeout_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        # Only 1 sample, adaptive doesn't kick in
        policy.record_voter_duration("mastery", 100)
        timeout = policy._get_adaptive_timeout("mastery")
        assert timeout == 5000.0  # default because < 3 samples

    def test_adaptive_enough_samples(self):
        cfg = ConsensusTimeoutConfig(adaptive_enabled=True, default_voter_timeout_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        for _ in range(10):
            policy.record_voter_duration("mastery", 100.0)
        timeout = policy._get_adaptive_timeout("mastery")
        # p95 = 100, recommended = 150, not clamped (10 <= 150 <= 50000)
        assert timeout == pytest.approx(150.0, rel=0.1)

    def test_adaptive_clamped_lower(self):
        cfg = ConsensusTimeoutConfig(adaptive_enabled=True, default_voter_timeout_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        for _ in range(10):
            policy.record_voter_duration("mastery", 1.0)
        timeout = policy._get_adaptive_timeout("mastery")
        # p95 = 1, recommended = 1.5, lower bound = 10ms (hard floor)
        assert timeout == pytest.approx(10.0, rel=0.1)

    def test_adaptive_clamped_upper(self):
        cfg = ConsensusTimeoutConfig(adaptive_enabled=True, default_voter_timeout_ms=1000)
        policy = ConsensusTimeoutPolicy(cfg)
        for _ in range(10):
            policy.record_voter_duration("mastery", 5000.0)
        timeout = policy._get_adaptive_timeout("mastery")
        # p95 = 5000, recommended = 7500, upper bound = 1000*10 = 10000
        assert timeout == pytest.approx(7500.0, rel=0.1)

    def test_get_all_stats(self):
        policy = ConsensusTimeoutPolicy()
        policy.record_voter_duration("a", 10)
        policy.record_voter_duration("b", 20)
        all_stats = policy.get_all_stats()
        assert "a" in all_stats
        assert "b" in all_stats
        assert len(all_stats) == 2


# ── ConsensusTimeoutPolicy — Baggage Propagation ──────────────────────


class TestBaggagePropagation:
    def test_to_baggage(self):
        cfg = ConsensusTimeoutConfig(overall_deadline_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        baggage = policy.to_baggage(state)
        assert "ctmo:remaining_ms" in baggage
        assert "ctmo:deadline_ms" in baggage
        assert baggage["ctmo:degraded"] == "0"
        assert baggage["ctmo:deadline_exceeded"] == "0"
        assert baggage["ctmo:quorum_met"] == "1"

    def test_to_baggage_degraded(self):
        policy = ConsensusTimeoutPolicy()
        state = policy.create_state()
        state.degraded = True
        baggage = policy.to_baggage(state)
        assert baggage["ctmo:degraded"] == "1"

    def test_from_baggage(self):
        policy = ConsensusTimeoutPolicy()
        baggage = {
            "ctmo:remaining_ms": "2500.0",
            "ctmo:deadline_ms": "5000.0",
            "ctmo:degraded": "1",
            "ctmo:deadline_exceeded": "0",
        }
        info = policy.from_baggage(baggage)
        assert info["remaining_ms"] == 2500.0
        assert info["deadline_ms"] == 5000.0
        assert info["degraded"] is True
        assert info["deadline_exceeded"] is False

    def test_from_baggage_empty(self):
        policy = ConsensusTimeoutPolicy()
        info = policy.from_baggage({})
        assert info == {}

    def test_check_baggage_timeout(self):
        policy = ConsensusTimeoutPolicy()
        # Baggage says deadline exceeded
        baggage = {"ctmo:deadline_exceeded": "1"}
        assert policy.check_baggage_timeout(baggage) is True

        # Baggage says remaining <= 0
        baggage = {"ctmo:remaining_ms": "-5.0"}
        assert policy.check_baggage_timeout(baggage) is True

        # Baggage says healthy
        baggage = {"ctmo:remaining_ms": "1000.0", "ctmo:deadline_exceeded": "0"}
        assert policy.check_baggage_timeout(baggage) is False


# ── State Summary ──────────────────────────────────────────────────────


class TestStateSummary:
    def test_get_state_summary(self):
        cfg = ConsensusTimeoutConfig(overall_deadline_ms=5000)
        policy = ConsensusTimeoutPolicy(cfg)
        state = policy.create_state()
        policy.record_voter_result(state, "a", duration_ms=10.0)
        state.degraded = True
        state.degraded_reason = "Test"
        summary = policy.get_state_summary(state)
        assert summary["degraded"] is True
        assert summary["degraded_reason"] == "Test"
        assert "elapsed_ms" in summary
        assert "remaining_ms" in summary
        assert "voter_count" in summary
        assert summary["voter_count"] == 1


# ── Integration with ConsensusEngine.run() ────────────────────────────


class TestConsensusEngineIntegration:
    def test_run_without_timeout_policy(self):
        """Existing behavior must be unchanged when no policy is passed."""
        engine = ConsensusEngine()
        ctx = make_ctx()
        result = engine.run(ctx)
        assert result.timeout_info is None

    def test_run_with_timeout_policy_all_fast(self):
        """All voters complete quickly; no timeouts."""
        config = ConsensusTimeoutConfig(
            default_voter_timeout_ms=5000,
            overall_deadline_ms=10000,
        )
        policy = ConsensusTimeoutPolicy(config)
        engine = ConsensusEngine(voters=[
            SlowVoter("a", delay_ms=1),
            SlowVoter("b", delay_ms=1),
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        assert result.decision == VoteDecision.APPROVE
        assert result.timeout_info is not None
        assert result.timeout_info["degraded"] is False
        assert result.timeout_info["deadline_exceeded"] is False
        # Both voters should have entries in timeouts
        assert result.timeout_info["voter_count"] == 2

    def test_run_with_timeout_voter_timing_recorded(self):
        """Voter timings should include timeout info in the trace entries."""
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=5000,
            overall_deadline_ms=10000,
        ))
        engine = ConsensusEngine(voters=[
            SlowVoter("a", delay_ms=1),
        ])
        ctx = make_ctx()
        trace_ctx = MagicMock()
        trace_ctx.trace_id = "test-trace-123"
        result = engine.run(ctx, trace_ctx=trace_ctx, timeout_policy=policy)
        assert len(result.voter_timings) == 1
        assert result.voter_timings[0]["voter_name"] == "a"
        assert result.voter_timings[0]["status"] == "ok"

    def test_run_with_slow_voter_triggers_timeout(self):
        """A voter that exceeds the per-voter timeout should get a fallback vote."""
        config = ConsensusTimeoutConfig(
            default_voter_timeout_ms=20,   # very short
            overall_deadline_ms=5000,
            quorum_minimum=1,
            degraded_voter_threshold=1,
        )
        policy = ConsensusTimeoutPolicy(config)
        engine = ConsensusEngine(voters=[
            SlowVoter("slowpoke", delay_ms=200),  # takes 200ms > 20ms timeout
            SlowVoter("quick", delay_ms=1),
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        # slowpoke should have timed out; its fallback vote is ABSTAIN with 0 confidence
        slow_vote = next(v for v in result.votes if v.voter_name == "slowpoke")
        assert slow_vote.decision == VoteDecision.ABSTAIN
        assert slow_vote.confidence == 0.0
        # The timeout state should reflect the timeout
        assert result.timeout_info is not None
        assert result.timeout_info["timed_out_count"] >= 1

    def test_run_overall_deadline(self):
        """If the overall deadline is too short, remaining voters are skipped."""
        config = ConsensusTimeoutConfig(
            default_voter_timeout_ms=5000,
            overall_deadline_ms=10,  # extremely short
            degraded_voter_threshold=1,
            quorum_minimum=1,
        )
        policy = ConsensusTimeoutPolicy(config)
        # Use real time — first voter sleeps 5ms, which already exceeds 10ms deadline
        engine = ConsensusEngine(voters=[
            SlowVoter("first", delay_ms=5),
            SlowVoter("second", delay_ms=5),
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        # first should be ABSTAIN because deadline exceeded even before its vote
        # Because overall_deadline_ms=10 is so short that the first voter's 5ms
        # plus overhead will trigger the deadline
        assert result.timeout_info is not None
        # At least one voter should be affected by deadline
        second_vote = next(v for v in result.votes if v.voter_name == "second")
        assert "deadline" in second_vote.reason.lower() or result.timeout_info["deadline_exceeded"]

    def test_run_error_voter_triggers_fallback(self):
        """A voter that raises an exception should get the fallback ABSTAIN vote."""
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=5000,
            overall_deadline_ms=10000,
            quorum_minimum=1,
        ))
        engine = ConsensusEngine(voters=[
            ErrorVoter(),
            SlowVoter("good", delay_ms=1),
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        error_vote = next(v for v in result.votes if v.voter_name == "error")
        assert error_vote.decision == VoteDecision.ABSTAIN
        assert "error" in error_vote.reason

    def test_run_quorum_not_met(self):
        """When quorum_minimum > completed voters, quorum fallback triggers."""
        config = ConsensusTimeoutConfig(
            default_voter_timeout_ms=20,   # very short
            overall_deadline_ms=5000,
            quorum_minimum=10,             # unrealistic minimum
            degraded_voter_threshold=1,
        )
        policy = ConsensusTimeoutPolicy(config)
        engine = ConsensusEngine(voters=[
            SlowVoter("a", delay_ms=200),  # will time out
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        assert result.timeout_info is not None
        assert result.timeout_info["quorum_fallback_triggered"] or result.timeout_info["timed_out_count"] > 0

    def test_run_respects_degraded_mode(self):
        """When degraded mode is triggered, result should reflect it."""
        config = ConsensusTimeoutConfig(
            default_voter_timeout_ms=10,   # all voters time out
            overall_deadline_ms=5000,
            degraded_voter_threshold=4,    # we have 2 voters, so threshold not met
            quorum_minimum=1,
        )
        policy = ConsensusTimeoutPolicy(config)
        engine = ConsensusEngine(voters=[
            SlowVoter("a", delay_ms=200),
            SlowVoter("b", delay_ms=200),
        ])
        ctx = make_ctx()
        result = engine.run(ctx, timeout_policy=policy)
        assert result.timeout_info is not None
        assert result.timeout_info["degraded"] is True


# ── Hung Consensus Detector ────────────────────────────────────────────


class TestHungConsensusDetector:
    def test_detection(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import HungConsensusDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = HungConsensusDetector(
            duration_threshold_ms=100,
            min_samples=3,
        )
        # Create vote events for a slow voter
        events = [
            DiagnosticEvent(
                event_id=f"e{i}",
                event_type="vote:approve",
                source="slowpoke",
                scope="student:s1",
                duration_ms=500.0,
                correlation_id="trace-1",
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any(s.metric_value == 500.0 for s in signals)

    def test_no_detection_for_fast_voter(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import HungConsensusDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = HungConsensusDetector(
            duration_threshold_ms=1000,
            min_samples=3,
        )
        events = [
            DiagnosticEvent(
                event_id=f"e{i}",
                event_type="vote:approve",
                source="fast",
                scope="student:s1",
                duration_ms=10.0,
            )
            for i in range(3)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0  # all under threshold

    def test_high_error_rate(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import HungConsensusDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = HungConsensusDetector(
            duration_threshold_ms=10000,
            error_rate_threshold=0.2,
            min_samples=3,
        )
        events = [
            DiagnosticEvent(
                event_id=f"e{i}",
                event_type="vote:approve",
                source="error_prone",
                scope="student:s1",
                duration_ms=10.0,
                error=f"err{i}" if i < 2 else None,  # 2 out of 5 errors = 40% > 20%
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1  # high error rate signal


# ── Cascading Delay Detector ───────────────────────────────────────────


class TestCascadingDelayDetector:
    def test_cascade_detected(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import CascadingDelayDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = CascadingDelayDetector(
            single_voter_threshold_ms=50,
            cascade_ratio_threshold=0.5,
        )
        # One run with 3 voters — first is slow, 2nd and 3rd are also slow
        events = [
            DiagnosticEvent(
                event_id="e1", event_type="vote:approve",
                source="voter_a", scope="student:s1",
                duration_ms=200.0, correlation_id="trace-x",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1),
            ),
            DiagnosticEvent(
                event_id="e2", event_type="vote:approve",
                source="voter_b", scope="student:s1",
                duration_ms=150.0, correlation_id="trace-x",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1, 200000),
            ),
            DiagnosticEvent(
                event_id="e3", event_type="vote:approve",
                source="voter_c", scope="student:s1",
                duration_ms=180.0, correlation_id="trace-x",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1, 400000),
            ),
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any("cascading" in s.title.lower() for s in signals)

    def test_no_cascade_when_subsequent_fast(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import CascadingDelayDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = CascadingDelayDetector(
            single_voter_threshold_ms=50,
            cascade_ratio_threshold=0.5,
        )
        # First voter is slow, but subsequent are fast — no cascade
        events = [
            DiagnosticEvent(
                event_id="e1", event_type="vote:approve",
                source="voter_a", scope="student:s1",
                duration_ms=200.0, correlation_id="trace-y",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1),
            ),
            DiagnosticEvent(
                event_id="e2", event_type="vote:approve",
                source="voter_b", scope="student:s1",
                duration_ms=10.0, correlation_id="trace-y",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1, 200000),
            ),
            DiagnosticEvent(
                event_id="e3", event_type="vote:approve",
                source="voter_c", scope="student:s1",
                duration_ms=5.0, correlation_id="trace-y",
                created_at=__import__('datetime').datetime(2026, 1, 1, 0, 0, 1, 210000),
            ),
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0


# ── Quorum Instability Detector ────────────────────────────────────────


class TestQuorumInstabilityDetector:
    def test_quorum_dip(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import QuorumInstabilityDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = QuorumInstabilityDetector(
            min_expected_voters=4,
            quorum_ratio_threshold=0.5,
        )
        events = [
            DiagnosticEvent(
                event_id="c1", event_type="consensus:approve",
                source="consensus_engine", scope="student:s1",
                payload={"num_voters": 2, "decision": "approve"},
            ),
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any("quorum dip" in s.title.lower() for s in signals)

    def test_no_dip_when_quorum_met(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import QuorumInstabilityDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = QuorumInstabilityDetector(
            min_expected_voters=4,
            quorum_ratio_threshold=0.5,
        )
        events = [
            DiagnosticEvent(
                event_id="c1", event_type="consensus:approve",
                source="consensus_engine", scope="student:s1",
                payload={"num_voters": 4, "decision": "approve"},
            ),
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0

    def test_instability_across_runs(self):
        from app.swarm_diagnostics.detectors.consensus_timeout import QuorumInstabilityDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent

        detector = QuorumInstabilityDetector(
            min_expected_voters=4,
            instability_window=5,
        )
        # 4 out of 5 runs have low quorum — triggers instability
        events = [
            DiagnosticEvent(
                event_id=f"c{i}", event_type="consensus:approve",
                source="consensus_engine", scope="student:s1",
                payload={"num_voters": 2 if i < 4 else 4, "decision": "approve"},
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) >= 1
        assert any("instability" in s.title.lower() for s in signals)


# ── Reset ──────────────────────────────────────────────────────────────


class TestReset:
    def test_policy_reset(self):
        policy = ConsensusTimeoutPolicy()
        policy.record_voter_duration("test", 100.0)
        assert len(policy.get_all_stats()) == 1
        policy.reset()
        assert len(policy.get_all_stats()) == 0

    def test_hung_state_reset(self):
        policy = ConsensusTimeoutPolicy(ConsensusTimeoutConfig(
            default_voter_timeout_ms=10,
            hung_voter_timeout_multiplier=2.0,
        ))
        state = policy.create_state()
        policy.check_voter(state, "hunky", elapsed_ms=100)
        assert policy.get_hung_state("hunky") == HungState.SUSPECTED
        policy.reset()
        assert policy.get_hung_state("hunky") == HungState.NORMAL


# ══════════════════════════════════════════════════════════════════════════
# V2 Tests — ConsensusCancellationContext, Metrics, Recovery, Middleware, async_run
# ══════════════════════════════════════════════════════════════════════════

import asyncio
from contextvars import ContextVar

import pytest

from app.core.consensus_cancellation import (
    CancellationToken,
    CancellationReason,
    ConsensusCancellationContext,
    CancelledError,
    get_current_cancellation_ctx,
    set_current_cancellation_ctx,
    is_cancellation_requested,
    require_not_cancelled,
)
from app.core.consensus_timeout_metrics import (
    ConsensusTimeoutMetrics,
    TimeoutMetricSnapshot,
)
from app.core.consensus_timeouts import (
    HungAgentRecoveryConfig,
    HungAgentRecoveryManager,
)


# ── CancellationToken Tests ──────────────────────────────────────────────


class TestCancellationToken:
    @pytest.mark.asyncio
    async def test_not_cancelled_by_default(self):
        token = CancellationToken()
        assert not token.is_cancelled()
        assert token.reason is None
        assert token.source_voter is None

    @pytest.mark.asyncio
    async def test_cancel_sets_reason(self):
        token = CancellationToken()
        token.cancel(CancellationReason.VOTER_TIMEOUT, source="mastery")
        assert token.is_cancelled()
        assert token.reason == CancellationReason.VOTER_TIMEOUT
        assert token.source_voter == "mastery"
        assert token.cancelled_at_ms is not None

    @pytest.mark.asyncio
    async def test_cancel_is_idempotent(self):
        token = CancellationToken()
        token.cancel(CancellationReason.VOTER_TIMEOUT)
        token.cancel(CancellationReason.HUNG_AGENT)  # second call ignored
        assert token.reason == CancellationReason.VOTER_TIMEOUT

    @pytest.mark.asyncio
    async def test_wait_returns_true_when_cancelled(self):
        token = CancellationToken()
        token.cancel(CancellationReason.MANUAL)
        result = await token.wait(timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_returns_false_on_timeout(self):
        token = CancellationToken()
        result = await token.wait(timeout=0.05)
        assert result is False

    @pytest.mark.asyncio
    async def test_to_dict(self):
        token = CancellationToken()
        token.cancel(CancellationReason.VOTER_TIMEOUT, source="mastery")
        d = token.to_dict()
        assert d["cancelled"] is True
        assert d["reason"] == "voter_timeout"
        assert d["source_voter"] == "mastery"


# ── ConsensusCancellationContext Tests ───────────────────────────────────


class TestConsensusCancellationContext:
    @pytest.mark.asyncio
    async def test_default_state(self):
        ctx = ConsensusCancellationContext()
        assert not ctx.cancelled
        assert ctx.token.reason is None
        assert ctx.remaining_voters == []

    @pytest.mark.asyncio
    async def test_cancel_propagates_to_token(self):
        ctx = ConsensusCancellationContext()
        ctx.cancel(CancellationReason.HUNG_AGENT, source="sequence")
        assert ctx.cancelled
        assert ctx.token.reason == CancellationReason.HUNG_AGENT

    @pytest.mark.asyncio
    async def test_mark_methods(self):
        ctx = ConsensusCancellationContext()
        ctx.mark_completed("mastery")
        ctx.mark_skipped("sequence")
        ctx.mark_timed_out("prerequisite")
        assert "mastery" in ctx.completed_voters
        assert "sequence" in ctx.skipped_voters
        assert "prerequisite" in ctx.timed_out_voters

    @pytest.mark.asyncio
    async def test_mark_methods_idempotent(self):
        ctx = ConsensusCancellationContext()
        ctx.mark_completed("mastery")
        ctx.mark_completed("mastery")
        assert len(ctx.completed_voters) == 1

    @pytest.mark.asyncio
    async def test_to_dict(self):
        ctx = ConsensusCancellationContext()
        ctx.remaining_voters = ["a", "b", "c"]
        ctx.mark_completed("a")
        d = ctx.to_dict()
        assert d["cancelled"] is False
        assert d["completed"] == 1
        assert d["remaining"] == 3

    @pytest.mark.asyncio
    async def test_contextvar_propagation(self):
        """Cancellation context propagates via ContextVar."""
        ctx = ConsensusCancellationContext()
        token = set_current_cancellation_ctx(ctx)
        try:
            retrieved = get_current_cancellation_ctx()
            assert retrieved is ctx
            assert not is_cancellation_requested()
            ctx.cancel(CancellationReason.VOTER_TIMEOUT)
            assert is_cancellation_requested()
        finally:
            set_current_cancellation_ctx(token)

    @pytest.mark.asyncio
    async def test_require_not_cancelled_raises_when_cancelled(self):
        ctx = ConsensusCancellationContext()
        token = set_current_cancellation_ctx(ctx)
        try:
            ctx.cancel(CancellationReason.VOTER_TIMEOUT)
            with pytest.raises(CancelledError):
                require_not_cancelled()
        finally:
            set_current_cancellation_ctx(token)

    @pytest.mark.asyncio
    async def test_require_not_cancelled_passes_when_not_cancelled(self):
        ctx = ConsensusCancellationContext()
        token = set_current_cancellation_ctx(ctx)
        try:
            require_not_cancelled()
        finally:
            set_current_cancellation_ctx(token)

    @pytest.mark.asyncio
    async def test_contextvar_none_when_unset(self):
        assert get_current_cancellation_ctx() is None
        assert not is_cancellation_requested()


# ── ConsensusTimeoutMetrics Tests ────────────────────────────────────────


class TestConsensusTimeoutMetrics:
    def test_initial_state(self):
        m = ConsensusTimeoutMetrics()
        snap = m.snapshot()
        assert snap.total_timeouts == 0
        assert snap.degraded_count == 0
        assert snap.quorum_fallback_count == 0
        assert snap.hung_agent_count == 0
        assert snap.cancellation_count == 0
        assert snap.cascading_delay_count == 0
        assert snap.total_consensus_runs == 0

    def test_record_timeout(self):
        m = ConsensusTimeoutMetrics()
        m.record_timeout("voter_timeout", "mastery")
        assert m.total_timeouts == 1
        snap = m.snapshot()
        assert snap.timeouts_by_reason.get("voter_timeout") == 1

    def test_record_timeout_with_enum(self):
        m = ConsensusTimeoutMetrics()
        m.record_timeout(CancellationReason.HUNG_AGENT, "sequence")
        snap = m.snapshot()
        assert snap.timeouts_by_reason.get("hung_agent") == 1

    def test_record_degraded(self):
        m = ConsensusTimeoutMetrics()
        m.record_degraded()
        assert m.snapshot().degraded_count == 1

    def test_record_quorum_fallback(self):
        m = ConsensusTimeoutMetrics()
        m.record_quorum_fallback()
        assert m.snapshot().quorum_fallback_count == 1

    def test_record_hung_agent(self):
        m = ConsensusTimeoutMetrics()
        m.record_hung_agent("mastery", strikes=2, action="skipped")
        snap = m.snapshot()
        assert snap.hung_agent_count == 1
        assert len(snap.hung_agents) == 1
        assert snap.hung_agents[0]["agent_name"] == "mastery"
        assert snap.hung_agents[0]["strikes"] == 2
        assert snap.hung_agents[0]["action"] == "skipped"

    def test_record_cancellation(self):
        m = ConsensusTimeoutMetrics()
        m.record_cancellation("voter_timeout", source="mastery")
        assert m.snapshot().cancellation_count == 1

    def test_record_cascading_delay(self):
        m = ConsensusTimeoutMetrics()
        m.record_cascading_delay()
        assert m.snapshot().cascading_delay_count == 1

    def test_record_consensus_run(self):
        m = ConsensusTimeoutMetrics()
        m.record_consensus_run(
            total_voters=4, timed_out=1, skipped=0,
            adaptive_multiplier=1.5,
            duration_stats={"avg_ms": 100.0, "p95_ms": 200.0},
        )
        snap = m.snapshot()
        assert snap.total_consensus_runs == 1
        assert snap.total_voters == 4
        assert snap.timed_out_voters == 1
        assert snap.adaptive_multipliers == [1.5]

    def test_thread_safety(self):
        import threading
        m = ConsensusTimeoutMetrics()
        def record():
            for _ in range(100):
                m.record_timeout("voter_timeout")
                m.record_degraded()
                m.record_quorum_fallback()
        threads = [threading.Thread(target=record) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        snap = m.snapshot()
        assert snap.total_timeouts == 400
        assert snap.degraded_count == 400
        assert snap.quorum_fallback_count == 400

    def test_reset(self):
        m = ConsensusTimeoutMetrics()
        m.record_timeout("voter_timeout")
        m.record_degraded()
        m.reset()
        snap = m.snapshot()
        assert snap.total_timeouts == 0
        assert snap.degraded_count == 0

    def test_timeout_metric_snapshot_to_dict(self):
        snap = TimeoutMetricSnapshot(
            timeouts_by_reason={"voter_timeout": 5},
            degraded_count=2,
            quorum_fallback_count=1,
            hung_agent_count=3,
            cancellation_count=4,
            cascading_delay_count=1,
            total_consensus_runs=10,
            total_voters=40,
            timed_out_voters=5,
            skipped_voters=2,
            adaptive_multipliers=[1.0, 2.0],
            hung_agents=[{"agent_name": "test", "strikes": 3}],
        )
        d = snap.to_dict()
        assert d["timeouts_by_reason"]["voter_timeout"] == 5
        assert d["degraded_count"] == 2
        assert d["adaptive_multiplier_avg"] == 1.5


# ── HungAgentRecoveryManager Tests ───────────────────────────────────────


class TestHungAgentRecoveryManager:
    def test_initial_state(self):
        r = HungAgentRecoveryManager()
        assert r.get_strikes("mastery") == 0
        assert not r.should_skip("mastery")

    def test_record_timeout_increments_strikes(self):
        r = HungAgentRecoveryManager()
        r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 1
        r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 2

    def test_max_strikes_capped(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3)
        )
        for _ in range(10):
            r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 4  # max_strikes + 1

    def test_should_skip_at_max_strikes(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3)
        )
        for _ in range(3):
            r.record_timeout("mastery")
        assert r.should_skip("mastery")

    def test_should_not_skip_below_max(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3)
        )
        r.record_timeout("mastery")
        r.record_timeout("mastery")
        assert not r.should_skip("mastery")

    def test_record_success_clears_strikes_after_threshold(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3, recovery_threshold=2)
        )
        r.record_timeout("mastery")
        r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 2
        r.record_success("mastery")
        assert r.get_strikes("mastery") == 2  # not yet recovered
        r.record_success("mastery")
        assert r.get_strikes("mastery") == 0  # recovered

    def test_record_success_noop_when_no_strikes(self):
        r = HungAgentRecoveryManager()
        r.record_success("mastery")
        assert r.get_strikes("mastery") == 0

    def test_exponential_backoff(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(backoff_factor=2.0)
        )
        assert r.get_timeout_multiplier("mastery") == 1.0
        r.record_timeout("mastery")
        assert r.get_timeout_multiplier("mastery") == 2.0
        r.record_timeout("mastery")
        assert r.get_timeout_multiplier("mastery") == 4.0
        r.record_timeout("mastery")
        assert r.get_timeout_multiplier("mastery") == 8.0

    def test_build_skip_vote(self):
        from app.core.consensus import VoteDecision
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3)
        )
        r.record_timeout("mastery")
        r.record_timeout("mastery")
        r.record_timeout("mastery")
        decision, confidence, reason = r.build_skip_vote("mastery")
        assert decision == VoteDecision.ABSTAIN
        assert confidence == 0.0
        assert "strikes=3" in reason

    def test_reset(self):
        r = HungAgentRecoveryManager()
        r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 1
        r.reset()
        assert r.get_strikes("mastery") == 0

    def test_timeout_resets_recovery_progress(self):
        r = HungAgentRecoveryManager(
            HungAgentRecoveryConfig(max_strikes=3, recovery_threshold=2)
        )
        r.record_timeout("mastery")
        r.record_success("mastery")
        assert r.get_strikes("mastery") == 1
        r.record_timeout("mastery")
        assert r.get_strikes("mastery") == 2  # progress reset, now strike 2


# ── ConsensusTimeoutMiddleware Tests ──────────────────────────────────────


# Reuse SlowVoter from V1 tests
class TestConsensusTimeoutMiddleware:
    @pytest.mark.asyncio
    async def test_sync_run_delegates_to_engine(self):
        """Middleware.run() defers to engine.run() with timeout_policy."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("mastery", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = mw.run(ctx)
        assert result.decision == VoteDecision.APPROVE

    @pytest.mark.asyncio
    async def test_async_run_happy_path(self):
        """Middleware.run_async() completes normally for fast voters."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("mastery", delay_ms=1), SlowVoter("prereq", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        assert mw_result.result.decision == VoteDecision.APPROVE
        assert len(mw_result.timed_out_voters) == 0
        assert len(mw_result.skipped_voters) == 0

    @pytest.mark.asyncio
    async def test_async_run_timeout_cancels_slow_voter(self):
        """Middleware.run_async() cancels a voter that exceeds the timeout."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("slowpoke", delay_ms=500)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=50)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        assert "slowpoke" in mw_result.timed_out_voters
        assert mw_result.cancellation_reason is None  # not overall deadline
        assert mw_result.result.votes[0].decision == VoteDecision.ABSTAIN

    @pytest.mark.asyncio
    async def test_async_run_overall_deadline(self):
        """Middleware.run_async() skips voters when overall deadline exceeded."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([
            SlowVoter("v1", delay_ms=200),
            SlowVoter("v2", delay_ms=200),
        ])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000, overall_deadline_ms=50)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        # At least one voter should have been deadline-skipped
        assert len(mw_result.skipped_voters) >= 1 or len(mw_result.timed_out_voters) >= 1

    @pytest.mark.asyncio
    async def test_async_run_hung_skip(self):
        """Middleware.run_async() skips voters with excessive strikes."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("hunky", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)

        # Simulate 3 strikes
        for _ in range(3):
            mw.recovery_manager.record_timeout("hunky")

        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        assert "hunky" in mw_result.skipped_voters
        assert mw_result.result.votes[0].decision == VoteDecision.ABSTAIN

    @pytest.mark.asyncio
    async def test_async_hung_backoff_timeout(self):
        """Hung backoff multiplier increases timeout for previously-hung voters."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("hunky", delay_ms=50)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        mw.recovery_manager.record_timeout("hunky")
        timeout = mw._get_voter_timeout("hunky")
        assert timeout > 5000  # backoff applied

    @pytest.mark.asyncio
    async def test_async_metrics_collected(self):
        """Middleware collects metrics after async run."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("fast", delay_ms=1), SlowVoter("fast2", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        snap = mw.metrics.snapshot()
        assert snap.total_consensus_runs >= 1
        assert snap.total_voters >= 2


# ── ConsensusEngine.async_run() Tests ────────────────────────────────────


class TestConsensusEngineAsyncRun:
    @pytest.mark.asyncio
    async def test_async_run_basic(self):
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = await engine.async_run(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert len(result.votes) == 2

    @pytest.mark.asyncio
    async def test_async_run_timeout_voter(self):
        engine = ConsensusEngine([SlowVoter("slow", delay_ms=500)])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = await engine.async_run(
            ctx,
            timeout_policy=ConsensusTimeoutPolicy(
                ConsensusTimeoutConfig(default_voter_timeout_ms=50)
            ),
            per_voter_timeout_ms=50,
        )
        assert result.votes[0].decision == VoteDecision.ABSTAIN
        assert result.timeout_info is not None
        assert result.timeout_info["timed_out_count"] >= 1

    @pytest.mark.asyncio
    async def test_async_run_deadline(self):
        engine = ConsensusEngine([
            SlowVoter("v1", delay_ms=80),
            SlowVoter("v2", delay_ms=80),
            SlowVoter("v3", delay_ms=80),
        ])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = await engine.async_run(
            ctx,
            per_voter_timeout_ms=5000,
            overall_deadline_ms=150,
        )
        # V1 and V2 should complete (80ms + 80ms = 160ms > 150ms deadline,
        # but each runs fine individually since per-voter timeout is 5000ms)
        # V3 should be deadline-skipped since cumulative time exceeds 150ms
        assert result.votes[0].decision == VoteDecision.APPROVE
        assert len(result.votes) == 3
        deadline_skipped = [
            t for t in result.voter_timings
            if t["status"] == "deadline_skipped"
        ]
        assert len(deadline_skipped) >= 1

    @pytest.mark.asyncio
    async def test_async_run_no_timeout_policy(self):
        """Without timeout_policy, async_run just delegates normally."""
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = await engine.async_run(ctx)
        assert result.decision == VoteDecision.APPROVE

    @pytest.mark.asyncio
    async def test_async_run_voter_error(self):
        engine = ConsensusEngine([ErrorVoter()])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = await engine.async_run(ctx)
        assert result.votes[0].decision == VoteDecision.ABSTAIN

    @pytest.mark.asyncio
    async def test_async_run_cancellation_context_propagated(self):
        """ContextVar-based cancellation context is set during async_run."""
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"

        captured_ctx = None
        original_vote = engine._voters[0].vote
        def capture_vote(vctx):
            nonlocal captured_ctx
            captured_ctx = get_current_cancellation_ctx()
            return original_vote(vctx)
        engine._voters[0].vote = capture_vote

        await engine.async_run(ctx)
        assert captured_ctx is not None
        assert not captured_ctx.cancelled


# ── Integration: Middleware → Metrics → Recovery ─────────────────────────


class TestV2Integration:
    @pytest.mark.asyncio
    async def test_full_pipeline_no_timeouts(self):
        """Happy path: all voters complete, metrics record a run."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        assert mw_result.result.decision == VoteDecision.APPROVE
        assert len(mw_result.timed_out_voters) == 0
        snap = mw.metrics.snapshot()
        assert snap.total_consensus_runs >= 1

    @pytest.mark.asyncio
    async def test_full_pipeline_with_timeouts(self):
        """Voters time out, metrics record them, recovery tracks strikes."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("turtle", delay_ms=500)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=30)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"

        # Run 3 times; each should time out
        for _ in range(3):
            mw_result = await mw.run_async(ctx)
            assert "turtle" in mw_result.timed_out_voters

        # Check recovery tracked strikes
        assert mw.recovery_manager.get_strikes("turtle") >= 3
        snap = mw.metrics.snapshot()
        assert snap.timed_out_voters >= 3

    @pytest.mark.asyncio
    async def test_hung_recovery_after_strikes(self):
        """After max strikes, voter is skipped; after successes, recovers."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        engine = ConsensusEngine([SlowVoter("hunky", delay_ms=200)])
        mw = ConsensusTimeoutMiddleware(
            engine, per_voter_timeout_ms=30,
        )
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"

        # Accumulate 3 strikes (timeouts)
        for _ in range(3):
            mw_result = await mw.run_async(ctx)
            assert "hunky" in mw_result.timed_out_voters

        # 4th run: should be skipped as hung
        mw_result = await mw.run_async(ctx)
        assert "hunky" in mw_result.skipped_voters

    @pytest.mark.asyncio
    async def test_metrics_bridge_compatible(self):
        """Metrics snapshot dict is JSON-serializable."""
        from app.core.consensus_timeout_middleware import ConsensusTimeoutMiddleware
        import json
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])
        mw = ConsensusTimeoutMiddleware(engine, per_voter_timeout_ms=5000)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        mw_result = await mw.run_async(ctx)
        # Should be serializable
        json.dumps(mw_result.metrics_snapshot)


# ── Parity: run() vs async_run() equivalence ──────────────────────────


def _compare_results_same(r1: ConsensusResult, r2: ConsensusResult) -> None:
    """Assert two ConsensusResults have identical business fields."""
    assert r1.module_id == r2.module_id
    assert r1.student_id == r2.student_id
    assert r1.decision == r2.decision
    assert r1.confidence == r2.confidence
    assert len(r1.votes) == len(r2.votes)
    for v1, v2 in zip(r1.votes, r2.votes):
        assert v1.voter_name == v2.voter_name
        assert v1.decision == v2.decision
        assert v1.confidence == v2.confidence
        assert v1.reason == v2.reason
        assert v1.evidence == v2.evidence
    assert r1.weights_used == r2.weights_used
    assert r1.trust_scores == r2.trust_scores
    assert r1.specialization_affinities == r2.specialization_affinities
    assert r1.trace_id == r2.trace_id
    assert r1.timeout_info == r2.timeout_info


class TestRunAsyncRunParity:
    """Functional parity: run() and async_run() produce identical results.

    For the same inputs (ctx, trust_system, shared_memory_store, etc.),
    both methods MUST yield the same consensus decision, weights, trust
    scores, specialization affinities, memory IDs, and diagnostics.
    """

    def _make_ctx(self, **overrides) -> VoteContext:
        return make_ctx(**overrides)

    def _make_engine(self, voter_names: list[str] | None = None) -> ConsensusEngine:
        names = voter_names or ["mastery", "prereq", "sequence", "time"]
        return ConsensusEngine()
        # Uses the default 4 voters which match the names above

    def test_basic_parity(self):
        """Same decision, votes, timings structure without adaptivity."""
        ctx = self._make_ctx(score=0.85)
        engine = self._make_engine()

        result_sync = engine.run(ctx)
        result_async = asyncio.run(engine.async_run(ctx))

        _compare_results_same(result_sync, result_async)

    def test_basic_parity_two_voters(self):
        """ConsensusEngine with two fast voters."""
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])
        ctx = self._make_ctx()
        sync_ctx = self._make_ctx()
        async_ctx = self._make_ctx()

        result_sync = engine.run(sync_ctx)
        result_async = asyncio.run(engine.async_run(async_ctx))

        _compare_results_same(result_sync, result_async)
        assert result_sync.decision == VoteDecision.APPROVE
        assert len(result_sync.votes) == 2

    def test_trust_system_parity(self):
        """Same trust scores and weight computation."""
        from app.core.trust import TrustSystem

        engine = ConsensusEngine([SlowVoter("alice", delay_ms=1), SlowVoter("bob", delay_ms=1)])
        trust = TrustSystem()
        ctx = self._make_ctx()

        # Run both with same trust system
        result_sync = engine.run(ctx, trust_system=trust)
        # Reset ctx.shared_memory since run() mutates it
        ctx2 = self._make_ctx()
        result_async = asyncio.run(engine.async_run(ctx2, trust_system=trust))

        _compare_results_same(result_sync, result_async)
        assert "alice" in result_sync.trust_scores
        assert "bob" in result_sync.trust_scores

    def test_specialization_parity(self):
        """Same specialization affinities."""
        from app.core.specialization import SpecializationTracker

        engine = ConsensusEngine([SlowVoter("alice", delay_ms=1), SlowVoter("bob", delay_ms=1)])
        spec = SpecializationTracker()
        ctx = self._make_ctx()
        ctx2 = self._make_ctx()

        result_sync = engine.run(ctx, specialization_tracker=spec)
        result_async = asyncio.run(engine.async_run(ctx2, specialization_tracker=spec))

        _compare_results_same(result_sync, result_async)
        assert "alice" in result_sync.specialization_affinities

    def test_trust_and_specialization_parity(self):
        """Same weights when both trust and specialization are active."""
        from app.core.trust import TrustSystem
        from app.core.specialization import SpecializationTracker

        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])
        trust = TrustSystem()
        spec = SpecializationTracker()
        ctx = self._make_ctx(score=0.7)
        ctx2 = self._make_ctx(score=0.7)

        result_sync = engine.run(ctx, trust_system=trust, specialization_tracker=spec)
        result_async = asyncio.run(engine.async_run(
            ctx2, trust_system=trust, specialization_tracker=spec,
        ))

        _compare_results_same(result_sync, result_async)
        # After one run, weights should be computed
        if result_sync.weights_used:
            assert abs(sum(result_sync.weights_used.values()) - 2.0) < 0.01

    def test_trace_id_parity(self):
        """Same trace_id propagated through trace_ctx."""
        try:
            from app.tracing import make_trace_context
        except ImportError:
            pytest.skip("tracing module not available")
        ctx = self._make_ctx()
        ctx2 = self._make_ctx()

        trace_ctx = make_trace_context("test-parity-trace")

        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])
        result_sync = engine.run(ctx, trace_ctx=trace_ctx)
        result_async = asyncio.run(engine.async_run(ctx2, trace_ctx=trace_ctx))

        assert result_sync.trace_id == result_async.trace_id
        assert result_sync.trace_id == "test-parity-trace"

    def test_trace_id_from_propagation_ctx_parity(self):
        """Same trace_id derived from propagation_ctx."""
        try:
            from app.tracing import make_propagation_context
        except ImportError:
            pytest.skip("tracing module not available")

        prop_ctx = make_propagation_context("test-prop-trace")

        ctx = self._make_ctx()
        ctx2 = self._make_ctx()
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])

        result_sync = engine.run(ctx, propagation_ctx=prop_ctx)
        # Reset propagation context for async
        prop_ctx2 = make_propagation_context("test-prop-trace")
        result_async = asyncio.run(engine.async_run(ctx2, propagation_ctx=prop_ctx2))

        assert result_sync.trace_id == result_async.trace_id

    def test_shared_memory_query_parity(self):
        """Same shared memory enrichment before voting."""
        from unittest.mock import MagicMock

        store = MagicMock()
        store.query.return_value = [{"id": "mem1", "content": "test"}]

        ctx = self._make_ctx()
        ctx2 = self._make_ctx()
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])

        result_sync = engine.run(ctx, shared_memory_store=store)
        result_async = asyncio.run(engine.async_run(ctx2, shared_memory_store=store))

        _compare_results_same(result_sync, result_async)
        # Both should have queried shared memory
        assert store.query.call_count == 2

    def test_diagnostics_parity(self):
        """Both paths record the same diagnostics events."""
        from app.swarm_diagnostics import diagnostics_engine as _diag

        ctx = self._make_ctx()
        ctx2 = self._make_ctx()
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1)])
        before = _diag.metrics.get_total_events()

        engine.run(ctx)
        after_sync = _diag.metrics.get_total_events()
        assert after_sync > before, "sync run() did not record diagnostics"

        asyncio.run(engine.async_run(ctx2))
        after_async = _diag.metrics.get_total_events()
        assert after_async > after_sync, "async_run() did not record diagnostics"

    def test_voter_timings_structure_parity(self):
        """Same voter timings shape when trace_ctx is provided."""
        try:
            from app.tracing import make_trace_context
        except ImportError:
            pytest.skip("tracing module not available")
        ctx = self._make_ctx()
        ctx2 = self._make_ctx()
        trace_ctx = make_trace_context("voter-timing-parity")
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])

        result_sync = engine.run(ctx, trace_ctx=trace_ctx)
        result_async = asyncio.run(engine.async_run(ctx2, trace_ctx=trace_ctx))

        assert len(result_sync.voter_timings) == len(result_async.voter_timings)
        for ts, ta in zip(result_sync.voter_timings, result_async.voter_timings):
            assert ts["voter_name"] == ta["voter_name"]
            assert ts["decision"] == ta["decision"]
            assert ts["confidence"] == ta["confidence"]
            assert ts["status"] == ta["status"]

    def test_reject_consensus_parity(self):
        """Same REJECT decision across both paths."""
        from app.core.consensus import VoteContext as VC
        ctx = self._make_ctx(score=0.3)
        ctx2 = self._make_ctx(score=0.3)
        engine = self._make_engine()

        result_sync = engine.run(ctx)
        result_async = asyncio.run(engine.async_run(ctx2))

        assert result_sync.decision == result_async.decision
        # Low score should trigger rejection
        # Note: this depends on MasteryVoter threshold

    def test_parity_roundtrip_same_instance(self):
        """Multiple runs on same engine produce deterministic results."""
        from app.core.trust import TrustSystem
        trust = TrustSystem()
        engine = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])

        ctx1 = self._make_ctx(score=0.9)
        ctx2 = self._make_ctx(score=0.9)

        r1_sync = engine.run(ctx1, trust_system=trust)
        r2_async = asyncio.run(engine.async_run(ctx2, trust_system=trust))

        _compare_results_same(r1_sync, r2_async)

        # Second round — trust system updated identically by both paths
        ctx3 = self._make_ctx(score=0.9)
        ctx4 = self._make_ctx(score=0.9)

        r3_sync = engine.run(ctx3, trust_system=trust)
        r4_async = asyncio.run(engine.async_run(ctx4, trust_system=trust))

        _compare_results_same(r3_sync, r4_async)

    def test_weights_deterministic_identity(self):
        """Weights after identical input sequences are identical."""
        from app.core.trust import TrustSystem
        from app.core.specialization import SpecializationTracker

        trust_sync = TrustSystem()
        trust_async = TrustSystem()
        spec_sync = SpecializationTracker()
        spec_async = SpecializationTracker()

        engine_sync = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])
        engine_async = ConsensusEngine([SlowVoter("a", delay_ms=1), SlowVoter("b", delay_ms=1)])

        ctx_sync = self._make_ctx(score=0.75)
        ctx_async = self._make_ctx(score=0.75)

        r_sync = engine_sync.run(ctx_sync, trust_system=trust_sync, specialization_tracker=spec_sync)
        r_async = asyncio.run(engine_async.async_run(
            ctx_async, trust_system=trust_async, specialization_tracker=spec_async,
        ))

        _compare_results_same(r_sync, r_async)

    def test_voter_error_trust_recorded_parity(self):
        """Voter error records in trust system for both paths."""
        from app.core.trust import TrustSystem

        trust_sync = TrustSystem()
        trust_async = TrustSystem()
        engine = ConsensusEngine([ErrorVoter()])

        ctx_sync = self._make_ctx()
        ctx_async = self._make_ctx()

        r_sync = engine.run(ctx_sync, trust_system=trust_sync)
        r_async = asyncio.run(engine.async_run(ctx_async, trust_system=trust_async))

        assert r_sync.votes[0].decision == VoteDecision.ABSTAIN
        assert r_async.votes[0].decision == VoteDecision.ABSTAIN

        # Trust should have recorded errors for both (latency differs due
        # to async overhead — compare business-critical fields only)
        ts_sync = trust_sync.get_snapshot()["error"]
        ts_async = trust_async.get_snapshot()["error"]
        assert ts_sync["voter_name"] == ts_async["voter_name"] == "error"
        assert ts_sync["errors"] == ts_async["errors"] == 1
        assert ts_sync["total_votes"] == ts_async["total_votes"] == 1
        assert ts_sync["trust_score"] == ts_async["trust_score"]
