"""
Tests for the Swarm Circuit Breaker System:
  - SwarmCircuitBreaker state machine (CLOSED/OPEN/HALF_OPEN/ISOLATED)
  - CircuitBreakerRegistry
  - AdaptiveRecoveryStrategy
  - SwarmBreakerIsolationStrategy
  - BreakerAwareVoter proxy
  - Circuit breaker swarm diagnostics detectors
"""
from __future__ import annotations

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core.circuit_breaker import (
    CircuitBreakerConfig,
    CircuitState,
    SwarmCircuitBreaker,
    CircuitBreakerRegistry,
    AdaptiveRecoveryStrategy,
    SwarmBreakerIsolationStrategy,
    BreakerAwareVoter,
    wrap_voters_with_breakers,
    BreakerHealth,
)
from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
    BaseVoter,
)
from app.swarm_diagnostics.detectors.circuit_breaker import (
    CircuitBreakerRetryStormDetector,
    CascadingFailureDetector,
    RecoveryInstabilityDetector,
)
from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
from app.swarm_diagnostics.models.anomaly_signal import AnomalyType, Severity


# ── Helpers ────────────────────────────────────────────────────────────


class FakeVoter(BaseVoter):
    def __init__(self, name: str = "test_voter"):
        self._name = name

    @property
    def voter_name(self) -> str:
        return self._name

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        return ConsensusVote(
            voter_name=self._name,
            decision=VoteDecision.APPROVE,
            confidence=1.0,
            reason="OK",
        )


class ErrorVoter(BaseVoter):
    def __init__(self, name: str = "err_voter"):
        self._name = name

    @property
    def voter_name(self) -> str:
        return self._name

    def vote(self, ctx: VoteContext) -> ConsensusVote:
        raise RuntimeError("Simulated voter error")


def make_breaker(agent: str = "mastery", **kwargs) -> SwarmCircuitBreaker:
    config = CircuitBreakerConfig(**kwargs)
    return SwarmCircuitBreaker(agent, config=config)


def make_event(
    event_type: str = "circuit_breaker.transition",
    *,
    source: str = "circuit_breaker",
    state: str = "open",
    agent: str = "mastery",
    error: str | None = None,
) -> DiagnosticEvent:
    from datetime import datetime, timezone
    return DiagnosticEvent(
        event_id="test-id",
        event_type=event_type,
        source=source,
        payload={
            "circuit_breaker": True,
            "state": state,
            "agent": agent,
        },
        error=error,
        created_at=datetime.now(timezone.utc),
    )


# ══════════════════════════════════════════════════════════════════════════
# SwarmCircuitBreaker Tests
# ══════════════════════════════════════════════════════════════════════════


