"""
Tests for ConsensusEngine V1 — deterministic module progression decisions.

Covers:
    - Individual voter logic (unit tests)
    - Aggregation rules
    - ConsensusEngine end-to-end
    - Integration with evaluate_module_completion
"""

import pytest
from datetime import datetime, timezone

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
    BaseVoter,
)
from app.models.student_progress import LearningPath, PathModule


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def path_and_module(db, estudiante_user, docente_token, client):
    """Create a learning path with 2 modules (first available, second locked)."""
    from app.models.student_progress import LearningPath, PathModule

    cr = client.post(
        "/api/courses",
        headers={"Authorization": f"Bearer {docente_token}"},
        json={"code": "CNS-TEST", "name": "Consensus Test", "cycle": 1, "year": 2026},
    )
    cid = cr.json()["id"]
    path = LearningPath(
        student_id=estudiante_user.id, course_id=cid,
        total_modules=2, completed_modules=0,
    )
    db.add(path)
    db.flush()
    m1 = PathModule(
        path_id=path.id, title="Module 1", order=1,
        status="available", bloom_level=2,
    )
    db.add(m1)
    m2 = PathModule(
        path_id=path.id, title="Module 2", order=2, status="locked",
    )
    db.add(m2)
    db.commit()
    return path, m1, m2


@pytest.fixture
def vote_ctx(test_uow, path_and_module, estudiante_user):
    """Build a default VoteContext (score=0.85, first module)."""
    path, m1, _m2 = path_and_module
    return VoteContext(
        uow=test_uow,
        student_id=estudiante_user.id,
        module_id=m1.id,
        path_id=path.id,
        course_id=path.course_id,
        score=0.85,
        module=m1,
        path=path,
    )


# ── Data class validation ───────────────────────────────────────────


class TestConsensusVoteValidation:
    def test_valid_confidence(self):
        v = ConsensusVote(voter_name="test", decision=VoteDecision.APPROVE, confidence=0.5)
        assert v.confidence == 0.5

    def test_confidence_too_low(self):
        with pytest.raises(ValueError, match="confidence"):
            ConsensusVote(voter_name="test", decision=VoteDecision.APPROVE, confidence=-0.1)

    def test_confidence_too_high(self):
        with pytest.raises(ValueError, match="confidence"):
            ConsensusVote(voter_name="test", decision=VoteDecision.APPROVE, confidence=1.1)


class TestVoteContextValidation:
    def test_valid_score(self, test_uow, path_and_module, estudiante_user):
        path, m1, _m2 = path_and_module
        ctx = VoteContext(
            uow=test_uow, student_id=estudiante_user.id,
            module_id=m1.id, path_id=path.id,
            course_id=path.course_id, score=0.5,
            module=m1, path=path,
        )
        assert ctx.score == 0.5

    def test_score_too_low(self, test_uow, path_and_module, estudiante_user):
        path, m1, _m2 = path_and_module
        with pytest.raises(ValueError, match="score"):
            VoteContext(
                uow=test_uow, student_id=estudiante_user.id,
                module_id=m1.id, path_id=path.id,
                course_id=path.course_id, score=-0.1,
                module=m1, path=path,
            )

    def test_score_too_high(self, test_uow, path_and_module, estudiante_user):
        path, m1, _m2 = path_and_module
        with pytest.raises(ValueError, match="score"):
            VoteContext(
                uow=test_uow, student_id=estudiante_user.id,
                module_id=m1.id, path_id=path.id,
                course_id=path.course_id, score=1.5,
                module=m1, path=path,
            )


class TestMasteryVoterInitialization:
    def test_invalid_thresholds(self):
        with pytest.raises(ValueError, match="reject_threshold"):
            MasteryVoter(approve_threshold=0.3, reject_threshold=0.5)

    def test_custom_thresholds(self):
        v = MasteryVoter(approve_threshold=0.8, reject_threshold=0.5)
        assert v.voter_name == "mastery"
        assert v._approve_threshold == 0.8
        assert v._reject_threshold == 0.5


