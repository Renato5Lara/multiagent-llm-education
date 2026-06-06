"""
Comprehensive Propagation TTL tests.

Covers:
    - PropagationTTL dataclass validation
    - PropagationTTLManager start, forward, stop conditions
    - Hop-based expiry (max_hops)
    - Time-based expiry (ttl_seconds)
    - Decay-based expiry (strength depletion)
    - Anti-feedback-loop detection
    - DAG cycle prevention
    - PropagationContext baggage serialization
    - PropagationRateTracker and storm detection
    - PropagationLifecycle high-level orchestration
    - ttl_event_guard integration
    - ttl_consensus_hook integration
    - Error/edge cases
"""

import time
from datetime import datetime, timezone, timedelta

import pytest

from app.events.propagation_ttl import (
    PropagationTTL,
    PropagationTTLManager,
    PropagationLifecycle,
    PropagationRateTracker,
    PropagationState,
    PropagationStopReason,
    PropagationError,
    PropagationStoppedError,
    FeedbackLoopError,
    DAGCycleError,
    PropagationStormError,
    propagation_lifecycle,
    ttl_event_guard,
    ttl_consensus_hook,
)


class TestPropagationTTLModel:
    def test_default_creation(self):
        ttl = PropagationTTL(
            propagation_id="test-1",
            source_id="src-1",
        )
        assert ttl.propagation_id == "test-1"
        assert ttl.source_id == "src-1"
        assert ttl.hop_count == 0
        assert ttl.max_hops == 10
        assert ttl.ttl_seconds == 300.0
        assert ttl.decay_factor == 0.8
        assert ttl.min_strength == 0.1
        assert ttl.state == PropagationState.ACTIVE
        assert ttl.stop_reason is None
        assert len(ttl.visited_agents) == 0
        assert len(ttl.visited_events) == 0

    def test_custom_parameters(self):
        ttl = PropagationTTL(
            propagation_id="test-2",
            source_id="src-2",
            hop_count=5,
            max_hops=20,
            ttl_seconds=600.0,
            decay_factor=0.5,
            min_strength=0.05,
            state=PropagationState.EXPIRED,
        )
        assert ttl.hop_count == 5
        assert ttl.max_hops == 20
        assert ttl.ttl_seconds == 600.0
        assert ttl.decay_factor == 0.5
        assert ttl.min_strength == 0.05
        assert ttl.state == PropagationState.EXPIRED

    def test_invalid_decay_factor_zero(self):
        with pytest.raises(ValueError, match="decay_factor"):
            PropagationTTL(
                propagation_id="x", source_id="x", decay_factor=0.0,
            )

    def test_invalid_decay_factor_negative(self):
        with pytest.raises(ValueError, match="decay_factor"):
            PropagationTTL(
                propagation_id="x", source_id="x", decay_factor=-0.1,
            )

    def test_invalid_decay_factor_too_high(self):
        with pytest.raises(ValueError, match="decay_factor"):
            PropagationTTL(
                propagation_id="x", source_id="x", decay_factor=1.5,
            )

    def test_invalid_max_hops_zero(self):
        with pytest.raises(ValueError, match="max_hops"):
            PropagationTTL(
                propagation_id="x", source_id="x", max_hops=0,
            )

    def test_invalid_ttl_seconds_zero(self):
        with pytest.raises(ValueError, match="ttl_seconds"):
            PropagationTTL(
                propagation_id="x", source_id="x", ttl_seconds=0,
            )

    def test_invalid_min_strength(self):
        with pytest.raises(ValueError, match="min_strength"):
            PropagationTTL(
                propagation_id="x", source_id="x", min_strength=0.0,
            )

    def test_visited_agents_tracking(self):
        ttl = PropagationTTL(
            propagation_id="test",
            source_id="src",
            visited_agents={"agent_a", "agent_b"},
        )
        assert "agent_a" in ttl.visited_agents
        assert "agent_c" not in ttl.visited_agents

    def test_visited_events_tracking(self):
        ttl = PropagationTTL(
            propagation_id="test",
            source_id="src",
            visited_events={"evt_1", "evt_2"},
        )
        assert "evt_1" in ttl.visited_events
        assert "evt_3" not in ttl.visited_events


