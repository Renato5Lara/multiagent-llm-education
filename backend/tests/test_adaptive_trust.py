"""Tests for adaptive trust scoring, specialization, and dynamic weighting."""

import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
)
from app.core.trust import TrustSystem, VoterTrustRecord, get_trust_system, reset_trust_system
from app.core.specialization import (
    SpecializationTracker,
    SpecializationProfile,
    context_key,
    get_specialization_tracker,
    reset_specialization_tracker,
)
from app.core.weighting import compute_weights, compute_weights_detailed


# =============================================================================
# 1. VoterTrustRecord
# =============================================================================


class TestVoterTrustRecord:
    def test_accuracy_no_votes(self):
        r = VoterTrustRecord(voter_name="test")
        assert r.accuracy == 0.0

    def test_accuracy_correct(self):
        r = VoterTrustRecord(voter_name="test", total_votes=10, correct_votes=8, abstentions=1)
        # non-abstain = 9, correct = 8
        assert r.accuracy == pytest.approx(8 / 9)

    def test_disagreement_rate(self):
        r = VoterTrustRecord(voter_name="test", total_votes=10, incorrect_votes=3, abstentions=2)
        # non-abstain = 8, incorrect = 3
        assert r.disagreement_rate == pytest.approx(3 / 8)

    def test_confidence_calibration_perfect(self):
        r = VoterTrustRecord(voter_name="test", total_votes=10, correct_votes=8, total_confidence=8.0, abstentions=1)
        # avg_confidence = 0.8, accuracy = 8/9 ≈ 0.889
        expected = 0.8 - 8/9
        assert r.confidence_calibration == pytest.approx(expected)

    def test_confidence_calibration_overconfident(self):
        r = VoterTrustRecord(voter_name="test", total_votes=10, correct_votes=5, total_confidence=9.0, abstentions=0)
        # avg_confidence = 0.9, accuracy = 0.5
        assert r.confidence_calibration == pytest.approx(0.4)
        assert r.confidence_calibration > 0  # overconfident

    def test_avg_latency(self):
        r = VoterTrustRecord(voter_name="test", total_votes=4, total_latency_ms=100.0)
        assert r.avg_latency_ms == 25.0

    def test_to_dict_keys(self):
        r = VoterTrustRecord(voter_name="mastery", total_votes=5, correct_votes=4)
        d = r.to_dict()
        assert d["voter_name"] == "mastery"
        assert "accuracy" in d
        assert "trust_score" in d
        assert "confidence_calibration" in d


# =============================================================================
# 2. TrustSystem
# =============================================================================