class TestSwarmCircuitBreaker:
    def test_initial_state_closed(self):
        b = make_breaker("mastery")
        assert b.state == CircuitState.CLOSED
        assert b.allow_request() is True

    def test_open_after_failure_threshold(self):
        b = make_breaker("mastery", failure_threshold=3)
        b.record_failure()
        assert b.state == CircuitState.CLOSED
        b.record_failure()
        assert b.state == CircuitState.CLOSED
        b.record_failure()
        assert b.state == CircuitState.OPEN
        assert b.allow_request() is False

    def test_open_rejects_requests(self):
        b = make_breaker("mastery", failure_threshold=1)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        assert b.allow_request() is False

    def test_half_open_after_recovery_timeout(self):
        b = make_breaker("mastery", failure_threshold=1, recovery_timeout_ms=10)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        time.sleep(0.015)  # 15ms > 10ms
        assert b.allow_request() is True  # transitions to half-open
        assert b.state == CircuitState.HALF_OPEN

    def test_half_open_limits_probe_calls(self):
        b = make_breaker("mastery", failure_threshold=1, recovery_timeout_ms=10,
                         half_open_max_calls=2)
        b.record_failure()  # open
        time.sleep(0.015)
        assert b.allow_request() is True  # transitions open→half-open (no probe consumed)
        assert b.allow_request() is True  # probe 1
        assert b.allow_request() is True  # probe 2
        assert b.allow_request() is False  # limit reached

    def test_half_open_success_closes(self):
        b = make_breaker("mastery", failure_threshold=1, recovery_timeout_ms=10,
                         consecutive_successes_to_close=2)
        b.record_failure()
        time.sleep(0.015)
        b.allow_request()  # transitions open→half-open
        assert b.state == CircuitState.HALF_OPEN
        b.record_success()
        assert b.state == CircuitState.HALF_OPEN  # 1/2 successes
        b.record_success()
        assert b.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        b = make_breaker("mastery", failure_threshold=3, recovery_timeout_ms=10,
                         consecutive_successes_to_close=2)
        # Get to half-open
        for _ in range(3):
            b.record_failure()
        time.sleep(0.015)
        b.allow_request()  # transitions open→half-open
        assert b.state == CircuitState.HALF_OPEN
        b.record_failure()
        assert b.state == CircuitState.OPEN

    def test_isolated_after_max_open_cycles(self):
        b = make_breaker("mastery", failure_threshold=1, recovery_timeout_ms=1,
                         max_isolation_strikes=3)
        # Open 2 full cycles → total_open_count hits 3 → isolated
        for i in range(2):
            b.record_failure()  # open
            time.sleep(0.005)
            b.allow_request()  # transitions to half-open
            b.record_failure()  # back to open, increments total_open_count
        # After 2 cycles: total_open_count = 1 (first open) + 2 (reopens) = 3 → isolated
        assert b.state == CircuitState.ISOLATED
        assert b.allow_request() is False

    def test_isolated_auto_recovery_after_timeout(self):
        b = make_breaker("mastery", failure_threshold=1, recovery_timeout_ms=1,
                         max_isolation_strikes=3, isolation_timeout_ms=10)
        # Isolate the breaker with 2 full open cycles
        for i in range(2):
            b.record_failure()
            time.sleep(0.005)
            b.allow_request()
            b.record_failure()
        assert b.state == CircuitState.ISOLATED
        time.sleep(0.015)
        assert b.allow_request() is True  # auto-recovery to open
        assert b.state == CircuitState.OPEN

    def test_record_success_resets_failures(self):
        b = make_breaker("mastery", failure_threshold=3)
        b.record_failure()
        b.record_failure()
        b.record_success()
        assert b.state == CircuitState.CLOSED
        assert b.health().consecutive_failures == 0

    def test_force_open(self):
        b = make_breaker("mastery")
        b.force_open("manual")
        assert b.state == CircuitState.OPEN
        assert b.allow_request() is False

    def test_force_close(self):
        b = make_breaker("mastery", failure_threshold=1)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        b.force_close()
        assert b.state == CircuitState.CLOSED
        assert b.allow_request() is True

    def test_force_isolate(self):
        b = make_breaker("mastery")
        b.force_isolate("maintenance")
        assert b.state == CircuitState.ISOLATED

    def test_build_fallback_vote(self):
        b = make_breaker("mastery", failure_threshold=1)
        b.record_failure()
        fb = b.build_fallback_vote()
        assert fb["decision"] == VoteDecision.ABSTAIN
        assert fb["confidence"] == 0.0
        assert fb["evidence"]["circuit_breaker"] is True
        assert fb["evidence"]["state"] == "open"

    def test_health_snapshot(self):
        b = make_breaker("mastery")
        h = b.health()
        assert isinstance(h, BreakerHealth)
        assert h.agent_name == "mastery"
        assert h.state == CircuitState.CLOSED
        assert h.recovery_remaining_ms == 0.0

    def test_to_dict(self):
        b = make_breaker("mastery")
        d = b.to_dict()
        assert d["agent"] == "mastery"
        assert d["state"] == "closed"

    def test_reset(self):
        b = make_breaker("mastery", failure_threshold=1)
        b.record_failure()
        assert b.state == CircuitState.OPEN
        b.reset()
        assert b.state == CircuitState.CLOSED
        assert b.health().failure_count == 0

    def test_consecutive_failures_tracked(self):
        b = make_breaker("mastery", failure_threshold=5)
        b.record_failure()
        b.record_failure()
        b.record_failure()
        assert b.health().consecutive_failures == 3
        assert b.health().failure_count == 3

    def test_consecutive_successes_tracked(self):
        b = make_breaker("mastery")
        b.record_success()
        b.record_success()
        b.record_success()
        assert b.health().consecutive_successes == 3


# ── CircuitBreakerRegistry Tests ────────────────────────────────────────