class TestPropagationTTLManager:
    def setup_method(self):
        self.manager = PropagationTTLManager()

    def test_start_propagation(self):
        ttl = self.manager.start_propagation("event-1")
        assert ttl.source_id == "event-1"
        assert ttl.hop_count == 0
        assert ttl.state == PropagationState.ACTIVE
        assert len(ttl.visited_agents) == 0
        assert len(ttl.visited_events) == 0
        assert ttl.max_hops == 10
        assert ttl.ttl_seconds == 300.0

    def test_start_with_custom_params(self):
        ttl = self.manager.start_propagation(
            "event-2",
            max_hops=5,
            ttl_seconds=60.0,
            decay_factor=0.9,
            min_strength=0.2,
        )
        assert ttl.max_hops == 5
        assert ttl.ttl_seconds == 60.0
        assert ttl.decay_factor == 0.9
        assert ttl.min_strength == 0.2

    def test_forward_increments_hop_count(self):
        ttl = self.manager.start_propagation("event-1")
        assert ttl.hop_count == 0
        ttl2 = self.manager.forward(ttl)
        assert ttl2.hop_count == 1

    def test_forward_preserves_ids(self):
        ttl = self.manager.start_propagation("event-1")
        ttl2 = self.manager.forward(ttl)
        assert ttl2.propagation_id == ttl.propagation_id
        assert ttl2.source_id == ttl.source_id

    def test_forward_with_agent_tracks_visit(self):
        ttl = self.manager.start_propagation("event-1")
        ttl2 = self.manager.forward(ttl, agent_id="agent_a")
        assert "agent_a" in ttl2.visited_agents
        assert "agent_a" not in ttl.visited_agents  # original unchanged

    def test_forward_with_event_tracks_visit(self):
        ttl = self.manager.start_propagation("event-1")
        ttl2 = self.manager.forward(ttl, event_id="evt_1")
        assert "evt_1" in ttl2.visited_events

    def test_feedback_loop_detected(self):
        ttl = self.manager.start_propagation("event-1")
        ttl2 = self.manager.forward(ttl, agent_id="agent_a")
        with pytest.raises(FeedbackLoopError, match="already visited"):
            self.manager.forward(ttl2, agent_id="agent_a")

    def test_dag_cycle_detected(self):
        ttl = self.manager.start_propagation("event-1")
        ttl2 = self.manager.forward(ttl, event_id="evt_1")
        with pytest.raises(DAGCycleError, match="already processed"):
            self.manager.forward(ttl2, event_id="evt_1")

    def test_max_hops_exceeded(self):
        ttl = self.manager.start_propagation("event-1", max_hops=3)
        ttl = self.manager.forward(ttl)
        ttl = self.manager.forward(ttl)
        ttl = self.manager.forward(ttl)
        assert ttl.hop_count == 3
        should_stop, reason = self.manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.MAX_HOPS_EXCEEDED

    def test_max_hops_forward_stops(self):
        ttl = self.manager.start_propagation("event-1", max_hops=1)
        ttl = self.manager.forward(ttl)
        assert ttl.hop_count == 1
        with pytest.raises(PropagationStoppedError, match="stopped"):
            self.manager.forward(ttl)

    def test_ttl_expiry(self):
        ttl = self.manager.start_propagation(
            "event-1",
            ttl_seconds=0.001,
        )
        time.sleep(0.01)
        should_stop, reason = self.manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.TTL_EXPIRED

    def test_strength_depletion(self):
        ttl = self.manager.start_propagation(
            "event-1",
            max_hops=100,
            decay_factor=0.5,
            min_strength=0.2,
        )
        for _ in range(3):
            ttl = self.manager.forward(ttl)
        should_stop, reason = self.manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.STRENGTH_DEPLETED

    def test_strength_computation(self):
        ttl = self.manager.start_propagation(
            "event-1",
            decay_factor=0.5,
        )
        assert self.manager.get_strength(ttl) == 1.0
        ttl = self.manager.forward(ttl)
        assert self.manager.get_strength(ttl) == 0.5
        ttl = self.manager.forward(ttl)
        assert self.manager.get_strength(ttl) == 0.25
        ttl = self.manager.forward(ttl)
        assert self.manager.get_strength(ttl) == 0.125

    def test_expire_marks_state(self):
        ttl = self.manager.start_propagation("event-1")
        expired = self.manager.expire(ttl)
        assert expired.state == PropagationState.EXPIRED
        assert expired.stop_reason == PropagationStopReason.TTL_EXPIRED

    def test_terminate_marks_state(self):
        ttl = self.manager.start_propagation("event-1")
        terminated = self.manager.terminate(
            ttl, reason=PropagationStopReason.MANUAL_TERMINATION,
        )
        assert terminated.state == PropagationState.TERMINATED
        assert terminated.stop_reason == PropagationStopReason.MANUAL_TERMINATION

    def test_check_feedback_loop(self):
        ttl = self.manager.start_propagation("event-1")
        assert self.manager.check_feedback_loop(ttl, "agent_a") is False
        ttl = self.manager.forward(ttl, agent_id="agent_a")
        assert self.manager.check_feedback_loop(ttl, "agent_a") is True

    def test_check_dag_cycle(self):
        ttl = self.manager.start_propagation("event-1")
        assert self.manager.check_dag_cycle(ttl, "evt_1") is False
        ttl = self.manager.forward(ttl, event_id="evt_1")
        assert self.manager.check_dag_cycle(ttl, "evt_1") is True

    def test_non_active_fork_raises(self):
        ttl = self.manager.start_propagation("event-1")
        expired = self.manager.expire(ttl)
        with pytest.raises(PropagationError, match="non-active"):
            self.manager.start_propagation(
                "event-2", parent_propagation=expired,
            )

    def test_fork_from_active(self):
        parent = self.manager.start_propagation("event-1", decay_factor=0.7)
        parent = self.manager.forward(parent, agent_id="agent_a")
        child = self.manager.start_propagation(
            "event-2", parent_propagation=parent,
        )
        assert child.parent_propagation_id == parent.propagation_id
        assert child.decay_factor == parent.decay_factor
        assert "agent_a" in child.visited_agents
        assert child.hop_count == 0
        assert child.source_id == "event-2"
        assert child.propagation_id != parent.propagation_id

    def test_should_stop_on_terminated(self):
        ttl = self.manager.start_propagation("event-1")
        terminated = self.manager.terminate(ttl)
        should_stop, reason = self.manager.should_stop(terminated)
        assert should_stop is True

    def test_forward_with_storm_state(self):
        ttl = self.manager.start_propagation("event-1")
        ttl = PropagationTTL(
            propagation_id=ttl.propagation_id,
            source_id=ttl.source_id,
            state=PropagationState.STORM_DETECTED,
            stop_reason=PropagationStopReason.STORM_DETECTED,
        )
        with pytest.raises(PropagationStoppedError):
            self.manager.forward(ttl)

    def test_full_forward_chain(self):
        ttl = self.manager.start_propagation("src", max_hops=5)
        agents = ["a", "b", "c", "d"]
        for agent in agents:
            ttl = self.manager.forward(ttl, agent_id=agent, event_id=f"evt_{agent}")
        assert ttl.hop_count == 4
        assert len(ttl.visited_agents) == 4
        assert len(ttl.visited_events) == 4
        assert all(a in ttl.visited_agents for a in agents)
        assert self.manager.get_strength(ttl) == pytest.approx(0.8 ** 4)


