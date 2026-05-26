"""Tests for observability: tracing, metrics, and diagnostics."""

import threading
import time
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.observability.tracing import (
    TraceContext,
    TracingSpan,
    get_current_trace,
    set_current_trace,
    trace_decay,
    new_trace_id,
    new_span_id,
)
from app.observability.consensus_metrics import ConsensusMetrics, VoterStats
from app.observability.swarm_diagnostics import (
    DecisionTimeline,
    DecisionRecord,
    EventChainTracker,
    SwarmDiagnostics,
)
from app.core.consensus import (
    ConsensusEngine,
    ConsensusResult,
    ConsensusVote,
    VoteContext,
    VoteDecision,
    MasteryVoter,
    PrereqVoter,
    SequenceVoter,
    TimeVoter,
)


# =============================================================================
# 1. TraceContext
# =============================================================================


class TestTraceContext:
    def test_new_creates_root_context(self):
        ctx = TraceContext.new()
        assert ctx.trace_id is not None
        assert ctx.span_id is not None
        assert ctx.parent_span_id is None
        assert ctx.causation_id is None

    def test_new_with_correlation(self):
        ctx = TraceContext.new(correlation_id="my-corr", emitted_by="test")
        assert ctx.correlation_id == "my-corr"
        assert ctx.emitted_by == "test"

    def test_child_inherits_trace_and_correlation(self):
        parent = TraceContext.new(correlation_id="root-corr")
        child = parent.child("child-op")
        assert child.trace_id == parent.trace_id
        assert child.parent_span_id == parent.span_id
        assert child.correlation_id == parent.correlation_id
        assert child.span_id != parent.span_id
        assert child.emitted_by == "child-op"

    def test_to_dict_roundtrip(self):
        original = TraceContext.new(
            correlation_id="corr", causation_id="caus", emitted_by="svc",
        )
        data = original.to_dict()
        restored = TraceContext.from_dict(data)
        assert restored.trace_id == original.trace_id
        assert restored.span_id == original.span_id
        assert restored.parent_span_id == original.parent_span_id
        assert restored.correlation_id == original.correlation_id
        assert restored.causation_id == original.causation_id
        assert restored.emitted_by == original.emitted_by

    def test_unique_ids(self):
        ids = [new_trace_id() for _ in range(100)]
        assert len(set(ids)) == 100

        spans = [new_span_id() for _ in range(100)]
        assert len(set(spans)) == 100


# =============================================================================
# 2. TracingSpan
# =============================================================================


class TestTracingSpan:
    def test_span_timing(self):
        ctx = TraceContext.new()
        span = TracingSpan(ctx, "test_op")
        span.start()
        time.sleep(0.01)
        span.finish()

        assert span.start_time is not None
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 8.0  # at least 8ms

    def test_span_context_manager(self):
        ctx = TraceContext.new()
        with TracingSpan(ctx, "cm_op") as span:
            span.set_tag("key", "value")

        assert span.duration_ms is not None
        assert span.tags["key"] == "value"

    def test_span_to_dict(self):
        ctx = TraceContext.new()
        with TracingSpan(ctx, "dict_op") as span:
            pass

        d = span.to_dict()
        assert d["operation"] == "dict_op"
        assert d["trace_id"] == ctx.trace_id
        assert d["span_id"] == ctx.span_id
        assert d["duration_ms"] is not None

    def test_context_var_propagation(self):
        trace_decay()
        assert get_current_trace() is None

        ctx = TraceContext.new()
        with TracingSpan(ctx, "prop_test") as span:
            current = get_current_trace()
            assert current is not None
            assert current["trace_id"] == ctx.trace_id
            assert current["span_id"] == ctx.span_id

        # After span exits, context var is still set (from last span)
        # That's fine — the span doesn't clean it up automatically

    def test_set_current_trace(self):
        ctx = TraceContext.new()
        set_current_trace(ctx.to_dict())
        assert get_current_trace()["trace_id"] == ctx.trace_id
        trace_decay()
        assert get_current_trace() is None


# =============================================================================
# 3. ConsensusMetrics
# =============================================================================