class TestCircuitBreakerRegistry:
    def test_get_or_create_creates_new(self):
        r = CircuitBreakerRegistry()
        b = r.get_or_create("mastery")
        assert b is not None
        assert b.state == CircuitState.CLOSED

    def test_get_or_create_returns_existing(self):
        r = CircuitBreakerRegistry()
        b1 = r.get_or_create("mastery")
        b2 = r.get_or_create("mastery")
        assert b1 is b2

    def test_get_returns_none_for_unknown(self):
        r = CircuitBreakerRegistry()
        assert r.get("nonexistent") is None

    def test_record_failure_opens_circuit(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        r.record_failure("mastery")
        b = r.get("mastery")
        assert b.state == CircuitState.OPEN

    def test_record_success(self):
        r = CircuitBreakerRegistry()
        r.record_success("mastery")
        b = r.get("mastery")
        assert b.health().consecutive_successes >= 1

    def test_allow_request(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        assert r.allow_request("mastery") is True
        r.record_failure("mastery")
        assert r.allow_request("mastery") is False

    def test_all_health(self):
        r = CircuitBreakerRegistry()
        r.get_or_create("a")
        r.get_or_create("b")
        r.get_or_create("c")
        health = r.all_health()
        assert len(health) == 3
        assert health["a"]["state"] == "closed"

    def test_health_summary(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        r.get_or_create("a")
        r.get_or_create("b")
        r.record_failure("a")
        summary = r.health_summary()
        assert summary["total_breakers"] == 2
        assert summary["open"] == 1
        assert summary["closed"] == 1

    def test_health_by_state(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        r.get_or_create("healthy")
        r.get_or_create("sick")
        r.record_failure("sick")
        open_breakers = r.health_by_state(CircuitState.OPEN)
        assert len(open_breakers) == 1
        assert open_breakers[0]["agent"] == "sick"

    def test_reset_all(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        r.record_failure("a")
        r.record_failure("b")
        assert r.health_summary()["open"] == 2
        r.reset_all()
        assert r.health_summary()["open"] == 0

    def test_reset_agent(self):
        r = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        r.record_failure("a")
        r.record_failure("b")
        r.reset_agent("a")
        h = r.get("a")
        assert h.state == CircuitState.CLOSED
        assert r.get("b").state == CircuitState.OPEN


# ── AdaptiveRecoveryStrategy Tests ──────────────────────────────────────


class TestAdaptiveRecoveryStrategy:
    def test_base_timeout(self):
        s = AdaptiveRecoveryStrategy(base_timeout_ms=30_000)
        assert s.get_recovery_timeout("mastery") == 30_000

    def test_exponential_backoff(self):
        s = AdaptiveRecoveryStrategy(base_timeout_ms=10_000, backoff_factor=2.0)
        s.record_recovery_failure("mastery")
        assert s.get_recovery_timeout("mastery") == 20_000  # 10k * 2^1
        s.record_recovery_failure("mastery")
        assert s.get_recovery_timeout("mastery") == 40_000  # 10k * 2^2

    def test_max_timeout_clamped(self):
        s = AdaptiveRecoveryStrategy(base_timeout_ms=10_000, backoff_factor=2.0,
                                      max_timeout_ms=25_000)
        s.record_recovery_failure("mastery")
        assert s.get_recovery_timeout("mastery") == 20_000
        s.record_recovery_failure("mastery")
        assert s.get_recovery_timeout("mastery") == 25_000  # clamped

    def test_record_recovery_success_reduces_strikes(self):
        s = AdaptiveRecoveryStrategy(base_timeout_ms=10_000)
        s.record_recovery_failure("mastery")
        s.record_recovery_failure("mastery")
        assert s.get_strikes("mastery") == 2
        s.record_recovery_success("mastery")
        assert s.get_strikes("mastery") == 1

    def test_get_strikes_unknown_agent(self):
        s = AdaptiveRecoveryStrategy()
        assert s.get_strikes("nonexistent") == 0

    def test_reset(self):
        s = AdaptiveRecoveryStrategy()
        s.record_recovery_failure("mastery")
        s.reset()
        assert s.get_strikes("mastery") == 0

    def test_max_strikes_capped(self):
        s = AdaptiveRecoveryStrategy(max_strikes=3)
        for _ in range(10):
            s.record_recovery_failure("mastery")
        assert s.get_strikes("mastery") == 3


# ── SwarmBreakerIsolationStrategy Tests ─────────────────────────────────


class TestSwarmBreakerIsolationStrategy:
    def test_record_open(self):
        s = SwarmBreakerIsolationStrategy()
        s.record_open("mastery")
        s.record_open("prerequisite")
        cascade = s.detect_cascade(threshold=2)
        assert len(cascade) >= 2

    def test_no_cascade_when_few_agents(self):
        s = SwarmBreakerIsolationStrategy(cascade_window_ms=10_000)
        s.record_open("mastery")
        cascade = s.detect_cascade(threshold=3)
        assert cascade == []

    def test_cascade_detects_distinct_agents(self):
        s = SwarmBreakerIsolationStrategy(cascade_window_ms=10_000)
        for agent in ["a", "b", "c"]:
            s.record_open(agent)
            time.sleep(0.001)
        cascade = s.detect_cascade(threshold=3)
        assert len(cascade) >= 3

    def test_old_events_pruned(self):
        s = SwarmBreakerIsolationStrategy(cascade_window_ms=10)
        s.record_open("a")
        time.sleep(0.015)
        s.record_open("b")
        s.record_open("c")
        cascade = s.detect_cascade(threshold=3)
        assert cascade == []  # 'a' was pruned

    def test_reset(self):
        s = SwarmBreakerIsolationStrategy()
        s.record_open("a")
        s.reset()
        cascade = s.detect_cascade(threshold=1)
        assert cascade == []


# ── BreakerAwareVoter Tests ─────────────────────────────────────────────


class TestBreakerAwareVoter:
    def test_normal_vote_passes_through(self):
        registry = CircuitBreakerRegistry()
        voter = FakeVoter("test")
        proxy = BreakerAwareVoter(voter, registry)
        ctx = MagicMock(spec=VoteContext)
        result = proxy.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence == 1.0

    def test_fallback_when_circuit_open(self):
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        voter = FakeVoter("test")
        proxy = BreakerAwareVoter(voter, registry)
        registry.record_failure("test")  # open
        ctx = MagicMock(spec=VoteContext)
        result = proxy.vote(ctx)
        assert result.decision == VoteDecision.ABSTAIN
        assert result.confidence == 0.0
        assert "circuit_breaker" in result.evidence

    def test_fallback_when_isolated(self):
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(
                failure_threshold=1, recovery_timeout_ms=1,
                max_isolation_strikes=2, isolation_timeout_ms=100_000,
            )
        )
        voter = FakeVoter("test")
        proxy = BreakerAwareVoter(voter, registry)
        # Open 2 times to isolate
        for _ in range(2):
            registry.record_failure("test")
            time.sleep(0.005)
            registry.get("test").allow_request()
            registry.record_failure("test")
        assert registry.get("test").state == CircuitState.ISOLATED
        ctx = MagicMock(spec=VoteContext)
        result = proxy.vote(ctx)
        assert result.decision == VoteDecision.ABSTAIN

    def test_error_recorded_as_failure(self):
        registry = CircuitBreakerRegistry()
        voter = ErrorVoter("err")
        proxy = BreakerAwareVoter(voter, registry)
        ctx = MagicMock(spec=VoteContext)
        with pytest.raises(RuntimeError):
            proxy.vote(ctx)
        breaker = registry.get("err")
        assert breaker.health().failure_count == 1

    def test_success_clears_failures(self):
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=2)
        )
        voter = ErrorVoter("err")
        proxy = BreakerAwareVoter(voter, registry)
        ctx = MagicMock(spec=VoteContext)
        # Record a failure
        with pytest.raises(RuntimeError):
            proxy.vote(ctx)
        # Now use a success voter with same name
        voter2 = FakeVoter("err")
        proxy2 = BreakerAwareVoter(voter2, registry)
        result = proxy2.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        breaker = registry.get("err")
        assert breaker.health().failure_count == 1  # prior failure still counted
        assert breaker.health().consecutive_failures == 0  # reset by success

    def test_wrap_voters_with_breakers(self):
        registry = CircuitBreakerRegistry()
        voters = [FakeVoter("a"), FakeVoter("b")]
        wrapped = wrap_voters_with_breakers(voters, registry)
        assert len(wrapped) == 2
        assert all(isinstance(w, BreakerAwareVoter) for w in wrapped)
        assert wrapped[0].voter_name == "a"
        assert wrapped[1].voter_name == "b"


# ══════════════════════════════════════════════════════════════════════════
# Circuit Breaker Detectors Tests
# ══════════════════════════════════════════════════════════════════════════


class TestCircuitBreakerRetryStormDetector:
    def test_no_events_no_signal(self):
        detector = CircuitBreakerRetryStormDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_high_failure_rate_triggers_signal(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=3, window_seconds=60.0,
        )
        events = [
            make_event("breaker.failure", agent="mastery", error="timeout")
            for _ in range(5)
        ]
        signals = detector.analyze(events)
        retry_signals = [s for s in signals if s.anomaly_type == AnomalyType.RETRY_STORM_AGENT]
        assert len(retry_signals) == 1
        assert "mastery" in retry_signals[0].scope

    def test_low_failure_rate_no_signal(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=5, window_seconds=60.0,
        )
        events = [
            make_event("breaker.failure", agent="mastery", error="err")
            for _ in range(3)
        ]
        signals = detector.analyze(events)
        retry_signals = [s for s in signals if s.anomaly_type == AnomalyType.RETRY_STORM_AGENT]
        assert retry_signals == []

    def test_non_cb_events_ignored(self):
        detector = CircuitBreakerRetryStormDetector(
            max_failures_per_window=1, window_seconds=60.0,
        )
        events = [
            DiagnosticEvent(
                event_id="x", event_type="consensus.vote", source="mastery",
                payload={}, created_at=None,
            )
        ]
        signals = detector.analyze(events)
        assert signals == []

    def test_rapid_cycling_detected(self):
        detector = CircuitBreakerRetryStormDetector(
            min_transitions_for_storm=3, window_seconds=60.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = []
        for i, state in enumerate(["closed", "open", "half_open", "open", "half_open"]):
            events.append(DiagnosticEvent(
                event_id=str(i), event_type="breaker.transition",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": state, "agent": "flaky"},
                created_at=now + timedelta(seconds=i * 0.5),
            ))
        signals = detector.analyze(events)
        instability_signals = [s for s in signals if s.anomaly_type == AnomalyType.RECOVERY_INSTABILITY]
        assert len(instability_signals) >= 1
        assert "flaky" in instability_signals[0].scope


class TestCascadingFailureDetector:
    def test_no_open_events_no_signal(self):
        detector = CascadingFailureDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_single_agent_open_no_signal(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
        )
        events = [make_event(agent="mastery")]
        signals = detector.analyze(events)
        assert signals == []

    def test_multiple_agents_open_triggers_cascade(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
            max_agent_gap_seconds=5.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "a"},
                created_at=now,
            ),
            DiagnosticEvent(
                event_id="2", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "b"},
                created_at=now + timedelta(seconds=1),
            ),
        ]
        signals = detector.analyze(events)
        cascade = [s for s in signals if s.anomaly_type == AnomalyType.CASCADING_FAILURE]
        assert len(cascade) >= 1

    def test_agents_outside_window_no_cascade(self):
        detector = CascadingFailureDetector(
            min_agents_for_cascade=2, cascade_window_seconds=30.0,
            max_agent_gap_seconds=1.0,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "a"},
                created_at=now,
            ),
            DiagnosticEvent(
                event_id="2", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "b"},
                created_at=now + timedelta(seconds=10),  # too late
            ),
        ]
        signals = detector.analyze(events)
        cascade = [s for s in signals if s.anomaly_type == AnomalyType.CASCADING_FAILURE]
        assert cascade == []