class TestTrustSystem:
    def test_initial_trust_is_1(self):
        ts = TrustSystem()
        assert ts.get_trust("mastery") == 1.0

    def test_trust_decreases_on_incorrect(self):
        ts = TrustSystem()
        ts.record_vote_outcome("mastery", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.REJECT)
        assert ts.get_trust("mastery") < 1.0

    def test_trust_increases_on_correct(self):
        ts = TrustSystem()
        # First vote: incorrect → trust drops
        ts.record_vote_outcome("mastery", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.REJECT)
        before = ts.get_trust("mastery")
        # Second vote: correct → trust increases
        ts.record_vote_outcome("mastery", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.APPROVE)
        after = ts.get_trust("mastery")
        assert after > before

    def test_error_records(self):
        ts = TrustSystem()
        ts.record_error("broken_voter")
        record = ts.get_record("broken_voter")
        assert record.errors == 1
        # record_error does not increment total_votes — the synthetic ABSTAIN
        # vote via record_vote_outcome is what counts the round participation
        assert record.total_votes == 0

    def test_min_trust_floor(self):
        ts = TrustSystem(min_trust=0.1)
        # Many wrong votes
        for _ in range(100):
            ts.record_vote_outcome("bad", VoteDecision.APPROVE, 1.0, 5.0, VoteDecision.REJECT)
        assert ts.get_trust("bad") >= 0.1

    def test_snapshot_includes_voters(self):
        ts = TrustSystem()
        ts.record_vote_outcome("mastery", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.APPROVE)
        snap = ts.get_snapshot()
        assert "mastery" in snap

    def test_reset_clears(self):
        ts = TrustSystem()
        ts.record_vote_outcome("mastery", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.APPROVE)
        ts.reset()
        assert len(ts.get_snapshot()) == 0

    def test_get_trust_scores(self):
        ts = TrustSystem()
        ts.record_vote_outcome("v1", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.APPROVE)
        ts.record_vote_outcome("v2", VoteDecision.REJECT, 1.0, 5.0, VoteDecision.APPROVE)
        scores = ts.get_trust_scores(["v1", "v2"])
        assert "v1" in scores
        assert "v2" in scores
        assert scores["v1"] > scores["v2"]  # v1 was correct, v2 was wrong

    def test_recompute_after_error(self):
        ts = TrustSystem()
        ts.record_vote_outcome("v1", VoteDecision.APPROVE, 0.9, 5.0, VoteDecision.APPROVE)
        good_trust = ts.get_trust("v1")
        ts.record_error("v1")
        assert ts.get_trust("v1") < good_trust  # error reduces trust

    def test_decay_rate_effect(self):
        fast = TrustSystem(decay_rate=0.1)
        slow = TrustSystem(decay_rate=0.001)
        fast.record_vote_outcome("f", VoteDecision.APPROVE, 1.0, 1.0, VoteDecision.APPROVE)
        slow.record_vote_outcome("s", VoteDecision.APPROVE, 1.0, 1.0, VoteDecision.APPROVE)
        # Both should have trust ≈ 1.0 (no decay yet since just voted)
        assert fast.get_trust("f") == pytest.approx(1.0, abs=0.01)
        assert slow.get_trust("s") == pytest.approx(1.0, abs=0.01)

    def test_thread_safety(self):
        ts = TrustSystem()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    ts.record_vote_outcome("v1", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.APPROVE)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        record = ts.get_record("v1")
        assert record.total_votes == 400

    def test_abstention_not_penalized(self):
        ts = TrustSystem()
        # Abstain when final was REJECT — abstention should not be penalized
        ts.record_vote_outcome("v1", VoteDecision.ABSTAIN, 0.5, 1.0, VoteDecision.REJECT)
        record = ts.get_record("v1")
        assert record.abstentions == 1
        assert record.correct_votes == 0
        assert record.incorrect_votes == 0
        # Accuracy should not be affected by abstentions (0/0 = 0.0 but trust stable)
        assert record.accuracy == 0.0

    def test_singleton(self):
        reset_trust_system()
        ts1 = get_trust_system()
        ts2 = get_trust_system()
        assert ts1 is ts2


# =============================================================================
# 3. SpecializationTracker
# =============================================================================


