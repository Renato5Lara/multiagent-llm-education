"""Tests for LLM-powered voters (Phase 1: HybridVoter + concrete voters)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.consensus import ConsensusEngine, ConsensusVote, VoteContext, VoteDecision
from app.llm import (
    LLMConfig,
    LLMResponse,
    LLMService,
    TokenBudgetTracker,
    ConfidenceCalibrator,
    HallucinationGuard,
    LLMResponseParser,
)
from app.llm.voters import (
    AdaptiveVoter,
    EvaluationVoter,
    HybridVoter,
    PedagogicalVoter,
)


# ── Fixtures ───────────────────────────────────────────────

@pytest.fixture
def mock_llm_service():
    service = MagicMock(spec=LLMService)
    service.generate = AsyncMock()
    service._estimate_tokens = MagicMock(return_value=100)
    return service


@pytest.fixture
def budget_tracker():
    return TokenBudgetTracker()


@pytest.fixture
def calibrator():
    return ConfidenceCalibrator(min_samples=10)


@pytest.fixture
def guard():
    return HallucinationGuard()


@pytest.fixture
def parser():
    return LLMResponseParser()


@pytest.fixture
def make_ctx():
    """Factory for VoteContext."""

    class FakeModule:
        def __init__(self):
            self.id = "mod-001"
            self.title = "Test Module"
            self.module_type = "exercise"
            self.bloom_level = "3"
            self.difficulty = 0.5
            self.status = "pending"

    class FakePath:
        def __init__(self):
            self.id = "path-001"
            self.title = "Test Path"

    def _make(
        score: float = 0.75,
        module_id: str = "mod-001",
        student_id: str = "stu-001",
        course_id: str = "course-001",
        evidence: dict | None = None,
    ):
        return VoteContext(
            uow=MagicMock(),
            module_id=module_id,
            student_id=student_id,
            course_id=course_id,
            path_id=f"path-{module_id}",
            score=score,
            module=FakeModule(),
            path=FakePath(),
            evidence=evidence or {},
        )

    return _make


# ── HybridVoter Base Tests ─────────────────────────────────

class TestHybridVoterBase:
    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            HybridVoter(
                llm_service=MagicMock(),
                budget_tracker=MagicMock(),
                calibrator=MagicMock(),
                guard=MagicMock(),
            )


# ── PedagogicalVoter Tests ─────────────────────────────────

class TestPedagogicalVoter:
    def test_voter_name(self):
        assert PedagogicalVoter.voter_name == "pedagogical"

    def test_heuristic_high_score_approves(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.85)
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence >= 0.8
        assert result.evidence.get("heuristic")

    def test_heuristic_low_score_rejects(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.25)
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.REJECT

    def test_heuristic_borderline_abstains(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.5)
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.ABSTAIN

    def test_build_messages_format(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx()
        messages = voter._build_messages(ctx)
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Student ID" in messages[1]["content"]
        assert "Module ID" in messages[1]["content"]

    def test_vote_falls_back_to_heuristic_on_llm_failure(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        mock_llm_service.generate.return_value = LLMResponse(
            content="", parsed=None, model="test", provider="test",
            tokens_prompt=0, tokens_completion=0, tokens_total=0,
            confidence_raw=0.0, duration_ms=0.0, success=False,
        )
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.85)
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.evidence.get("heuristic")

    def test_vote_uses_llm_when_successful(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        llm_content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.85,
            "reason_summary": "Student is cognitively ready",
            "reasoning": "The student has strong mastery of prerequisites.",
            "evidence": {"cognitive_alignment": 0.9, "readiness_score": 0.85},
        })
        mock_llm_service.generate.return_value = LLMResponse(
            content=llm_content, parsed=json.loads(llm_content),
            model="gpt-4o", provider="openai",
            tokens_prompt=100, tokens_completion=50, tokens_total=150,
            confidence_raw=0.85, duration_ms=500.0, success=True,
        )
        calibrator._min_samples = 100
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.8, evidence={
            "cognitive_stage": "formal_operational",
            "mastered_concepts": ["algebra", "logic"],
            "weak_concepts": ["calculus"],
            "learning_profile": "visual",
        })
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.voter_name == "pedagogical"
        assert not result.evidence.get("heuristic", False)
        assert "llm_model" in result.evidence

    def test_hallucination_detected_not_severe(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        """LLM vote with moderate hallucination proceeds but records score."""
        llm_content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.99,
            "reason_summary": "Ready",
            "reasoning": "The student is ready with strong preparation",
            "evidence": {},
        })
        mock_llm_service.generate.return_value = LLMResponse(
            content=llm_content, parsed=json.loads(llm_content),
            model="test", provider="test",
            tokens_prompt=50, tokens_completion=30, tokens_total=80,
            confidence_raw=0.99, duration_ms=100.0, success=True,
        )
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.15)
        result = voter.vote(ctx)
        assert not result.evidence.get("heuristic", False)
        assert "hallucination_score" in result.evidence
        assert result.evidence["hallucination_score"] > 0

    def test_register_with_consensus_engine(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        engine = ConsensusEngine(voters=[voter])
        assert engine._voters == [voter]
        assert len(engine._voters) == 1


# ── AdaptiveVoter Tests ────────────────────────────────────

class TestAdaptiveVoter:
    def test_voter_name(self):
        assert AdaptiveVoter.voter_name == "adaptive"

    def test_heuristic_default_approves(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx()
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert result.evidence.get("heuristic")

    def test_build_messages_format(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(evidence={
            "mastered_concepts": ["A", "B"],
            "weak_concepts": ["C"],
            "completed_modules": ["mod-000"],
            "next_modules": ["mod-002"],
        })
        messages = voter._build_messages(ctx)
        assert len(messages) == 2
        assert messages[1]["role"] == "user"
        assert "Mastered concepts" in messages[1]["content"]

    def test_vote_falls_back_on_failure(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        mock_llm_service.generate.return_value = LLMResponse(
            content="", parsed=None, model="test", provider="test",
            tokens_prompt=0, tokens_completion=0, tokens_total=0,
            confidence_raw=0.0, duration_ms=0.0, success=False,
        )
        voter = AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx()
        result = voter.vote(ctx)
        assert result.evidence.get("heuristic")

    def test_vote_uses_llm_when_successful(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        llm_content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.78,
            "reason_summary": "Module fits pathway",
            "reasoning": "The module fills a gap in the student's sequence.",
            "evidence": {"pathway_alignment": 0.8, "sequence_correctness": 0.9},
        })
        mock_llm_service.generate.return_value = LLMResponse(
            content=llm_content, parsed=json.loads(llm_content),
            model="gpt-4o-mini", provider="openai",
            tokens_prompt=80, tokens_completion=40, tokens_total=120,
            confidence_raw=0.78, duration_ms=300.0, success=True,
        )
        calibrator._min_samples = 100
        voter = AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx()
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert not result.evidence.get("heuristic", False)


# ── EvaluationVoter Tests ──────────────────────────────────

class TestEvaluationVoter:
    def test_voter_name(self):
        assert EvaluationVoter.voter_name == "evaluation"

    def test_heuristic_high_score_approves(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.8, evidence={"total_exercises": 5})
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.APPROVE

    def test_heuristic_low_score_rejects(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.3)
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.REJECT

    def test_heuristic_insufficient_evidence_abstains(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.5, evidence={"total_exercises": 1})
        result = voter._heuristic_vote(ctx)
        assert result.decision == VoteDecision.ABSTAIN

    def test_build_messages_format(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(evidence={
            "mastery_scores": {"algebra": 0.9, "logic": 0.8},
            "total_exercises": 10,
            "concepts_covered": ["algebra", "logic"],
        })
        messages = voter._build_messages(ctx)
        assert len(messages) == 2
        assert "Mastery scores" in messages[1]["content"]

    def test_vote_falls_back_on_failure(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        mock_llm_service.generate.return_value = LLMResponse(
            content="", parsed=None, model="test", provider="test",
            tokens_prompt=0, tokens_completion=0, tokens_total=0,
            confidence_raw=0.0, duration_ms=0.0, success=False,
        )
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.8, evidence={"total_exercises": 5})
        result = voter.vote(ctx)
        assert result.evidence.get("heuristic")
        assert result.decision == VoteDecision.APPROVE

    def test_vote_uses_llm_when_successful(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        llm_content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.82,
            "reason_summary": "Ready for evaluation",
            "reasoning": "Student has sufficient practice and mastery.",
            "evidence": {"mastery_readiness": 0.85, "practice_sufficiency": 0.8},
        })
        mock_llm_service.generate.return_value = LLMResponse(
            content=llm_content, parsed=json.loads(llm_content),
            model="gpt-4o-mini", provider="openai",
            tokens_prompt=90, tokens_completion=45, tokens_total=135,
            confidence_raw=0.82, duration_ms=400.0, success=True,
        )
        calibrator._min_samples = 100
        voter = EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser)
        ctx = make_ctx(score=0.75, evidence={
            "mastery_scores": {"concept_a": 0.85, "concept_b": 0.78},
            "total_exercises": 15,
            "concepts_covered": ["concept_a", "concept_b"],
        })
        result = voter.vote(ctx)
        assert result.decision == VoteDecision.APPROVE
        assert not result.evidence.get("heuristic", False)


# ── Integration Patterns ───────────────────────────────────

class TestVoterIntegration:
    """Tests that demonstrate how voters integrate with ConsensusEngine."""

    def test_engine_can_register_all_llm_voters(self, mock_llm_service, budget_tracker, calibrator, guard, parser):
        voters = [
            PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser),
            AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser),
            EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser),
        ]
        engine = ConsensusEngine(voters=voters)
        assert len(engine._voters) == 3
        names = [v.voter_name for v in engine._voters]
        assert "pedagogical" in names
        assert "adaptive" in names
        assert "evaluation" in names

    def test_engine_with_all_voters_processes_vote(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        """Simulates a full ConsensusEngine run with LLM voters (using heuristic fallback)."""
        mock_llm_service.generate.side_effect = [
            LLMResponse(
                content=json.dumps({"decision": "APPROVE", "confidence": 0.9, "reason_summary": "Ready", "reasoning": "...", "evidence": {}}),
                parsed={"decision": "APPROVE", "confidence": 0.9},
                model="test", provider="test", tokens_prompt=50, tokens_completion=30, tokens_total=80,
                confidence_raw=0.9, duration_ms=100.0, success=True,
            )
            for _ in range(3)
        ]
        calibrator._min_samples = 100

        voters = [
            PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser, min_llm_confidence=0.0),
            AdaptiveVoter(mock_llm_service, budget_tracker, calibrator, guard, parser, min_llm_confidence=0.0),
            EvaluationVoter(mock_llm_service, budget_tracker, calibrator, guard, parser, min_llm_confidence=0.0),
        ]
        engine = ConsensusEngine(voters=voters)
        ctx = make_ctx(score=0.8)

        result = engine.run(ctx)
        assert result.decision is not None
        assert len(result.votes) == 3
        assert result.votes[0].voter_name == "pedagogical"
        assert "llm_model" in result.votes[0].evidence

    def test_engine_mixed_heuristic_and_llm(self, mock_llm_service, budget_tracker, calibrator, guard, parser, make_ctx):
        """ConsensusEngine with both deterministic + LLM voters."""
        from app.core.consensus import MasteryVoter, PrereqVoter, SequenceVoter, TimeVoter

        mock_llm_service.generate.side_effect = [
            LLMResponse(
                content=json.dumps({"decision": "APPROVE", "confidence": 0.85, "reason_summary": "Ready", "reasoning": "...", "evidence": {}}),
                parsed={"decision": "APPROVE", "confidence": 0.85},
                model="test", provider="test", tokens_prompt=50, tokens_completion=30, tokens_total=80,
                confidence_raw=0.85, duration_ms=100.0, success=True,
            )
        ]
        calibrator._min_samples = 100

        voters = [
            MasteryVoter(),
            PrereqVoter(),
            SequenceVoter(),
            TimeVoter(),
            PedagogicalVoter(mock_llm_service, budget_tracker, calibrator, guard, parser, min_llm_confidence=0.0),
        ]
        engine = ConsensusEngine(voters=voters)
        ctx = make_ctx(score=0.8)

        result = engine.run(ctx)
        assert len(result.votes) > 4
        voter_names = [v.voter_name for v in result.votes]
        assert "mastery" in voter_names
        assert "pedagogical" in voter_names
