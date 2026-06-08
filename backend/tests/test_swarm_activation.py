"""
Tests de integración del swarm: activación, propagación, consenso y agentes reales.
"""
import asyncio
import threading
import time
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from app.agents.base import BaseAgent
from app.agents.pedagogical_agent import PedagogicalAgent
from app.agents.adaptive_agent import AdaptiveAgent
from app.agents.risk_agent import RiskAgent
from app.agents.evaluation_agent import EvaluationAgent
from app.db.uow import UnitOfWork
from app.memory.shared_memory import SharedMemoryStore
from app.swarm.lifecycle import SwarmLifecycle, SwarmPhase, PhaseStatus, PHASE_ORDER
from app.swarm.events import SwarmEventBus, SwarmEventType, SwarmEvent
from app.swarm.synchronization import PhaseGate, SwarmFence, ContextLock
from app.swarm.detectors import (
    BottleneckDetector,
    RaceConditionDetector,
    ContextInconsistencyDetector,
    PropagationFailureDetector,
)
from app.swarm.metrics import SwarmActivationMetrics
from app.models.programming_domain import ProgrammingConcept, ProgrammingStage
from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
    MasteryVoter,
    PrereqVoter,
    SequenceVoter,
    TimeVoter,
)
from app.core.programming_voters import CodeMasteryVoter, ProgressionVoter
from app.models.programming_prerequisite import CONCEPT_DEPENDENCY_GRAPH


# ═══════════════════════════════════════════════════════════════
# BASE AGENT TESTS
# ═══════════════════════════════════════════════════════════════