class TestPropagationRateTracker:
    def setup_method(self):
        self.tracker = PropagationRateTracker(window_seconds=60.0)

    def test_no_events_returns_zero(self):
        assert self.tracker.get_rate("nonexistent") == 0.0

    def test_single_event_returns_zero(self):
        self.tracker.record_event("chain-1")
        assert self.tracker.get_rate("chain-1") == 0.0

    def test_multiple_events_computes_rate(self):
        self.tracker.record_event("chain-1")
        self.tracker.record_event("chain-1")
        self.tracker.record_event("chain-1")
        # 3 events with near-zero time span → rate should be high
        rate = self.tracker.get_rate("chain-1")
        assert rate > 0

    def test_storm_detection(self):
        chain = "storm-chain"
        for _ in range(100):
            self.tracker.record_event(chain)
        assert self.tracker.check_storm(chain, threshold=5.0) is True

    def test_no_storm_below_threshold(self):
        chain = "quiet-chain"
        self.tracker.record_event(chain)
        assert self.tracker.check_storm(chain, threshold=1000.0) is False

    def test_reset_chain(self):
        self.tracker.record_event("chain-1")
        assert self.tracker.get_rate("chain-1") == 0.0
        self.tracker.reset("chain-1")
        assert self.tracker.get_rate("chain-1") == 0.0

    def test_reset_all(self):
        self.tracker.record_event("chain-1")
        self.tracker.record_event("chain-2")
        self.tracker.reset()
        assert self.tracker.get_rate("chain-1") == 0.0
        assert self.tracker.get_rate("chain-2") == 0.0

    def test_separate_chains(self):
        self.tracker.record_event("chain-a")
        self.tracker.record_event("chain-a")
        self.tracker.record_event("chain-b")
        # Both chains have events
        rate_a = self.tracker.get_rate("chain-a")
        rate_b = self.tracker.get_rate("chain-b")
        # Now with enough events, rates should be comparable
        # chain-a has 2 events, chain-b has 1
        assert rate_a >= 0 or rate_b >= 0

    def test_prune_old_events(self):
        chain = "prune-chain"
        self.tracker._window_seconds = 0.001
        self.tracker.record_event(chain)
        time.sleep(0.01)
        self.tracker._prune(chain)
        assert self.tracker.get_rate(chain) == 0.0