class TestConsensusMetrics:
    def make_result(self, decision: VoteDecision, unanimous: bool = True) -> ConsensusResult:
        votes = [
            ConsensusVote(voter_name="voter1", decision=decision, confidence=0.9),
        ]
        if not unanimous:
            votes.append(
                ConsensusVote(voter_name="voter2", decision=VoteDecision.ABSTAIN, confidence=0.5),
            )
        return ConsensusResult(
            module_id="mod-1",
            student_id="stu-1",
            decision=decision,
            confidence=0.9,
            votes=votes,
        )

    def test_records_run_counts(self):
        m = ConsensusMetrics()
        m.record_run(self.make_result(VoteDecision.APPROVE), 10.0)
        assert m.total_runs == 1
        assert m.approvals == 1

        m.record_run(self.make_result(VoteDecision.REJECT), 5.0)
        assert m.total_runs == 2
        assert m.rejections == 1

    def test_records_abstention(self):
        m = ConsensusMetrics()
        m.record_run(self.make_result(VoteDecision.ABSTAIN), 3.0)
        assert m.abstentions == 1

    def test_disagreement_detection(self):
        m = ConsensusMetrics()
        result = self.make_result(VoteDecision.APPROVE, unanimous=False)
        m.record_run(result, 10.0)
        assert m.disagreements == 1

    def test_latency_tracking(self):
        m = ConsensusMetrics()
        m.record_run(self.make_result(VoteDecision.APPROVE), 100.0)
        m.record_run(self.make_result(VoteDecision.APPROVE), 200.0)
        snap = m.get_snapshot()
        assert snap["min_latency_ms"] == 100.0
        assert snap["max_latency_ms"] == 200.0
        assert snap["avg_latency_ms"] == 150.0

    def test_voter_stats(self):
        m = ConsensusMetrics()
        vote = ConsensusVote(
            voter_name="mastery", decision=VoteDecision.REJECT,
            confidence=0.8, reason="Score too low",
        )
        m.record_vote(vote, 5.0)

        snap = m.get_snapshot()
        assert "mastery" in snap["voter_stats"]
        vs = snap["voter_stats"]["mastery"]
        assert vs["votes"] == 1
        assert vs["rejections"] == 1

    def test_rejection_reasons_tracked(self):
        m = ConsensusMetrics()
        vote = ConsensusVote(
            voter_name="mastery", decision=VoteDecision.REJECT,
            confidence=0.8, reason="Score 0.3 below threshold",
        )
        m.record_vote(vote, 1.0)
        assert ("Score 0.3 below threshold") in dict(m.rejection_reasons)

    def test_module_completed_locked(self):
        m = ConsensusMetrics()
        m.record_module_completed()
        m.record_module_locked()
        snap = m.get_snapshot()
        assert snap["modules_completed"] == 1
        assert snap["modules_locked"] == 1

    def test_rollback_recorded(self):
        m = ConsensusMetrics()
        m.record_rollback()
        assert m.rollbacks == 1

    def test_error_recorded(self):
        m = ConsensusMetrics()
        m.record_error()
        assert m.errors == 1

    def test_reset_clears(self):
        m = ConsensusMetrics()
        m.record_run(self.make_result(VoteDecision.APPROVE), 10.0)
        m.reset()
        assert m.total_runs == 0
        assert m.approvals == 0

    def test_thread_safety(self):
        m = ConsensusMetrics()
        errors = []

        def worker():
            try:
                for _ in range(50):
                    m.record_run(self.make_result(VoteDecision.APPROVE), 1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert m.total_runs == 200

    def test_snapshot_approval_rate(self):
        m = ConsensusMetrics()
        m.record_run(self.make_result(VoteDecision.APPROVE), 10.0)
        m.record_run(self.make_result(VoteDecision.APPROVE), 10.0)
        m.record_run(self.make_result(VoteDecision.REJECT), 10.0)
        snap = m.get_snapshot()
        assert snap["approval_rate"] == round(2 / 3, 4)
        assert snap["rejection_rate"] == round(1 / 3, 4)


class TestVoterStats:
    def test_records_vote_decisions(self):
        vs = VoterStats()
        vs.record(VoteDecision.APPROVE, 5.0, "All good")
        assert vs.votes == 1
        assert vs.approvals == 1

        vs.record(VoteDecision.REJECT, 10.0, "Bad")
        assert vs.votes == 2
        assert vs.rejections == 1

    def test_latency_bounds(self):
        vs = VoterStats()
        vs.record(VoteDecision.APPROVE, 100.0, "")
        vs.record(VoteDecision.APPROVE, 50.0, "")
        assert vs.min_latency_ms == 50.0
        assert vs.max_latency_ms == 100.0
        assert vs.avg_latency_ms == 75.0


# =============================================================================
# 4. DecisionTimeline
# =============================================================================


class TestDecisionTimeline:
    def make_record(self, decision="approve", module_id="mod-1"):
        return DecisionRecord(
            module_id=module_id,
            student_id="stu-1",
            decision=decision,
            confidence=0.9,
            trace_id="trace-1",
            duration_ms=10.0,
            num_voters=4,
            unanimous=True,
            approve_ratio=1.0,
            reject_ratio=0.0,
            computed_at=datetime.now(timezone.utc),
        )

    def test_append_and_records(self):
        tl = DecisionTimeline()
        assert len(tl.records) == 0

        tl.append(self.make_record())
        assert len(tl.records) == 1

    def test_filter_by_student(self):
        tl = DecisionTimeline()
        tl.append(self.make_record(module_id="mod-1"))
        tl.append(self.make_record(module_id="mod-2"))
        assert len(tl.filter_by_student("stu-1")) == 2
        assert len(tl.filter_by_student("stu-2")) == 0

    def test_filter_by_module(self):
        tl = DecisionTimeline()
        tl.append(self.make_record(module_id="mod-1", decision="approve"))
        tl.append(self.make_record(module_id="mod-2", decision="reject"))
        mod1s = tl.filter_by_module("mod-1")
        assert len(mod1s) == 1
        assert mod1s[0].module_id == "mod-1"

    def test_last_decision(self):
        tl = DecisionTimeline()
        r1 = self.make_record(module_id="mod-1", decision="reject")
        r2 = self.make_record(module_id="mod-1", decision="approve")
        tl.append(r1)
        tl.append(r2)
        last = tl.last_decision("mod-1")
        assert last is not None
        assert last.decision == "approve"

    def test_last_decision_none(self):
        tl = DecisionTimeline()
        assert tl.last_decision("non-existent") is None

    def test_to_dict(self):
        tl = DecisionTimeline()
        tl.append(self.make_record())
        d = tl.to_dict()
        assert len(d) == 1
        assert d[0]["module_id"] == "mod-1"
        assert d[0]["decision"] == "approve"

    def test_from_consensus_result(self):
        votes = [
            ConsensusVote(voter_name="mastery", decision=VoteDecision.APPROVE, confidence=0.9),
            ConsensusVote(voter_name="sequence", decision=VoteDecision.REJECT, confidence=1.0,
                          reason="Prerequisite not met"),
        ]
        result = ConsensusResult(
            module_id="mod-1",
            student_id="stu-1",
            decision=VoteDecision.REJECT,
            confidence=0.5,
            votes=votes,
            trace_id="trace-abc",
        )
        record = DecisionTimeline.from_consensus_result(result, 15.0)
        assert record.module_id == "mod-1"
        assert record.decision == "reject"
        assert record.trace_id == "trace-abc"
        assert record.duration_ms == 15.0
        assert len(record.rejection_reasons) == 1
        assert "Prerequisite" in record.rejection_reasons[0]
        assert "mastery" in record.voter_breakdown


# =============================================================================
# 5. EventChainTracker
# =============================================================================


class TestEventChainTracker:
    def test_add_and_get_chain(self):
        tracker = EventChainTracker()
        tracker.add_event({"correlation_id": "chain-1", "event_type": "a", "aggregate_id": "agg-1"})
        tracker.add_event({"correlation_id": "chain-1", "event_type": "b", "aggregate_id": "agg-2"})
        chain = tracker.get_chain("chain-1")
        assert len(chain) == 2

    def test_empty_chain(self):
        tracker = EventChainTracker()
        assert tracker.get_chain("nonexistent") == []

    def test_all_chains(self):
        tracker = EventChainTracker()
        tracker.add_event({"correlation_id": "c1", "event_type": "a"})
        tracker.add_event({"correlation_id": "c2", "event_type": "b"})
        chains = tracker.all_chains()
        assert len(chains) == 2
        assert len(chains["c1"]) == 1
        assert len(chains["c2"]) == 1

    def test_reset(self):
        tracker = EventChainTracker()
        tracker.add_event({"correlation_id": "c1", "event_type": "a"})
        tracker.reset()
        assert len(tracker.all_chains()) == 0

    def test_fallback_to_trace_id(self):
        tracker = EventChainTracker()
        tracker.add_event({"trace_id": "t1", "event_type": "a"})
        chain = tracker.get_chain("t1")
        assert len(chain) == 1


# =============================================================================
# 6. SwarmDiagnostics
# =============================================================================


class TestSwarmDiagnostics:
    def make_result(self, decision="approve") -> ConsensusResult:
        votes = [ConsensusVote(voter_name="v1", decision=VoteDecision(decision))]
        return ConsensusResult(
            module_id="mod-1",
            student_id="stu-1",
            decision=VoteDecision(decision),
            confidence=0.9,
            votes=votes,
            trace_id="trace-1",
        )

    def test_record_decision(self):
        sd = SwarmDiagnostics()
        sd.record_decision(self.make_result("approve"), 10.0)
        assert len(sd.timeline.records) == 1

    def test_record_event(self):
        sd = SwarmDiagnostics()
        sd.record_event({"correlation_id": "c1", "event_type": "test"})
        assert len(sd.chain_tracker.get_chain("c1")) == 1

    def test_student_report(self):
        sd = SwarmDiagnostics()
        sd.record_decision(self.make_result("approve"), 10.0)
        report = sd.student_report("stu-1")
        assert report["total_decisions"] == 1

    def test_student_report_no_data(self):
        sd = SwarmDiagnostics()
        report = sd.student_report("stu-none")
        assert report["total_decisions"] == 0

    def test_module_report(self):
        sd = SwarmDiagnostics()
        sd.record_decision(self.make_result("approve"), 10.0)
        report = sd.module_report("mod-1")
        assert report["total_decisions"] == 1
        assert report["last_decision"]["decision"] == "approve"

    def test_summary_empty(self):
        sd = SwarmDiagnostics()
        summary = sd.summary()
        assert summary["total_decisions"] == 0

    def test_summary_with_data(self):
        sd = SwarmDiagnostics()
        sd.record_decision(self.make_result("approve"), 10.0)
        sd.record_decision(self.make_result("reject"), 20.0)
        sd.record_event({"correlation_id": "c1", "event_type": "test"})
        summary = sd.summary()
        assert summary["total_decisions"] == 2
        assert summary["approvals"] == 1
        assert summary["rejections"] == 1
        assert summary["event_chains"] == 1
        assert summary["avg_duration_ms"] == 15.0

    def test_reset(self):
        sd = SwarmDiagnostics()
        sd.record_decision(self.make_result("approve"), 10.0)
        sd.record_event({"correlation_id": "c1"})
        sd.reset()
        assert len(sd.timeline.records) == 0
        assert len(sd.chain_tracker.all_chains()) == 0


# =============================================================================
# 7. Integration: ConsensusEngine with TraceContext
# =============================================================================


class TestConsensusTracingIntegration:
    def _make_path_and_module(self, db, estudiante_user, client, docente_token):
        """Create a course, path and 2 modules for integration testing."""
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "OBS-TRACE", "name": "Obs Trace", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Obs Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Obs Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()
        return path, m1, m2

    def test_engine_run_adds_voter_timings(self, db, estudiante_user, client, docente_token):
        from app.db.uow import UnitOfWork

        uow = UnitOfWork(lambda: db)
        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        ctx = VoteContext(
            uow=uow,
            student_id=estudiante_user.id,
            module_id=module.id,
            path_id=path.id,
            course_id=path.course_id,
            score=0.85,
            module=module,
            path=path,
        )
        trace_ctx = TraceContext.new(emitted_by="test")
        engine = ConsensusEngine()
        result = engine.run(ctx, trace_ctx=trace_ctx)

        assert result.trace_id == trace_ctx.trace_id
        assert len(result.voter_timings) == 4
        for timing in result.voter_timings:
            assert "voter_name" in timing
            assert "decision" in timing
            assert "duration_ms" in timing
            assert timing["duration_ms"] >= 0
            assert "status" in timing

    def test_engine_run_without_trace_ctx(self, db, estudiante_user, client, docente_token):
        from app.db.uow import UnitOfWork

        uow = UnitOfWork(lambda: db)
        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        ctx = VoteContext(
            uow=uow,
            student_id=estudiante_user.id,
            module_id=module.id,
            path_id=path.id,
            course_id=path.course_id,
            score=0.85,
            module=module,
            path=path,
        )
        engine = ConsensusEngine()
        result = engine.run(ctx)
        assert result.trace_id is None
        assert result.voter_timings == []

    def test_voter_timing_on_error(self):
        class BrokenVoter(MasteryVoter):
            @property
            def voter_name(self):
                return "broken"

            def vote(self, ctx):
                raise RuntimeError("Voter exploded")

        engine = ConsensusEngine(voters=[BrokenVoter()])
        from app.db.uow import UnitOfWork

        uow = UnitOfWork(lambda: None)
        ctx = VoteContext(
            uow=uow,
            student_id="stu-1",
            module_id="mod-1",
            path_id="path-1",
            course_id="course-1",
            score=0.5,
            module=None,
            path=None,
        )
        trace_ctx = TraceContext.new()
        result = engine.run(ctx, trace_ctx=trace_ctx)

        assert len(result.voter_timings) == 1
        timing = result.voter_timings[0]
        assert timing["status"] == "error"
        assert "Voter exploded" in timing["error"]

    def test_consensus_to_dict_includes_trace(self, db, estudiante_user, client, docente_token):
        from app.db.uow import UnitOfWork

        uow = UnitOfWork(lambda: db)
        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        ctx = VoteContext(
            uow=uow,
            student_id=estudiante_user.id,
            module_id=module.id,
            path_id=path.id,
            course_id=path.course_id,
            score=0.85,
            module=module,
            path=path,
        )
        trace_ctx = TraceContext.new()
        engine = ConsensusEngine()
        result = engine.run(ctx, trace_ctx=trace_ctx)

        d = result.to_dict()
        assert d["trace_id"] == trace_ctx.trace_id
        assert len(d["voter_timings"]) == 4


# =============================================================================
# 8. Integration: evaluate_module_completion produces trace context
# =============================================================================


class TestEvaluateModuleCompletionTracing:
    def _make_path_and_module(self, db, estudiante_user, client, docente_token):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "OBS-EVAL", "name": "Obs Eval", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Eval Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Eval Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()
        return path, m1, m2

    def test_completion_returns_consensus_with_trace_id(self, test_uow, estudiante_user, db, client, docente_token):
        from app.services.adaptive_service import evaluate_module_completion

        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        result = evaluate_module_completion(
            test_uow, str(estudiante_user.id), module.id, 0.85,
        )
        test_uow.commit()

        assert "consensus" in result
        assert "trace_id" in result["consensus"]
        assert result["consensus"]["trace_id"] is not None
        assert len(result["consensus"]["voter_timings"]) > 0

    def test_completion_metrics_recorded(self, test_uow, estudiante_user, db, client, docente_token):
        from app.observability.consensus_metrics import metrics
        from app.services.adaptive_service import evaluate_module_completion

        before = metrics.total_runs
        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        evaluate_module_completion(
            test_uow, str(estudiante_user.id), module.id, 0.85,
        )
        test_uow.commit()
        assert metrics.total_runs == before + 1

    def test_completion_diagnostics_recorded(self, test_uow, estudiante_user, db, client, docente_token):
        from app.observability.swarm_diagnostics import diagnostics
        from app.services.adaptive_service import evaluate_module_completion

        before = len(diagnostics.timeline.records)
        path, module, _m2 = self._make_path_and_module(db, estudiante_user, client, docente_token)
        evaluate_module_completion(
            test_uow, str(estudiante_user.id), module.id, 0.85,
        )
        test_uow.commit()
        assert len(diagnostics.timeline.records) == before + 1


# =============================================================================
# 9. Metrics snapshot structure
# =============================================================================


class TestMetricsSnapshot:
    def test_snapshot_keys(self):
        m = ConsensusMetrics()
        m.record_run(
            ConsensusResult(
                module_id="m", student_id="s",
                decision=VoteDecision.APPROVE, confidence=0.9,
                votes=[ConsensusVote(voter_name="v", decision=VoteDecision.APPROVE)],
            ),
            10.0,
        )
        snap = m.get_snapshot()
        required_keys = [
            "total_runs", "approvals", "rejections", "abstentions",
            "approval_rate", "rejection_rate", "disagreements",
            "avg_latency_ms", "min_latency_ms", "max_latency_ms",
            "modules_completed", "modules_locked", "rollbacks",
            "voter_stats", "top_rejection_reasons", "top_abstention_reasons",
        ]
        for key in required_keys:
            assert key in snap, f"Missing key: {key}"