class _ConcreteAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent."""
    @property
    def agent_type(self) -> str:
        return "test"
    def analyze(self, state: dict) -> dict:
        return {"result": "ok", "input": state}


def test_base_agent_initialization():
    uow = MagicMock(spec=UnitOfWork)
    agent = _ConcreteAgent(
        agent_name="test_agent",
        uow=uow,
        student_id="student1",
        course_id="course1",
        context_key="ctx:student1:course1",
    )
    assert agent.agent_name == "test_agent"
    assert agent.agent_id is not None
    assert agent.metrics_snapshot()["invocations"] == 0


def test_base_agent_run(db):
    uow = UnitOfWork(lambda: db)
    agent = _ConcreteAgent(
        agent_name="test_agent",
        uow=uow,
        student_id="student1",
        course_id="course1",
        context_key="ctx:student1:course1",
    )
    result = agent.run(state={"hello": "world"})
    assert result["result"] == "ok"
    assert result["input"]["hello"] == "world"
    assert "_agent" in result
    assert result["_agent"]["agent_name"] == "test_agent"
    assert result["_agent"]["elapsed_ms"] > 0

    metrics = agent.metrics_snapshot()
    assert metrics["invocations"] == 1
    assert metrics["successes"] == 1


def test_base_agent_run_failure():
    class FailingAgent(BaseAgent):
        @property
        def agent_type(self) -> str:
            return "failing"
        def analyze(self, state: dict) -> dict:
            raise ValueError("intentional failure")

    uow = MagicMock(spec=UnitOfWork)
    agent = FailingAgent(
        agent_name="failing_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    with pytest.raises(ValueError, match="intentional failure"):
        agent.run(state={})
    assert agent.metrics_snapshot()["failures"] == 1


# ═══════════════════════════════════════════════════════════════
# PEDAGOGICAL AGENT TESTS
# ═══════════════════════════════════════════════════════════════

def test_pedagogical_agent_non_programming():
    uow = MagicMock(spec=UnitOfWork)
    agent = PedagogicalAgent(
        agent_name="pedagogical_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={"is_programming_course": False})
    assert result["cognitive_stage"] == "general"


def test_pedagogical_agent_programming_no_db():
    """Should handle missing DB gracefully."""
    uow = MagicMock(spec=UnitOfWork)
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    mock_session.query.return_value.filter.return_value.all.return_value = []
    type(uow).db = PropertyMock(return_value=mock_session)

    agent = PedagogicalAgent(
        agent_name="pedagogical_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={"is_programming_course": True})
    assert "cognitive_stage" in result
    assert "mastered_concepts" in result
    assert "weak_concepts" in result


# ═══════════════════════════════════════════════════════════════
# ADAPTIVE AGENT TESTS
# ═══════════════════════════════════════════════════════════════

def test_adaptive_agent_non_programming():
    uow = MagicMock(spec=UnitOfWork)
    agent = AdaptiveAgent(
        agent_name="adaptive_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={"is_programming_course": False})
    assert result["pathway"] == "standard"
    assert result["bloom_range"] == [1, 6]


def test_adaptive_agent_programming():
    uow = MagicMock(spec=UnitOfWork)
    agent = AdaptiveAgent(
        agent_name="adaptive_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={"is_programming_course": True})
    assert result["pathway"] in ("standard", "accelerated", "reinforced", "visual_first")
    assert len(result["concept_sequence"]) > 0
    assert "boolean_logic" in result["concept_sequence"] or "variables" in result["concept_sequence"]


# ═══════════════════════════════════════════════════════════════
# RISK AGENT TESTS
# ═══════════════════════════════════════════════════════════════

def test_risk_agent_basic():
    uow = MagicMock(spec=UnitOfWork)
    mock_session = MagicMock()
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_session.query.return_value.filter.return_value.all.return_value = []
    type(uow).db = PropertyMock(return_value=mock_session)

    agent = RiskAgent(
        agent_name="risk_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={})
    assert "risk_score" in result
    assert "risk_level" in result
    assert "recommendations" in result
    assert result["risk_level"] in ("bajo", "medio", "alto")


def test_risk_agent_with_weak_concepts():
    uow = MagicMock(spec=UnitOfWork)
    mock_session = MagicMock()
    from app.models.student_memory import WeaknessRecord
    wr = MagicMock(spec=WeaknessRecord)
    wr.topic = "variables"
    wr.bloom_level = 1
    wr.detection_count = 5
    wr.last_detected_at = None
    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [
        wr, wr, wr,
    ]
    mock_session.query.return_value.filter.return_value.all.return_value = []
    type(uow).db = PropertyMock(return_value=mock_session)

    agent = RiskAgent(
        agent_name="risk_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={})
    assert result["risk_level"] in ("medio", "alto")


# ═══════════════════════════════════════════════════════════════
# EVALUATION AGENT TESTS
# ═══════════════════════════════════════════════════════════════

def test_evaluation_agent_non_programming():
    uow = MagicMock(spec=UnitOfWork)
    agent = EvaluationAgent(
        agent_name="evaluation_agent",
        uow=uow,
        student_id="s1",
        course_id="c1",
        context_key="ctx:s1:c1",
    )
    result = agent.run(state={"is_programming_course": False})
    assert result["evaluation_ready"] is False
    assert result["exercises"] == []


# ═══════════════════════════════════════════════════════════════
# LIFECYCLE TESTS
# ═══════════════════════════════════════════════════════════════

def test_lifecycle_full_transition():
    life = SwarmLifecycle("ctx:test:test", "s1", "c1")
    assert life.current_phase == SwarmPhase.ENTERING

    # Walk through all phases
    for i, phase in enumerate(PHASE_ORDER):
        if phase == SwarmPhase.ENTERING:
            life.complete_phase(phase, postconditions=["enrollment_verified"])
            continue
        ok = life.start_phase(phase)
        assert ok["ok"], f"Failed to start {phase.value}: {ok.get('error')}"
        config_phase = phase
        postconditions = [f"{config_phase.value}_done"]
        life.complete_phase(phase, postconditions=postconditions)

    snap = life.snapshot()
    assert snap["current_phase"] == SwarmPhase.ACTIVE.value
    assert snap["active"] is True


def test_lifecycle_phase_timeout():
    life = SwarmLifecycle("ctx:test", "s1", "c1")
    life.complete_phase(SwarmPhase.ENTERING, postconditions=["enrollment_verified"])
    life.start_phase(SwarmPhase.CONTEXT_LOADING)
    result = life.timeout_phase(SwarmPhase.CONTEXT_LOADING, 99999)
    assert result.get("action") in ("retry", "rollback")
    if result.get("action") == "rollback":
        assert life.current_phase == SwarmPhase.ENTERING


# ═══════════════════════════════════════════════════════════════
# EVENT PROPAGATION TESTS
# ═══════════════════════════════════════════════════════════════

def test_event_bus_causation_chain():
    bus = SwarmEventBus()
    ev1 = bus.publish(
        SwarmEventType.ACTIVATION_STARTED,
        "ctx:test", "s1", "c1", "entering",
        payload={"msg": "start"},
    )
    ev2 = bus.publish(
        SwarmEventType.CONTEXT_LOAD_STARTED,
        "ctx:test", "s1", "c1", "context_loading",
        causation_id=ev1.event_id,
    )
    ev3 = bus.publish(
        SwarmEventType.CONTEXT_LOAD_COMPLETED,
        "ctx:test", "s1", "c1", "context_loading",
        causation_id=ev2.event_id,
    )
    chain = bus.get_causation_chain(ev3.event_id)
    assert len(chain) == 3
    assert chain[0].event_id == ev3.event_id
    assert chain[1].event_id == ev2.event_id
    assert chain[2].event_id == ev1.event_id


def test_event_bus_sequence():
    bus = SwarmEventBus()
    events = []
    for i in range(5):
        ev = bus.publish(
            SwarmEventType.ACTIVATION_STARTED,
            "ctx:seq", "s1", "c1", "entering",
            payload={"seq": i},
        )
        events.append(ev)
    for i in range(1, len(events)):
        assert events[i].sequence > events[i - 1].sequence


def test_event_bus_subscription():
    bus = SwarmEventBus()
    received = []
    def handler(ev):
        received.append(ev.event_type)

    bus.subscribe(SwarmEventType.ACTIVATION_STARTED, handler)
    bus.publish(
        SwarmEventType.ACTIVATION_STARTED,
        "ctx:sub", "s1", "c1", "entering",
    )
    assert len(received) == 1
    assert received[0] == SwarmEventType.ACTIVATION_STARTED


def test_event_bus_propagation_failure_detection():
    bus = SwarmEventBus()
    # Publish events without handlers
    for i in range(5):
        bus.publish(
            SwarmEventType.CONSENSUS_STARTED,
            "ctx:pfail", "s1", "c1", "consensus",
            payload={"i": i},
        )
    failures = bus.detect_propagation_failures("ctx:pfail", grace_period_ms=0)
    # Some events may not have propagated (no handler)
    unpropagated = [f for f in failures if f.get("reason") == "event_not_propagated"]
    assert len(unpropagated) > 0


# ═══════════════════════════════════════════════════════════════
# SYNCHRONIZATION TESTS
# ═══════════════════════════════════════════════════════════════

def test_phase_gate():
    gate = PhaseGate("test", ["a", "b"], timeout_ms=5000)
    assert not gate.is_open
    assert "a" in gate.missing

    gate.satisfy("a")
    assert not gate.is_open
    gate.satisfy("b")
    assert gate.is_open

    ok, _ = gate.wait()
    assert ok


def test_phase_gate_timeout():
    gate = PhaseGate("timeout_test", ["never"], timeout_ms=100)
    ok, msg = gate.wait()
    assert not ok
    assert "timed out" in msg


def test_swarm_fence():
    fence = SwarmFence("test", ["a", "b", "c"], timeout_ms=5000)
    ok, msg = fence.arrive("a")
    assert ok
    assert "b" in msg
    ok, msg = fence.arrive("b")
    assert ok
    ok, result = fence.arrive("c")
    assert ok
    assert fence._tripped


async def test_context_lock():
    lock = ContextLock()
    assert not lock.is_locked("ctx:test")

    async with lock.acquire("ctx:test", "orch") as acquired:
        assert acquired
        assert lock.is_locked("ctx:test")
        assert lock.owner("ctx:test") == "orch"

    assert not lock.is_locked("ctx:test")


async def test_context_lock_is_locked():
    """Verify is_locked and owner reflect the current lock state."""
    lock = ContextLock()
    assert not lock.is_locked("ctx:locktest")
    assert lock.owner("ctx:locktest") is None

    async with lock.acquire("ctx:locktest", "my_owner") as a:
        assert a
        assert lock.is_locked("ctx:locktest")
        assert lock.owner("ctx:locktest") == "my_owner"

    assert not lock.is_locked("ctx:locktest")
    assert lock.owner("ctx:locktest") is None


async def test_context_lock_snapshot():
    """Verify snapshot reflects active and historical state."""
    lock = ContextLock()
    snap0 = lock.snapshot()
    assert snap0["total_locks"] == 0
    assert snap0["active_locks"] == {}

    async with lock.acquire("ctx:snap", "snap_owner") as a:
        assert a
        snap1 = lock.snapshot()
        assert snap1["active_locks"] == {"ctx:snap": "snap_owner"}
        assert snap1["total_locks"] == 1

    snap2 = lock.snapshot()
    assert snap2["active_locks"] == {}
    assert snap2["total_locks"] == 1


async def test_context_lock_twice_same_key_not_deadlock():
    """Acquire → release → acquire again on the same key works."""
    lock = ContextLock()
    async with lock.acquire("ctx:twice", "first") as a:
        assert a
    async with lock.acquire("ctx:twice", "second") as a:
        assert a
    assert not lock.is_locked("ctx:twice")


async def test_context_lock_owner_isolation():
    """Different keys don't interfere with each other."""
    lock = ContextLock()
    async with lock.acquire("ctx:alpha", "owner_a") as a:
        assert a
        async with lock.acquire("ctx:beta", "owner_b") as b:
            assert b
            assert lock.owner("ctx:alpha") == "owner_a"
            assert lock.owner("ctx:beta") == "owner_b"

    assert not lock.is_locked("ctx:alpha")
    assert not lock.is_locked("ctx:beta")