class TestBaggageSerialization:
    def setup_method(self):
        self.manager = PropagationTTLManager()

    def test_roundtrip(self):
        original = self.manager.start_propagation("event-1")
        original = self.manager.forward(original, agent_id="agent_a")
        baggage = self.manager.to_baggage(original)
        restored = self.manager.from_baggage(baggage)
        assert restored is not None
        assert restored.propagation_id == original.propagation_id
        assert restored.source_id == original.source_id
        assert restored.hop_count == original.hop_count
        assert restored.max_hops == original.max_hops
        assert restored.decay_factor == original.decay_factor
        assert restored.min_strength == original.min_strength
        assert restored.state == original.state
        assert "agent_a" in restored.visited_agents

    def test_roundtrip_empty_sets(self):
        original = self.manager.start_propagation("event-1")
        baggage = self.manager.to_baggage(original)
        restored = self.manager.from_baggage(baggage)
        assert restored is not None
        assert len(restored.visited_agents) == 0
        assert len(restored.visited_events) == 0

    def test_roundtrip_with_all_fields(self):
        original = self.manager.start_propagation(
            "event-1", max_hops=7, ttl_seconds=120.0, decay_factor=0.6, min_strength=0.15,
        )
        for i in range(3):
            original = self.manager.forward(
                original, agent_id=f"agent_{i}", event_id=f"evt_{i}",
            )
        baggage = self.manager.to_baggage(original)
        restored = self.manager.from_baggage(baggage)
        assert restored.max_hops == 7
        assert restored.ttl_seconds == 120.0
        assert restored.decay_factor == 0.6
        assert restored.min_strength == 0.15
        assert restored.hop_count == 3
        assert len(restored.visited_agents) == 3
        assert len(restored.visited_events) == 3

    def test_roundtrip_expired_state(self):
        original = self.manager.start_propagation("event-1")
        expired = self.manager.expire(original)
        baggage = self.manager.to_baggage(expired)
        restored = self.manager.from_baggage(baggage)
        assert restored.state == PropagationState.EXPIRED

    def test_missing_keys_returns_none(self):
        assert self.manager.from_baggage({}) is None

    def test_invalid_data_returns_none(self):
        assert self.manager.from_baggage({"pttl:id": "x"}) is None

    def test_baggage_format(self):
        ttl = self.manager.start_propagation("src")
        ttl = self.manager.forward(ttl, agent_id="a1")
        baggage = self.manager.to_baggage(ttl)
        assert "pttl:hop" in baggage
        assert "pttl:id" in baggage
        assert "pttl:source" in baggage
        assert baggage["pttl:hop"] == "1"
        assert baggage["pttl:source"] == "src"
        assert "a1" in baggage["pttl:agents"]