# ── Individual Voter Tests ─────────────────────────────────────────


class TestMasteryVoter:
    def test_approve_high_score(self, vote_ctx):
        voter = MasteryVoter()
        result = voter.vote(vote_ctx)
        # score=0.85 >= 0.6
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence == 0.85
        assert "0.85" in result.reason

    def test_abstain_borderline(self, vote_ctx):
        voter = MasteryVoter()
        vote_ctx.score = 0.5
        result = voter.vote(vote_ctx)
        # 0.4 <= 0.5 < 0.6
        assert result.decision == VoteDecision.ABSTAIN
        assert result.confidence == 0.5

    def test_reject_low_score(self, vote_ctx):
        voter = MasteryVoter()
        vote_ctx.score = 0.2
        result = voter.vote(vote_ctx)
        # 0.2 < 0.4
        assert result.decision == VoteDecision.REJECT
        assert result.confidence == 0.8  # 1.0 - 0.2

    def test_approve_at_exact_threshold(self, vote_ctx):
        voter = MasteryVoter(approve_threshold=0.7, reject_threshold=0.5)
        vote_ctx.score = 0.7
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_reject_at_exact_threshold(self, vote_ctx):
        voter = MasteryVoter(approve_threshold=0.6, reject_threshold=0.4)
        vote_ctx.score = 0.39
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.REJECT


class TestPrereqVoter:
    def test_no_prereqs_approve(self, vote_ctx):
        # First module (order=1), no lower modules
        voter = PrereqVoter()
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_prereqs_completed_approve(self, test_uow, db, estudiante_user,
                                       docente_token, client):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-PREREQ", "name": "Prereq Test", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=1,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod A", order=1,
            status="completed", completed_at=datetime.now(timezone.utc),
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod B", order=2, status="available",
        )
        db.add(m2)
        db.commit()

        ctx = VoteContext(
            uow=test_uow, student_id=estudiante_user.id,
            module_id=m2.id, path_id=path.id,
            course_id=cid, score=0.8, module=m2, path=path,
        )
        voter = PrereqVoter()
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_prereqs_incomplete_reject(self, test_uow, db, estudiante_user,
                                        docente_token, client):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-PRERQ2", "name": "Prereq Reject", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod A", order=1, status="available",
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod B", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        ctx = VoteContext(
            uow=test_uow, student_id=estudiante_user.id,
            module_id=m2.id, path_id=path.id,
            course_id=cid, score=0.8, module=m2, path=path,
        )
        voter = PrereqVoter()
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.REJECT
        assert "prerequisite" in result.reason.lower()
        assert result.evidence["incomplete_prereqs"] == 1
        assert "Mod A" in result.evidence["prerequisite_titles"]


class TestSequenceVoter:
    def test_first_module_approve(self, vote_ctx):
        # order=1, no previous module
        voter = SequenceVoter()
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_previous_completed_approve(self, test_uow, db, estudiante_user,
                                         docente_token, client):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-SEQ", "name": "Sequence Test", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=1,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod A", order=1,
            status="completed", completed_at=datetime.now(timezone.utc),
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod B", order=2, status="available",
        )
        db.add(m2)
        db.commit()

        ctx = VoteContext(
            uow=test_uow, student_id=estudiante_user.id,
            module_id=m2.id, path_id=path.id,
            course_id=cid, score=0.8, module=m2, path=path,
        )
        voter = SequenceVoter()
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_previous_not_completed_reject(self, test_uow, db, estudiante_user,
                                            docente_token, client):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-SEQ2", "name": "Seq Reject", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod A", order=1, status="available",
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod B", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        ctx = VoteContext(
            uow=test_uow, student_id=estudiante_user.id,
            module_id=m2.id, path_id=path.id,
            course_id=cid, score=0.8, module=m2, path=path,
        )
        voter = SequenceVoter()
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.REJECT
        assert "not completed" in result.reason

    def test_already_completed_abstain(self, vote_ctx):
        vote_ctx.module.status = "completed"
        voter = SequenceVoter()
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.ABSTAIN