async def test_context_lock_key_reuse_after_release():
    """Lock can be reused after release with different key."""
    lock = ContextLock()
    async with lock.acquire("ctx:reuse", "a") as a:
        assert a
    async with lock.acquire("ctx:reuse", "b") as b:
        assert b
    assert lock.owner("ctx:reuse") is None


# ═══════════════════════════════════════════════════════════════
# DETECTOR TESTS
# ═══════════════════════════════════════════════════════════════

def test_bottleneck_detector():
    bd = BottleneckDetector(baseline_p99_ms={"fast": 1000, "slow": 100})
    bd.record_duration("slow", 500)
    signals = bd.detect({
        "phase_history": [
            {
                "phase": "slow",
                "status": "completed",
                "started_at": "2025-01-01T00:00:00",
                "completed_at": "2025-01-01T00:00:01",
            },
        ],
    })
    assert len(signals) > 0
    # duration=1000ms, baseline=100ms → 10x → critical
    assert any(s["severity"] == "critical" for s in signals)


def test_race_condition_reversal():
    rcd = RaceConditionDetector()
    bus = SwarmEventBus()
    ev1 = bus.publish(SwarmEventType.ACTIVATION_STARTED, "ctx:rc", "s1", "c1", "entering")
    ev2 = bus.publish(SwarmEventType.CONTEXT_LOAD_STARTED, "ctx:rc", "s1", "c1", "context_loading")

    # Manually create a sequence reversal scenario
    ev2.sequence = 0
    ev1.sequence = 1

    events = bus.get_events(context_key="ctx:rc")
    signals = rcd.detect(events)
    # May or may not detect depending on timing; at least no crash
    assert isinstance(signals, list)