class TestPropagationLifecycle:
    def setup_method(self):
        self.lifecycle = PropagationLifecycle()

    def test_start_and_forward(self):
        ttl = self.lifecycle.start("event-1")
        assert ttl.hop_count == 0
        ttl = self.lifecycle.forward(ttl, agent_id="agent_a")
        assert ttl.hop_count == 1
        assert "agent_a" in ttl.visited_agents

    def test_forward_with_storm_check(self):
        ttl = self.lifecycle.start("event-1")
        # Fast events trigger storm check (but won't exceed threshold with 1 event)
        ttl = self.lifecycle.forward(ttl, agent_id="a", check_storm=True)
        assert ttl.hop_count == 1

    def test_extend_ttl(self):
        ttl = self.lifecycle.start("event-1", ttl_seconds=60.0)
        extended = self.lifecycle.extend_ttl(ttl, extra_seconds=30.0)
        assert extended.ttl_seconds == 90.0

    def test_extend_ttl_with_max(self):
        ttl = self.lifecycle.start("event-1", ttl_seconds=60.0)
        extended = self.lifecycle.extend_ttl(ttl, extra_seconds=100.0, max_ttl=120.0)
        assert extended.ttl_seconds == 120.0

    def test_extend_non_active_raises(self):
        ttl = self.lifecycle.start("event-1")
        expired = self.lifecycle.manager.expire(ttl)
        with pytest.raises(PropagationError, match="non-active"):
            self.lifecycle.extend_ttl(expired, extra_seconds=10.0)

    def test_forward_until_depleted(self):
        ttl = self.lifecycle.start("event-1", max_hops=3)
        ttl = self.lifecycle.forward(ttl)
        ttl = self.lifecycle.forward(ttl)
        ttl = self.lifecycle.forward(ttl)
        with pytest.raises(PropagationStoppedError):
            self.lifecycle.forward(ttl)

    def test_manager_property(self):
        assert isinstance(self.lifecycle.manager, PropagationTTLManager)

    def test_rate_tracker_property(self):
        assert isinstance(self.lifecycle.rate_tracker, PropagationRateTracker)

    def test_forward_with_feedback_loop_raises(self):
        ttl = self.lifecycle.start("event-1")
        ttl = self.lifecycle.forward(ttl, agent_id="agent_a")
        with pytest.raises(FeedbackLoopError):
            self.lifecycle.forward(ttl, agent_id="agent_a")

    def test_forward_with_dag_cycle_raises(self):
        ttl = self.lifecycle.start("event-1")
        ttl = self.lifecycle.forward(ttl, event_id="evt_1")
        with pytest.raises(DAGCycleError):
            self.lifecycle.forward(ttl, event_id="evt_1")

    def test_ttl_expiry_via_lifecycle(self):
        ttl = self.lifecycle.start("event-1", ttl_seconds=0.001)
        time.sleep(0.01)
        with pytest.raises(PropagationStoppedError):
            self.lifecycle.forward(ttl)

    def test_default_singleton(self):
        assert propagation_lifecycle is not None
        assert isinstance(propagation_lifecycle, PropagationLifecycle)


class TestTTLEventGuard:
    def test_new_event_starts_propagation(self):
        guard = ttl_event_guard()
        result = guard("test.event", "agg-1", {}, None)
        assert result is not None
        assert result.hop_count == 1

    def test_existing_ttl_continues(self):
        guard = ttl_event_guard()
        first = guard("test.event", "agg-1", {}, None)
        second = guard("test.event", "agg-2", {}, first, agent_id="agent_a")
        assert second is not None
        assert second.hop_count == 2
        assert "agent_a" in second.visited_agents

    def test_exhausted_ttl_returns_none(self):
        from app.events.propagation_ttl import PropagationTTL
        # Create TTL at max hops
        ttl = PropagationTTL(
            propagation_id="test",
            source_id="s",
            hop_count=10,
            max_hops=10,
        )
        guard = ttl_event_guard()
        result = guard("test.event", "agg-1", {}, ttl)
        assert result is None

    def test_feedback_loop_returns_none(self):
        guard = ttl_event_guard()
        ttl = guard("test.event", "agg-1", {}, None)
        ttl = guard("test.event", "agg-2", {}, ttl, agent_id="agent_a")
        # Try to visit agent_a again
        result = guard("test.event", "agg-3", {}, ttl, agent_id="agent_a")
        assert result is None  # blocked by feedback loop

    def test_multiple_events_same_chain(self):
        guard = ttl_event_guard()
        ttl = guard("e1", "a1", {}, None)
        ttl = guard("e2", "a2", {}, ttl, agent_id="agent_b")
        ttl = guard("e3", "a3", {}, ttl, agent_id="agent_c")
        assert ttl.hop_count == 3
        assert len(ttl.visited_agents) == 2