class TestTimeVoter:
    def test_always_approve_v1(self, vote_ctx):
        voter = TimeVoter()
        result = voter.vote(vote_ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence == 0.6
        assert "v1_heuristic" in result.evidence.get("voter_version", "")


# ── Aggregation Rules ──────────────────────────────────────────────


class TestConsensusEngineAggregation:
    """Unit tests for _aggregate logic with synthetic votes."""

    def make_engine(self):
        return ConsensusEngine(voters=[])

    def test_empty_votes_abstain(self):
        e = self.make_engine()
        decision, confidence = e._aggregate([])
        assert decision == VoteDecision.ABSTAIN
        assert confidence == 0.0

    def test_all_approve_unanimous(self):
        e = self.make_engine()
        votes = [
            ConsensusVote("v1", VoteDecision.APPROVE, 0.9),
            ConsensusVote("v2", VoteDecision.APPROVE, 0.8),
        ]
        decision, confidence = e._aggregate(votes)
        assert decision == VoteDecision.APPROVE
        assert confidence == pytest.approx(0.85)

    def test_all_abstain(self):
        e = self.make_engine()
        votes = [
            ConsensusVote("v1", VoteDecision.ABSTAIN),
            ConsensusVote("v2", VoteDecision.ABSTAIN),
        ]
        decision, confidence = e._aggregate(votes)
        assert decision == VoteDecision.ABSTAIN

    def test_any_reject_overall_reject(self):
        e = self.make_engine()
        votes = [
            ConsensusVote("v1", VoteDecision.APPROVE, 0.9),
            ConsensusVote("v2", VoteDecision.REJECT, 0.95),
            ConsensusVote("v3", VoteDecision.APPROVE, 0.8),
        ]
        decision, confidence = e._aggregate(votes)
        assert decision == VoteDecision.REJECT
        assert confidence == 0.95  # weighted confidence of reject votes

    def test_mixed_approve_abstain(self):
        e = self.make_engine()
        votes = [
            ConsensusVote("v1", VoteDecision.APPROVE, 1.0),
            ConsensusVote("v2", VoteDecision.ABSTAIN, 0.5),
            ConsensusVote("v3", VoteDecision.APPROVE, 1.0),
        ]
        decision, confidence = e._aggregate(votes)
        assert decision == VoteDecision.APPROVE
        # ratio = 2/2 = 1.0, avg_confidence = 1.0, confidence = 1.0 * 1.0 = 1.0
        assert confidence == 1.0

    def test_approve_with_abstain_and_reject(self):
        e = self.make_engine()
        votes = [
            ConsensusVote("v1", VoteDecision.APPROVE, 1.0),
            ConsensusVote("v2", VoteDecision.ABSTAIN),
            ConsensusVote("v3", VoteDecision.REJECT, 1.0),
        ]
        decision, confidence = e._aggregate(votes)
        # Any reject → overall reject
        assert decision == VoteDecision.REJECT

    def test_single_approve(self):
        e = self.make_engine()
        votes = [ConsensusVote("v1", VoteDecision.APPROVE, 0.75)]
        decision, confidence = e._aggregate(votes)
        assert decision == VoteDecision.APPROVE
        assert confidence == 0.75


# ── ConsensusEngine End-to-End ────────────────────────────────────


class TestConsensusEngineRun:
    def test_default_voters_all_approve(self, vote_ctx):
        # score=0.85, first module, no prereqs
        engine = ConsensusEngine()
        result = engine.run(vote_ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence > 0.5
        assert len(result.votes) == 4
        assert result.unanimous is True

    def test_low_score_rejects(self, vote_ctx):
        vote_ctx.score = 0.2
        engine = ConsensusEngine()
        result = engine.run(vote_ctx)
        assert result.decision == VoteDecision.REJECT

    def test_borderline_score_abstain_or_approve(self, vote_ctx):
        # score=0.5: Mastery ABSTAIN, others APPROVE
        vote_ctx.score = 0.5
        engine = ConsensusEngine()
        result = engine.run(vote_ctx)
        # 3 approve (Prereq, Sequence, Time) + 1 abstain (Mastery)
        # Non-abstain = 3, all approve → ratio=1.0 → APPROVE
        assert result.decision == VoteDecision.APPROVE

    def test_voter_error_does_not_crash(self, vote_ctx):
        class BrokenVoter(BaseVoter):
            @property
            def voter_name(self):
                return "broken"

            def vote(self, ctx):
                raise RuntimeError("Something went wrong")

        engine = ConsensusEngine(voters=[BrokenVoter()])
        result = engine.run(vote_ctx)
        assert len(result.votes) == 1
        assert result.votes[0].decision == VoteDecision.ABSTAIN
        assert "Something went wrong" in result.votes[0].reason

    def test_custom_voter_registration(self, vote_ctx):
        class AlwaysReject(BaseVoter):
            @property
            def voter_name(self):
                return "always_reject"

            def vote(self, ctx):
                return ConsensusVote(
                    voter_name=self.voter_name,
                    decision=VoteDecision.REJECT,
                    confidence=1.0,
                    reason="Reject always",
                )

        engine = ConsensusEngine(voters=[])
        engine.register_voter(AlwaysReject())
        result = engine.run(vote_ctx)
        assert result.decision == VoteDecision.REJECT


# ── ConsensusResult Properties ────────────────────────────────────


class TestConsensusResult:
    def test_unanimous_true(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.APPROVE, confidence=1.0,
            votes=[
                ConsensusVote("v1", VoteDecision.APPROVE),
                ConsensusVote("v2", VoteDecision.APPROVE),
            ],
        )
        assert result.unanimous is True

    def test_unanimous_false(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.APPROVE, confidence=0.5,
            votes=[
                ConsensusVote("v1", VoteDecision.APPROVE),
                ConsensusVote("v2", VoteDecision.ABSTAIN),
            ],
        )
        assert result.unanimous is False

    def test_approve_ratio(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.APPROVE, confidence=0.5,
            votes=[
                ConsensusVote("v1", VoteDecision.APPROVE),
                ConsensusVote("v2", VoteDecision.REJECT),
                ConsensusVote("v3", VoteDecision.ABSTAIN),
            ],
        )
        assert result.approve_ratio == 0.5  # 1/2 non-abstain

    def test_approve_ratio_no_votes(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.ABSTAIN, confidence=0.0,
        )
        assert result.approve_ratio == 0.0

    def test_reject_ratio(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.REJECT, confidence=1.0,
            votes=[
                ConsensusVote("v1", VoteDecision.REJECT),
                ConsensusVote("v2", VoteDecision.APPROVE),
                ConsensusVote("v3", VoteDecision.ABSTAIN),
            ],
        )
        assert result.reject_ratio == 0.5  # 1/2 non-abstain

    def test_to_dict_structure(self):
        result = ConsensusResult(
            module_id="m1", student_id="s1",
            decision=VoteDecision.APPROVE, confidence=0.95,
            votes=[
                ConsensusVote("v1", VoteDecision.APPROVE, 0.95,
                              reason="Good", evidence={"k": "v"}),
            ],
        )
        d = result.to_dict()
        assert d["module_id"] == "m1"
        assert d["decision"] == "approve"
        assert d["confidence"] == 0.95
        assert d["unanimous"] is True
        assert d["num_votes"] == 1
        assert d["votes"][0]["voter_name"] == "v1"
        assert d["votes"][0]["evidence"]["k"] == "v"


# ── Integration with evaluate_module_completion ──────────────────


class TestEvaluateModuleCompletionConsensus:
    """Verify consensus integration in evaluate_module_completion.
    Tests mirror existing test_adaptive.py pattern for backward compat."""

    def test_high_score_unlocks_next(self, test_uow, estudiante_user,
                                      docente_token, client, db):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-HI", "name": "Consensus High", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, m1.id, 0.85)
        test_uow.commit()

        assert "unlocked" in result
        assert result["unlocked"] == "Mod 2"
        assert "consensus" in result
        assert result["consensus"]["decision"] == "approve"

    def test_medium_score_does_not_block(self, test_uow, estudiante_user,
                                          docente_token, client, db):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-MED", "name": "Consensus Med", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, m1.id, 0.5)
        test_uow.commit()

        assert result.get("unlocked") == "Mod 2"
        assert "consensus" in result

    def test_low_score_locks_next(self, test_uow, estudiante_user,
                                   docente_token, client, db):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-LOW", "name": "Consensus Low", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, m1.id, 0.2)
        test_uow.commit()

        assert result.get("locked") is True
        assert "reject threshold" in result.get("reason", "")
        assert "consensus" in result

    def test_module_not_found(self, test_uow, estudiante_user):
        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, "non-existent", 0.8)
        assert "error" in result

    def test_last_module_completes_path(self, test_uow, estudiante_user,
                                         docente_token, client, db):
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-LAST", "name": "Consensus Last", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=1, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        db.commit()

        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, m1.id, 0.9)
        test_uow.commit()

        assert result.get("completed") is True
        assert "consensus" in result

    def test_custom_engine_injected(self, test_uow, estudiante_user,
                                     docente_token, client, db):
        """Verify we can inject a custom ConsensusEngine."""
        from app.models.student_progress import LearningPath, PathModule

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-CUST", "name": "Cust Engine", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        class StrictMasteryOnly(BaseVoter):
            @property
            def voter_name(self):
                return "strict_mastery"

            def vote(self, ctx):
                if ctx.score >= 0.9:
                    return ConsensusVote(
                        self.voter_name, VoteDecision.APPROVE, 1.0,
                    )
                return ConsensusVote(
                    self.voter_name, VoteDecision.REJECT, 1.0,
                    reason="Score below 0.9",
                )

        engine = ConsensusEngine(voters=[StrictMasteryOnly()])

        from app.services.adaptive_service import evaluate_module_completion

        # With score=0.85, StrictMasteryOnly rejects
        result = evaluate_module_completion(
            test_uow, estudiante_user.id, m1.id, 0.85, engine=engine,
        )
        test_uow.commit()
        assert result.get("locked") is True
        assert result["consensus"]["decision"] == "reject"

    def test_consensus_emits_event(self, test_uow, estudiante_user,
                                    docente_token, client, db):
        """Verify an outbox event is created on consensus run."""
        from app.models.student_progress import LearningPath, PathModule
        from app.models.event_outbox import EventOutbox

        cr = client.post(
            "/api/courses",
            headers={"Authorization": f"Bearer {docente_token}"},
            json={"code": "CNS-EVT", "name": "Consensus Event", "cycle": 1, "year": 2026},
        )
        cid = cr.json()["id"]
        path = LearningPath(
            student_id=estudiante_user.id, course_id=cid,
            total_modules=2, completed_modules=0,
        )
        db.add(path)
        db.flush()
        m1 = PathModule(
            path_id=path.id, title="Mod 1", order=1,
            status="available", bloom_level=2,
        )
        db.add(m1)
        m2 = PathModule(
            path_id=path.id, title="Mod 2", order=2, status="locked",
        )
        db.add(m2)
        db.commit()

        from app.services.adaptive_service import evaluate_module_completion
        result = evaluate_module_completion(test_uow, estudiante_user.id, m1.id, 0.85)

        # Event should be registered (not committed yet)
        assert len(test_uow.pending_events) >= 1
        event_types = [e.event_type for e in test_uow.pending_events]
        assert "module.progression.consensus" in event_types

        test_uow.commit()

        # After commit, verify event is persisted
        db_events = (
            db.query(EventOutbox)
            .filter(EventOutbox.event_type == "module.progression.consensus")
            .all()
        )
        assert len(db_events) >= 1
        assert db_events[0].aggregate_id == m1.id
        assert "decision" in db_events[0].payload