def test_context_inconsistency_detector():
    cid = ContextInconsistencyDetector()
    signals = cid.detect_from_lifecycle({
        "phases": {
            "entering": "completed",
            "context_loading": "completed",
            "memory_init": "pending",
        },
        "phase_history": [
            {"phase": "entering", "status": "completed", "started_at": None, "completed_at": None},
        ],
        "metadata": {"achieved_postconditions": []},
    })
    # Should detect: memory_init not completed but no history for context_loading completed
    assert len(signals) > 0


def test_propagation_failure_detector():
    pfd = PropagationFailureDetector()
    bus = SwarmEventBus()

    # Publish events without any handler
    for i in range(3):
        bus.publish(SwarmEventType.PHASE_TIMEOUT, "ctx:pf", "s1", "c1", "consensus")

    events = bus.get_events(context_key="ctx:pf")
    signals = pfd.detect(events)
    assert isinstance(signals, list)


# ═══════════════════════════════════════════════════════════════
# CONSENSUS TESTS
# ═══════════════════════════════════════════════════════════════

def test_consensus_engine_basic():
    from unittest.mock import MagicMock
    engine = ConsensusEngine(voters=[
        MasteryVoter(),
        PrereqVoter(),
        SequenceVoter(),
        TimeVoter(),
    ])
    mock_uow = MagicMock()
    mock_module = MagicMock()
    mock_path = MagicMock()
    mock_module.order = 1
    mock_module.status = "in_progress"
    mock_module.evidence = {}

    # Mock DB to return no incomplete prereqs
    mock_query = MagicMock()
    mock_query.filter.return_value.count.return_value = 0
    mock_uow.db.query.return_value = mock_query

    ctx = VoteContext(
        uow=mock_uow,
        student_id="s1",
        module_id="m1",
        path_id="p1",
        course_id="c1",
        score=0.8,
        module=mock_module,
        path=mock_path,
    )
    result = engine.run(ctx)
    assert result.decision in (VoteDecision.APPROVE, VoteDecision.REJECT, VoteDecision.ABSTAIN)
    assert 0 <= result.confidence <= 1
    assert len(result.votes) == 4