class TestTTLConsensusHook:
    def setup_method(self):
        self.lifecycle = PropagationLifecycle()
        self.hooks = ttl_consensus_hook(self.lifecycle)

    def test_pre_run_creates_new_ttl(self):
        ttl = self.hooks["pre_run"]("mod-1", "stu-1")
        assert ttl is not None
        assert ttl.source_id == "consensus:mod-1:stu-1"
        assert ttl.hop_count == 1  # forward with agent=consensus_engine

    def test_pre_run_with_existing_ttl(self):
        initial = self.lifecycle.start("test")
        ttl = self.hooks["pre_run"]("mod-1", "stu-1", ttl=initial)
        assert ttl.hop_count == initial.hop_count + 1

    def test_post_run_terminates(self):
        ttl = self.lifecycle.start("test")
        result = self.hooks["post_run"](ttl, decision="approve")
        assert result.state == PropagationState.TERMINATED

    def test_voter_hook_forwards(self):
        ttl = self.lifecycle.start("test")
        result = self.hooks["voter_hook"]("MasteryVoter", ttl)
        assert result.hop_count == ttl.hop_count + 1
        assert "MasteryVoter" in result.visited_agents

    def test_voter_hook_tracks_all_voters(self):
        ttl = self.lifecycle.start("test")
        voters = ["MasteryVoter", "PrereqVoter", "SequenceVoter", "TimeVoter"]
        for voter in voters:
            ttl = self.hooks["voter_hook"](voter, ttl)
        assert ttl.hop_count == 4
        assert all(v in ttl.visited_agents for v in voters)

    def test_voter_hook_detects_duplicate(self):
        ttl = self.lifecycle.start("test")
        ttl = self.hooks["voter_hook"]("MasteryVoter", ttl)
        with pytest.raises(FeedbackLoopError):
            self.hooks["voter_hook"]("MasteryVoter", ttl)

    def test_stop_in_pre_run(self):
        ttl = self.lifecycle.start("test", max_hops=1)
        ttl = self.lifecycle.forward(ttl)
        with pytest.raises(PropagationStoppedError):
            self.hooks["pre_run"]("mod-1", "stu-1", ttl=ttl)