class TestRecoveryInstabilityDetector:
    def test_no_transitions_no_signal(self):
        detector = RecoveryInstabilityDetector()
        signals = detector.analyze([])
        assert signals == []

    def test_oscillation_detected(self):
        detector = RecoveryInstabilityDetector(
            instability_window_seconds=120.0,
            min_open_half_open_cycles=2,
        )
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        events = []
        for i in range(4):
            events.append(DiagnosticEvent(
                event_id=str(i * 2),
                event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "osc"},
                created_at=now + timedelta(seconds=i * 2),
            ))
            events.append(DiagnosticEvent(
                event_id=str(i * 2 + 1),
                event_type="breaker.half_open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "half_open", "agent": "osc"},
                created_at=now + timedelta(seconds=i * 2 + 1),
            ))
        signals = detector.analyze(events)
        instability = [s for s in signals if s.anomaly_type == AnomalyType.RECOVERY_INSTABILITY]
        assert len(instability) >= 1
        assert "osc" in instability[0].scope

    def test_stable_breaker_no_signal(self):
        detector = RecoveryInstabilityDetector(
            min_open_half_open_cycles=5,
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id="1", event_type="breaker.open",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "open", "agent": "stable"},
                created_at=now,
            ),
        ]
        signals = detector.analyze(events)
        assert signals == []

    def test_repeated_isolation_detected(self):
        detector = RecoveryInstabilityDetector(
            consecutively_isolated_threshold=2,
        )
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        events = [
            DiagnosticEvent(
                event_id=str(i), event_type="breaker.isolated",
                source="circuit_breaker",
                payload={"circuit_breaker": True, "state": "isolated", "agent": "bad"},
                created_at=now,
            )
            for i in range(3)
        ]
        signals = detector.analyze(events)
        isolated = [s for s in signals if "isolation" in s.title.lower()]
        assert len(isolated) >= 1