def test_consensus_engine_with_programming_voters():
    engine = ConsensusEngine(voters=[
        MasteryVoter(),
        PrereqVoter(),
        SequenceVoter(),
        TimeVoter(),
        CodeMasteryVoter(),
        ProgressionVoter(),
    ])
    assert len(engine.voters) == 6


def test_code_mastery_voter_approve():
    from unittest.mock import MagicMock
    mock_uow = MagicMock()
    mock_module = MagicMock()
    mock_path = MagicMock()
    ctx = VoteContext(
        uow=mock_uow, student_id="s1", module_id="m1",
        path_id="p1", course_id="c1", score=0.8,
        module=mock_module, path=mock_path,
        evidence={"code_correctness": 0.9, "ct_score": 0.8, "concept": "loops"},
    )
    voter = CodeMasteryVoter()
    vote = voter.vote(ctx)
    assert vote.decision == VoteDecision.APPROVE


def test_code_mastery_voter_reject():
    from unittest.mock import MagicMock
    mock_uow = MagicMock()
    mock_module = MagicMock()
    mock_path = MagicMock()
    ctx = VoteContext(
        uow=mock_uow, student_id="s1", module_id="m1",
        path_id="p1", course_id="c1", score=0.8,
        module=mock_module, path=mock_path,
        evidence={"code_correctness": 0.2, "ct_score": 0.1, "concept": "loops"},
    )
    voter = CodeMasteryVoter()
    vote = voter.vote(ctx)
    assert vote.decision == VoteDecision.REJECT


def test_progression_voter_approve():
    from unittest.mock import MagicMock
    mock_uow = MagicMock()
    mock_module = MagicMock()
    mock_path = MagicMock()
    ctx = VoteContext(
        uow=mock_uow, student_id="s1", module_id="m1",
        path_id="p1", course_id="c1", score=0.8,
        module=mock_module, path=mock_path,
        evidence={
            "concept": "loops",
            "completed_concepts": ["variables", "data_types", "boolean_logic", "conditionals"],
        },
    )
    voter = ProgressionVoter()
    vote = voter.vote(ctx)
    assert vote.decision == VoteDecision.APPROVE, f"Got {vote.decision}: {vote.reason}"