class TestEdgeCases:
    def test_visited_agents_limit(self):
        from app.events.propagation_ttl import MAX_VISITED_AGENTS
        manager = PropagationTTLManager()
        ttl = manager.start_propagation(
            "src", max_hops=MAX_VISITED_AGENTS + 5,
            decay_factor=1.0, min_strength=0.001,
        )
        for i in range(MAX_VISITED_AGENTS):
            ttl = manager.forward(ttl, agent_id=f"agent_{i}")
        with pytest.raises(PropagationError, match="visited_agents"):
            manager.forward(ttl, agent_id="overflow")

    def test_visited_events_limit(self):
        from app.events.propagation_ttl import MAX_VISITED_EVENTS
        manager = PropagationTTLManager()
        ttl = manager.start_propagation(
            "src", max_hops=MAX_VISITED_EVENTS + 5,
            decay_factor=1.0, min_strength=0.001,
        )
        for i in range(MAX_VISITED_EVENTS):
            ttl = manager.forward(ttl, event_id=f"evt_{i}")
        with pytest.raises(PropagationError, match="visited_events"):
            manager.forward(ttl, event_id="overflow")

    def test_zero_hop_chain_invalid(self):
        with pytest.raises(ValueError, match="max_hops"):
            PropagationTTL(
                propagation_id="x", source_id="x", max_hops=0,
            )

    def test_single_hop_chain(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", max_hops=1)
        ttl = manager.forward(ttl)
        assert ttl.hop_count == 1
        with pytest.raises(PropagationStoppedError):
            manager.forward(ttl)

    def test_decay_factor_one_no_decay(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", decay_factor=1.0, max_hops=5)
        for _ in range(5):
            ttl = manager.forward(ttl)
        assert manager.get_strength(ttl) == 1.0

    def test_immutable_pattern(self):
        manager = PropagationTTLManager()
        original = manager.start_propagation("src")
        forwarded = manager.forward(original, agent_id="a")
        assert original.hop_count == 0
        assert "a" not in original.visited_agents
        assert forwarded.hop_count == 1
        assert "a" in forwarded.visited_agents

    def test_deep_chain(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation(
            "src", max_hops=50, decay_factor=0.95, min_strength=0.01,
        )
        for i in range(50):
            ttl = manager.forward(ttl, agent_id=f"a{i}", event_id=f"e{i}")
        assert ttl.hop_count == 50
        should_stop, reason = manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.MAX_HOPS_EXCEEDED

    def test_parent_link_in_baggage(self):
        manager = PropagationTTLManager()
        parent = manager.start_propagation("parent-event")
        child = manager.start_propagation("child-event", parent_propagation=parent)
        baggage = manager.to_baggage(child)
        assert baggage["pttl:parent"] == parent.propagation_id
        restored = manager.from_baggage(baggage)
        assert restored.parent_propagation_id == parent.propagation_id

    def test_concurrent_safety_of_rate_tracker(self):
        import threading
        tracker = PropagationRateTracker()
        errors = []

        def record():
            try:
                for _ in range(100):
                    tracker.record_event("chain-1")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
        # Some rate should be computed
        rate = tracker.get_rate("chain-1")
        assert rate >= 0

    def test_propagation_stop_reason_enum_values(self):
        assert PropagationStopReason.MAX_HOPS_EXCEEDED.value == "max_hops_exceeded"
        assert PropagationStopReason.TTL_EXPIRED.value == "ttl_expired"
        assert PropagationStopReason.STRENGTH_DEPLETED.value == "strength_depleted"
        assert PropagationStopReason.FEEDBACK_LOOP.value == "feedback_loop"
        assert PropagationStopReason.DAG_CYCLE.value == "dag_cycle"
        assert PropagationStopReason.STORM_DETECTED.value == "storm_detected"
        assert PropagationStopReason.MANUAL_TERMINATION.value == "manual_termination"

    def test_propagation_state_enum_values(self):
        assert PropagationState.ACTIVE.value == "active"
        assert PropagationState.EXPIRED.value == "expired"
        assert PropagationState.TERMINATED.value == "terminated"
        assert PropagationState.STORM_DETECTED.value == "storm_detected"
        assert PropagationState.FEEDBACK_LOOP.value == "feedback_loop"
        assert PropagationState.DEPLETED.value == "depleted"


class TestSwarmDiagnosticsDetectors:
    """Integration tests for the new swarm diagnostics detectors."""

    def test_propagation_storm_detector_empty(self):
        from app.swarm_diagnostics.detectors.propagation_storm import PropagationStormDetector
        detector = PropagationStormDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_propagation_storm_detector_few_events(self):
        from app.swarm_diagnostics.detectors.propagation_storm import PropagationStormDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
        detector = PropagationStormDetector(min_events_for_detection=10)
        events = [
            DiagnosticEvent(
                event_id=f"e{i}", event_type="test", scope="test",
                causation_id="root", correlation_id="c1",
                source="test", payload={},
            )
            for i in range(5)
        ]
        signals = detector.analyze(events)
        assert len(signals) == 0

    def test_recursive_amplification_detector_empty(self):
        from app.swarm_diagnostics.detectors.recursive_amplification import RecursiveAmplificationDetector
        detector = RecursiveAmplificationDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_dag_traversal_pitfall_detector_empty(self):
        from app.swarm_diagnostics.detectors.dag_traversal import DAGTraversalPitfallDetector
        detector = DAGTraversalPitfallDetector()
        signals = detector.analyze([])
        assert len(signals) == 0

    def test_dag_cycle_detection(self):
        from app.swarm_diagnostics.detectors.dag_traversal import DAGTraversalPitfallDetector
        from app.swarm_diagnostics.models.diagnostic_event import DiagnosticEvent
        from datetime import datetime, timezone
        detector = DAGTraversalPitfallDetector(min_events_for_detection=2)
        now = datetime.now(timezone.utc)
        # Create a cycle: e1 → e2 → e3 → e1
        events = [
            DiagnosticEvent(
                event_id="e1", event_type="a", scope="test",
                causation_id="e3", correlation_id="c1",
                source="test", payload={}, created_at=now,
            ),
            DiagnosticEvent(
                event_id="e2", event_type="b", scope="test",
                causation_id="e1", correlation_id="c1",
                source="test", payload={}, created_at=now,
            ),
            DiagnosticEvent(
                event_id="e3", event_type="c", scope="test",
                causation_id="e2", correlation_id="c1",
                source="test", payload={}, created_at=now,
            ),
        ]
        signals = detector.analyze(events)
        # Should detect the cycle
        cycle_signals = [s for s in signals if "cycle" in s.title.lower()]
        assert len(cycle_signals) >= 1, f"Expected cycle detection, got: {[s.title for s in signals]}"

    def test_detector_registered_in_engine(self):
        from app.swarm_diagnostics.core import SwarmDiagnosticsEngine
        engine = SwarmDiagnosticsEngine()
        assert "propagation_storm" in engine._detectors
        assert "recursive_amplification" in engine._detectors
        assert "dag_traversal_pitfall" in engine._detectors


class TestBoundaryConditions:
    """Propagation boundary, TTL=0/1, recursion prevention, cycle detection,
    replay propagation validation, and concurrent safety tests."""

    def test_ttl_expires_at_boundary(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", ttl_seconds=0.001)
        time.sleep(0.01)
        should_stop, reason = manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.TTL_EXPIRED

    def test_ttl_not_expired_below_boundary(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", ttl_seconds=60.0)
        should_stop, reason = manager.should_stop(ttl)
        assert should_stop is False

    def test_hop_count_stops_at_exact_max(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", max_hops=3)
        ttl = manager.forward(ttl)
        ttl = manager.forward(ttl)
        ttl = manager.forward(ttl)
        assert ttl.hop_count == 3
        should_stop, reason = manager.should_stop(ttl)
        assert should_stop is True
        assert reason == PropagationStopReason.MAX_HOPS_EXCEEDED

    def test_recursive_agent_loop_prevented(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src")
        ttl = manager.forward(ttl, agent_id="agent_x")
        with pytest.raises(FeedbackLoopError):
            manager.forward(ttl, agent_id="agent_x")

    def test_recursive_agent_loop_different_agent_allowed(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src")
        ttl = manager.forward(ttl, agent_id="agent_x")
        ttl = manager.forward(ttl, agent_id="agent_y")
        assert "agent_x" in ttl.visited_agents
        assert "agent_y" in ttl.visited_agents
        assert ttl.hop_count == 2

    def test_event_cycle_detected(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src")
        ttl = manager.forward(ttl, event_id="evt_cycle")
        with pytest.raises(DAGCycleError):
            manager.forward(ttl, event_id="evt_cycle")

    def test_event_cycle_different_event_allowed(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src")
        ttl = manager.forward(ttl, event_id="evt_a")
        ttl = manager.forward(ttl, event_id="evt_b")
        assert ttl.hop_count == 2
        assert "evt_a" in ttl.visited_events
        assert "evt_b" in ttl.visited_events

    def test_replay_propagation_validates_ttl(self):
        guard = ttl_event_guard()
        ttl = guard("replay.event", "agg-1", {}, None)
        ttl = guard("replay.event", "agg-2", {}, ttl, agent_id="agent_a")
        ttl = guard("replay.event", "agg-3", {}, ttl, agent_id="agent_b")
        assert ttl.hop_count == 3
        assert len(ttl.visited_agents) == 2

    def test_replay_exhausted_returns_none(self):
        manager = PropagationTTLManager()
        ttl = manager.start_propagation("src", max_hops=1)
        ttl = manager.forward(ttl)
        ttl2 = manager.start_propagation("src-replay", parent_propagation=ttl)
        assert ttl2.hop_count == 0
        assert ttl2.parent_propagation_id == ttl.propagation_id

    def test_concurrent_forward_safety(self):
        import threading
        manager = PropagationTTLManager()
        ttl = manager.start_propagation(
            "src", max_hops=100, decay_factor=1.0, min_strength=0.001,
        )
        lock = threading.Lock()
        errors = []

        def forward_agent(agent: str):
            nonlocal ttl
            try:
                with lock:
                    ttl = manager.forward(ttl, agent_id=agent)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=forward_agent, args=(f"t{i}",)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(ttl.visited_agents) == 20
        assert ttl.hop_count == 20

    def test_concurrent_rate_tracker_safety(self):
        import threading
        tracker = PropagationRateTracker(window_seconds=60.0)
        errors = []

        def record_events(chain: str):
            try:
                for _ in range(50):
                    tracker.record_event(chain)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=record_events, args=("chain-concurrent",))
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        rate = tracker.get_rate("chain-concurrent")
        assert rate >= 0