class TestSpecializationTracker:
    def test_initial_affinity_is_neutral(self):
        st = SpecializationTracker()
        assert st.get_affinity("mastery", "bloom:3") == 0.5

    def test_affinity_improves_with_correct_votes(self):
        st = SpecializationTracker()
        for _ in range(10):
            st.record_vote("mastery", "bloom:3", agreed_with_consensus=True)
        assert st.get_affinity("mastery", "bloom:3") > 0.5

    def test_affinity_decreases_with_incorrect_votes(self):
        st = SpecializationTracker()
        for _ in range(10):
            st.record_vote("mastery", "bloom:3", agreed_with_consensus=False)
        assert st.get_affinity("mastery", "bloom:3") < 0.5

    def test_domain_separation(self):
        st = SpecializationTracker()
        # Good in bloom:3, bad in bloom:5
        for _ in range(10):
            st.record_vote("mastery", "bloom:3", agreed_with_consensus=True)
            st.record_vote("mastery", "bloom:5", agreed_with_consensus=False)
        assert st.get_affinity("mastery", "bloom:3") > 0.5
        assert st.get_affinity("mastery", "bloom:5") < 0.5

    def test_profile_creation(self):
        st = SpecializationTracker()
        st.record_vote("mastery", "bloom:2", agreed_with_consensus=True)
        profile = st.get_profile("mastery")
        assert profile is not None
        assert profile.total_votes == 1

    def test_get_all_profiles(self):
        st = SpecializationTracker()
        st.record_vote("v1", "bloom:3", True)
        st.record_vote("v2", "bloom:5", False)
        assert len(st.get_all_profiles()) == 2

    def test_snapshot(self):
        st = SpecializationTracker()
        st.record_vote("mastery", "bloom:3", True)
        snap = st.get_snapshot()
        assert "mastery" in snap
        assert "domains" in snap["mastery"]

    def test_reset(self):
        st = SpecializationTracker()
        st.record_vote("mastery", "bloom:3", True)
        st.reset()
        assert len(st.get_all_profiles()) == 0

    def test_thread_safety(self):
        st = SpecializationTracker()
        errors = []

        def worker():
            try:
                for _ in range(100):
                    st.record_vote("v1", "bloom:3", True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        profile = st.get_profile("v1")
        assert profile.total_votes == 400

    def test_singleton(self):
        reset_specialization_tracker()
        st1 = get_specialization_tracker()
        st2 = get_specialization_tracker()
        assert st1 is st2


# =============================================================================
# 4. Weighting
# =============================================================================


class TestWeighting:
    def test_all_equal_weights_without_trust(self):
        weights = compute_weights(["v1", "v2", "v3"])
        assert all(w == 1.0 for w in weights.values())

    def test_weights_reflect_trust(self):
        ts = TrustSystem()
        ts.record_vote_outcome("good", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.APPROVE)
        ts.record_vote_outcome("bad", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.REJECT)
        weights = compute_weights(["good", "bad"], trust_system=ts)
        assert weights["good"] > weights["bad"]

    def test_weights_with_specialization(self):
        ts = TrustSystem()
        st = SpecializationTracker()
        st.record_vote("expert", "bloom:3", True)
        st.record_vote("novice", "bloom:3", False)
        weights = compute_weights(
            ["expert", "novice"],
            trust_system=ts,
            specialization_tracker=st,
            context_key="bloom:3",
        )
        assert weights["expert"] > weights["novice"]

    def test_weights_sum_to_voter_count(self):
        ts = TrustSystem()
        ts.record_vote_outcome("v1", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.APPROVE)
        ts.record_vote_outcome("v2", VoteDecision.REJECT, 0.9, 1.0, VoteDecision.APPROVE)
        weights = compute_weights(["v1", "v2"], trust_system=ts)
        total = sum(weights.values())
        assert total == pytest.approx(2.0, rel=0.01)

    def test_detailed_weights(self):
        ts = TrustSystem()
        details = compute_weights_detailed(["v1", "v2"], trust_system=ts)
        for name in ["v1", "v2"]:
            assert "trust" in details[name]
            assert "affinity" in details[name]
            assert "raw_weight" in details[name]
            assert "final_weight" in details[name]

    def test_empty_voters(self):
        assert compute_weights([]) == {}
        assert compute_weights_detailed([]) == {}


# =============================================================================
# 5. Integration: ConsensusEngine with adaptive weighting
# =============================================================================


class TestAdaptiveWeightingIntegration:
    def _make_vote_ctx(self, uow, module=None, path=None, score=0.85):
        return VoteContext(
            uow=uow,
            student_id="stu-1",
            module_id="mod-1",
            path_id="path-1",
            course_id="course-1",
            score=score,
            module=module,
            path=path,
        )

    def test_engine_weights_in_result(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem
        from app.core.specialization import SpecializationTracker

        uow = UnitOfWork(lambda: db)
        ctx = self._make_vote_ctx(uow)
        trust = TrustSystem()
        spec = SpecializationTracker()
        engine = ConsensusEngine()
        result = engine.run(ctx, trust_system=trust, specialization_tracker=spec)

        assert len(result.weights_used) == 4  # 4 voters
        assert len(result.trust_scores) == 4
        assert len(result.specialization_affinities) == 4
        for name in ["mastery", "prerequisite", "sequence", "time"]:
            assert name in result.weights_used
            assert name in result.trust_scores
            assert name in result.specialization_affinities

    def test_trust_updated_after_run(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem

        uow = UnitOfWork(lambda: db)
        ctx = self._make_vote_ctx(uow)
        trust = TrustSystem()
        engine = ConsensusEngine()
        result = engine.run(ctx, trust_system=trust)

        # All voters should have trust records now
        for name in ["mastery", "prerequisite", "sequence", "time"]:
            record = trust.get_record(name)
            assert record is not None
            assert record.total_votes == 1

    def test_trust_differs_by_accuracy(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem

        uow = UnitOfWork(lambda: db)
        trust = TrustSystem()

        # Two voters: one APPROVEs, one REJECTs
        # Rule: any REJECT → overall REJECT, so rejecter agrees, approver disagrees
        class ApproveVoter:
            voter_name = "approver"
            def vote(self, ctx):
                return ConsensusVote(voter_name="approver", decision=VoteDecision.APPROVE, confidence=0.9, reason="yes")

        class RejectVoter:
            voter_name = "rejecter"
            def vote(self, ctx):
                return ConsensusVote(voter_name="rejecter", decision=VoteDecision.REJECT, confidence=1.0, reason="no")

        engine = ConsensusEngine(voters=[ApproveVoter(), RejectVoter()])
        ctx = self._make_vote_ctx(uow)
        engine.run(ctx, trust_system=trust)

        # approver voted APPROVE but consensus was REJECT (any REJECT → REJECT)
        record = trust.get_record("approver")
        assert record is not None
        assert record.incorrect_votes == 1
        assert record.trust_score < 1.0

        # rejecter agreed with consensus
        record2 = trust.get_record("rejecter")
        assert record2 is not None
        assert record2.correct_votes == 1

    def test_specialization_updates(self, db):
        from app.db.uow import UnitOfWork
        from app.core.specialization import SpecializationTracker

        uow = UnitOfWork(lambda: db)
        spec = SpecializationTracker()
        engine = ConsensusEngine()
        ctx = self._make_vote_ctx(uow)
        engine.run(ctx, specialization_tracker=spec)

        # Mastery and time voters work without a real module and should have profiles
        for name in ["mastery", "time"]:
            profile = spec.get_profile(name)
            assert profile is not None
            assert profile.total_votes > 0
            assert len(profile.domain_total) > 0
        # Prerequisite and sequence need ctx.module and will ABSTAIN (no profile)
        for name in ["prerequisite", "sequence"]:
            profile = spec.get_profile(name)
            assert profile is None

    def test_weights_normalized(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem

        uow = UnitOfWork(lambda: db)
        ctx = self._make_vote_ctx(uow)
        trust = TrustSystem()
        engine = ConsensusEngine()
        result = engine.run(ctx, trust_system=trust)

        total = sum(result.weights_used.values())
        assert total == pytest.approx(4.0, rel=0.01)  # 4 voters

    def test_result_to_dict_includes_adaptives(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem

        uow = UnitOfWork(lambda: db)
        ctx = self._make_vote_ctx(uow)
        trust = TrustSystem()
        engine = ConsensusEngine()
        result = engine.run(ctx, trust_system=trust)
        d = result.to_dict()
        assert "weights_used" in d
        assert "trust_scores" in d
        assert "specialization_affinities" in d

    def test_run_without_trust_is_backward_compatible(self, db):
        from app.db.uow import UnitOfWork

        uow = UnitOfWork(lambda: db)
        ctx = self._make_vote_ctx(uow)
        engine = ConsensusEngine()
        result = engine.run(ctx)  # no trust, no specialization
        assert result.weights_used == {}
        assert result.trust_scores == {}
        assert result.specialization_affinities == {}
        assert result.decision is not None  # still works


# =============================================================================
# 6. Reproducibility
# =============================================================================


class TestReproducibility:
    def test_same_inputs_same_trust(self, db):
        from app.db.uow import UnitOfWork
        from app.core.trust import TrustSystem

        uow = UnitOfWork(lambda: db)
        ctx = VoteContext(
            uow=uow,
            student_id="stu-1",
            module_id="mod-1",
            path_id="path-1",
            course_id="course-1",
            score=0.85,
            module=None,
            path=None,
        )

        trust1 = TrustSystem()
        trust2 = TrustSystem()
        engine = ConsensusEngine()

        result1 = engine.run(ctx, trust_system=trust1)
        result2 = engine.run(ctx, trust_system=trust2)

        assert result1.decision == result2.decision
        assert result1.confidence == result2.confidence
        assert result1.weights_used.keys() == result2.weights_used.keys()

    def test_deterministic_weight_order(self):
        """Weights should be deterministic: same voters, same order → same weights."""
        ts = TrustSystem()
        ts.record_vote_outcome("a", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.APPROVE)
        ts.record_vote_outcome("b", VoteDecision.REJECT, 0.9, 1.0, VoteDecision.APPROVE)

        w1 = compute_weights(["a", "b"], trust_system=ts)
        w2 = compute_weights(["a", "b"], trust_system=ts)
        assert w1 == w2


# =============================================================================
# 7. Context key generation
# =============================================================================


class TestContextKey:
    def test_context_key_with_module(self):
        """Need a real module to test, but we can create a mock-like object."""
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.module = MagicMock()
        ctx.module.bloom_level = 3
        key = context_key(ctx)
        assert key == "bloom:3"

    def test_context_key_no_module(self):
        from unittest.mock import MagicMock
        ctx = MagicMock()
        ctx.module = None
        key = context_key(ctx)
        assert key == "bloom:unknown"


# =============================================================================
# 8. Calibration tests
# =============================================================================


class TestCalibration:
    def test_confidence_calibration_error(self):
        """Overconfident voters should have larger calibration error."""
        ts = TrustSystem()

        # Overconfident: high confidence but often wrong
        for _ in range(10):
            ts.record_vote_outcome("over", VoteDecision.APPROVE, 0.95, 1.0, VoteDecision.REJECT)

        # Well-calibrated: moderate confidence, often right
        for _ in range(10):
            ts.record_vote_outcome("good", VoteDecision.APPROVE, 0.75, 1.0, VoteDecision.APPROVE)

        over_record = ts.get_record("over")
        good_record = ts.get_record("good")

        # Overconfident has large positive calibration error
        assert over_record.confidence_calibration > 0.3
        # Good voter has small calibration error
        assert abs(good_record.confidence_calibration) < 0.3

    def test_trust_drift_detected(self):
        """Trust should drift downward for a voter that degrades."""
        ts = TrustSystem()

        # Start good
        for _ in range(5):
            ts.record_vote_outcome("degrader", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.APPROVE)
        good_trust = ts.get_trust("degrader")

        # Then degrade
        for _ in range(10):
            ts.record_vote_outcome("degrader", VoteDecision.APPROVE, 0.9, 1.0, VoteDecision.REJECT)
        bad_trust = ts.get_trust("degrader")

        assert bad_trust < good_trust


# =============================================================================
# 9. SpecializationProfile properties
# =============================================================================


class TestSpecializationProfile:
    def test_no_data_neutral(self):
        sp = SpecializationProfile(voter_name="test")
        assert sp.specialization_affinity("bloom:3") == 0.5

    def test_perfect_accuracy_high_affinity(self):
        sp = SpecializationProfile(voter_name="test")
        for _ in range(10):
            sp.record("bloom:3", correct=True)
        assert sp.specialization_affinity("bloom:3") > 0.9

    def test_zero_accuracy_low_affinity(self):
        sp = SpecializationProfile(voter_name="test")
        for _ in range(10):
            sp.record("bloom:3", correct=False)
        assert sp.specialization_affinity("bloom:3") < 0.3

    def test_domain_accuracy(self):
        sp = SpecializationProfile(voter_name="test")
        sp.record("bloom:3", correct=True)
        sp.record("bloom:3", correct=True)
        sp.record("bloom:3", correct=False)
        assert sp.domain_accuracy("bloom:3") == pytest.approx(2 / 3)

    def test_to_dict(self):
        sp = SpecializationProfile(voter_name="test")
        sp.record("bloom:3", correct=True)
        d = sp.to_dict()
        assert d["voter_name"] == "test"
        assert "domains" in d


# =============================================================================
# 10. Stress and concurrency
# =============================================================================


class TestTrustConcurrency:
    def test_concurrent_trust_scores(self):
        """Multiple threads accessing trust concurrently should not race."""
        ts = TrustSystem()
        errors = []

        def read_trust():
            try:
                for _ in range(500):
                    ts.get_trust("mastery")
                    ts.get_trust("sequence")
            except Exception as e:
                errors.append(e)

        def write_trust():
            try:
                for _ in range(500):
                    ts.record_vote_outcome(
                        "mastery", VoteDecision.APPROVE, 0.9, 1.0,
                        VoteDecision.APPROVE,
                    )
            except Exception as e:
                errors.append(e)

        readers = [threading.Thread(target=read_trust) for _ in range(4)]
        writers = [threading.Thread(target=write_trust) for _ in range(2)]
        all_threads = readers + writers
        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()

        assert len(errors) == 0