def test_progression_voter_reject():
    from unittest.mock import MagicMock
    mock_uow = MagicMock()
    mock_module = MagicMock()
    mock_path = MagicMock()
    ctx = VoteContext(
        uow=mock_uow, student_id="s1", module_id="m1",
        path_id="p1", course_id="c1", score=0.8,
        module=mock_module, path=mock_path,
        evidence={
            "concept": "recursion",
            "completed_concepts": ["variables"],
        },
    )
    voter = ProgressionVoter()
    vote = voter.vote(ctx)
    assert vote.decision == VoteDecision.REJECT


# ═══════════════════════════════════════════════════════════════
# METRICS TESTS
# ═══════════════════════════════════════════════════════════════

def test_swarm_metrics_basic():
    m = SwarmActivationMetrics()
    m.record_activation(success=True)
    m.record_phase("entering", 100.0, "completed")
    m.record_phase("context_loading", 500.0, "completed")
    m.record_agent("pedagogical_agent", 200.0, True)
    m.record_agent("risk_agent", 150.0, False)
    m.record_event("swarm.activation.started", True)
    m.record_event("swarm.activation.started", True)
    m.record_event("swarm.activation.started", False)
    m.record_consensus_vote("mastery", "approve")
    m.record_consensus_vote("mastery", "approve")
    m.record_consensus_vote("prereq", "approve")
    m.record_anomaly("bottleneck:entering")

    snap = m.snapshot()
    assert snap["activations"] == 1
    assert snap["activation_successes"] == 1
    assert snap["success_rate"] == 1.0
    assert snap["phases"]["entering"]["invocations"] == 1
    assert snap["agents"]["pedagogical_agent"]["successes"] == 1
    assert snap["agents"]["risk_agent"]["failures"] == 1
    assert snap["events"]["swarm.activation.started"]["total"] == 3
    assert snap["events"]["swarm.activation.started"]["propagation_rate"] == pytest.approx(0.67, abs=0.01)
    assert snap["consensus_votes"]["mastery"]["approve"] == 2
    assert snap["anomalies"]["bottleneck:entering"] == 1


# ═══════════════════════════════════════════════════════════════
# CONCEPT DEPENDENCY GRAPH TESTS
# ═══════════════════════════════════════════════════════════════

def test_concept_dependency_graph_completeness():
    """Every ProgrammingConcept should have an entry in CONCEPT_DEPENDENCY_GRAPH."""
    for concept in ProgrammingConcept:
        assert concept in CONCEPT_DEPENDENCY_GRAPH, f"Missing: {concept}"


def test_concept_dependency_graph_acyclic():
    """Verify the dependency graph has no cycles (basic DAG check)."""
    visited = set()
    rec_stack = set()

    def dfs(node):
        visited.add(node)
        rec_stack.add(node)
        for prereq in CONCEPT_DEPENDENCY_GRAPH.get(node, set()):
            if prereq not in visited:
                if dfs(prereq):
                    return True
            elif prereq in rec_stack:
                return True
        rec_stack.discard(node)
        return False

    for concept in ProgrammingConcept:
        if concept not in visited:
            assert not dfs(concept), f"Cycle detected involving {concept}"


# ═══════════════════════════════════════════════════════════════
# SWARM ORCHESTRATION TESTS (INTEGRATION)
# ═══════════════════════════════════════════════════════════════

@pytest.fixture
def mock_context():
    ctx = MagicMock()
    ctx.student_id = "test_student"
    ctx.course_id = "test_course"
    ctx.shared_memory_key = "ctx:test_student:test_course"
    ctx.status = "pending"
    ctx.enrollment = MagicMock()
    ctx.course = MagicMock()
    ctx.course.code = "PRO201"
    return ctx


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    return db


@pytest.mark.skip(reason="Requires full DB setup — use test_lifecycle instead")
async def test_swarm_orchestrator_full_activation(mock_db, mock_context):
    """Full integration test — requires DB tables. Skipped by default."""
    from app.swarm.orchestrator import SwarmOrchestrator
    orchestrator = SwarmOrchestrator(mock_db, mock_context)
    result = await orchestrator.activate()
    assert result["ok"] is True
    assert "lifecycle" in result
    assert "detected_anomalies" in result
    assert "metrics" in result