# ══════════════════════════════════════════════════════════════════════════
# Integration: Registry + Voter Proxy + Consensus Engine
# ══════════════════════════════════════════════════════════════════════════


class TestCircuitBreakerIntegration:
    def test_healthy_voters_pass(self):
        """Healthy voters produce normal consensus results."""
        registry = CircuitBreakerRegistry()
        voters = [FakeVoter("a"), FakeVoter("b")]
        wrapped = wrap_voters_with_breakers(voters, registry)
        engine = ConsensusEngine(wrapped)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = engine.run(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert len(result.votes) == 2

    def test_open_breaker_produces_degraded_vote(self):
        """When a breaker is open, the proxy returns a degraded vote."""
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        # Pre-open the breaker for voter 'a'
        registry.record_failure("a")
        voters = [FakeVoter("a"), FakeVoter("b")]
        wrapped = wrap_voters_with_breakers(voters, registry)
        engine = ConsensusEngine(wrapped)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        result = engine.run(ctx)
        assert result.votes[0].decision == VoteDecision.ABSTAIN  # degraded
        assert result.votes[1].decision == VoteDecision.APPROVE  # healthy
        assert result.votes[0].evidence.get("circuit_breaker") is True

    def test_error_voter_triggers_breaker_open(self):
        """A voter that errors opens the breaker and subsequent calls fail fast."""
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(failure_threshold=1)
        )
        voters = [ErrorVoter("err")]
        wrapped = wrap_voters_with_breakers(voters, registry)
        engine = ConsensusEngine(wrapped)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        # First call: error, breaker opens
        result = engine.run(ctx)
        assert result.votes[0].decision == VoteDecision.ABSTAIN  # error fallback
        breaker = registry.get("err")
        assert breaker.state == CircuitState.OPEN

    def test_breaker_resets_after_successful_votes(self):
        """After enough successes, breaker closes."""
        registry = CircuitBreakerRegistry(
            default_config=CircuitBreakerConfig(
                failure_threshold=1, recovery_timeout_ms=10,
                consecutive_successes_to_close=2,
            )
        )
        # Open the breaker
        registry.record_failure("good")
        time.sleep(0.015)
        registry.get("good").allow_request()  # half-open
        # Now send successes
        voters = [FakeVoter("good")]
        wrapped = wrap_voters_with_breakers(voters, registry)
        engine = ConsensusEngine(wrapped)
        ctx = MagicMock(spec=VoteContext)
        ctx.module_id = "mod1"
        ctx.student_id = "stu1"
        # First success in half-open
        result = engine.run(ctx)
        assert result.votes[0].decision == VoteDecision.APPROVE
        # Second success closes
        result = engine.run(ctx)
        assert result.votes[0].decision == VoteDecision.APPROVE
        breaker = registry.get("good")
        assert breaker.state == CircuitState.CLOSED


# ── Config Validation ─────────────────────────────────────────────────


class TestCircuitBreakerConfigValidation:
    def test_valid_defaults(self):
        c = CircuitBreakerConfig()
        assert c.failure_threshold == 5

    def test_invalid_failure_threshold(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(failure_threshold=0)

    def test_invalid_recovery_timeout(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(recovery_timeout_ms=0)

    def test_invalid_half_open_max_calls(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(half_open_max_calls=0)

    def test_invalid_consecutive_successes(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(consecutive_successes_to_close=0)

    def test_invalid_max_isolation_strikes(self):
        with pytest.raises(ValueError):
            CircuitBreakerConfig(max_isolation_strikes=0)


# ── BreakerHealth Tests ────────────────────────────────────────────────


class TestBreakerHealth:
    def test_health_fields(self):
        h = BreakerHealth(
            agent_name="test",
            state=CircuitState.OPEN,
            failure_count=5,
            success_count=10,
            consecutive_failures=5,
            consecutive_successes=0,
            total_open_count=2,
            last_failure_time_ms=1000.0,
            last_success_time_ms=None,
            recovery_remaining_ms=15_000.0,
            half_open_calls_remaining=0,
            is_isolated=False,
        )
        assert h.agent_name == "test"
        assert h.state == CircuitState.OPEN
        assert h.failure_count == 5
        assert h.recovery_remaining_ms == 15_000.0
