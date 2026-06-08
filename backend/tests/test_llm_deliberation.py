"""Tests for SwarmDeliberationOrchestrator and MediatorVoter (Phase 2)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    MasteryVoter,
    VoteContext,
    VoteDecision,
)
from app.llm import (
    LLMResponse,
    LLMResponseParser,
    LLMService,
    TokenBudgetTracker,
    ConfidenceCalibrator,
    HallucinationGuard,
)
from app.llm.deliberation import (
    DeliberationPhase,
    DeliberationResult,
    RoundResult,
    SwarmDeliberationOrchestrator,
)
from app.llm.voters import (
    AdaptiveVoter,
    EvaluationVoter,
    MediatorVoter,
    PedagogicalVoter,
)


# ── Fixtures ─────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    s = MagicMock(spec=LLMService)
    s.generate = AsyncMock()
    return s


@pytest.fixture
def budget():
    return TokenBudgetTracker()


@pytest.fixture
def cal():
    c = ConfidenceCalibrator(min_samples=100)
    return c


@pytest.fixture
def guard():
    return HallucinationGuard()


@pytest.fixture
def parser():
    return LLMResponseParser()


@pytest.fixture
def make_voters(mock_llm, budget, cal, guard, parser):
    """Factory for pre-configured LLM voters with mock LLM."""

    def _make(responses: list[dict] | None = None):
        if responses:
            mock_llm.generate.side_effect = [
                LLMResponse(
                    content=json.dumps(r), parsed=r,
                    model="test", provider="test",
                    tokens_prompt=50, tokens_completion=30, tokens_total=80,
                    confidence_raw=r.get("confidence", 0.8), duration_ms=100.0, success=True,
                )
                for r in responses
            ]
        return [
            PedagogicalVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0),
            AdaptiveVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0),
            EvaluationVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0),
        ]

    return _make


@pytest.fixture
def make_ctx():
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

    def _make(score=0.75, evidence=None):
        return VoteContext(
            uow=MagicMock(), module_id="mod-001",
            student_id="stu-001", course_id="course-001",
            path_id="path-001", score=score,
            module=FakeModule(), path=FakePath(),
            evidence=evidence or {},
        )
    return _make


# ── SwarmDeliberationOrchestrator Tests ──────────────────

class TestSwarmDeliberationOrchestrator:
    def test_converges_on_first_round_when_unanimous(self, mock_llm, make_voters, make_ctx):
        """Round 1 unanimous + high confidence → immediate convergence."""
        # Raw confidence 0.95 → calibrated = 0.95*0.85 = 0.8075, threshold at 0.8
        responses = [
            {"decision": "APPROVE", "confidence": 0.95, "reason_summary": "A", "reasoning": "...", "evidence": {"r": 0.95}},
            {"decision": "APPROVE", "confidence": 0.95, "reason_summary": "B", "reasoning": "...", "evidence": {"r": 0.95}},
            {"decision": "APPROVE", "confidence": 0.95, "reason_summary": "C", "reasoning": "...", "evidence": {"r": 0.95}},
        ]
        voters = make_voters(responses)
        engine = ConsensusEngine(voters=voters)
        orch = SwarmDeliberationOrchestrator(engine, convergence_threshold=0.8)

        import asyncio
        result = asyncio.run(orch.deliberate(make_ctx(), voters, []))

        assert result.converged
        assert result.total_rounds == 1
        assert result.rounds_to_converge == 1
        assert result.final_result is not None
        assert result.final_result.decision == VoteDecision.APPROVE

    def test_does_not_converge_on_mixed_votes(self, mock_llm, make_voters, make_ctx):
        """Mixed decisions → multiple rounds."""
        voters = make_voters([
            {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Strong readiness", "evidence": {"r": 0.9}},
            {"decision": "REJECT", "confidence": 0.85, "reason_summary": "B", "reasoning": "Weak foundation", "evidence": {"r": 0.85}},
            {"decision": "APPROVE", "confidence": 0.88, "reason_summary": "C", "reasoning": "Good profile", "evidence": {"r": 0.88}},
        ])
        engine = ConsensusEngine(voters=voters)
        orch = SwarmDeliberationOrchestrator(engine, max_rounds=2, convergence_threshold=0.8)

        # Round 2: one voter changes to APPROVE (still not unanimous)
        voters2 = make_voters([
            {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Still strong", "evidence": {"r": 0.9}},
            {"decision": "APPROVE", "confidence": 0.7, "reason_summary": "B revised", "reasoning": "Reconsidering", "evidence": {"r": 0.7}},
            {"decision": "APPROVE", "confidence": 0.88, "reason_summary": "C", "reasoning": "Still good", "evidence": {"r": 0.88}},
        ])
        # Re-assign side_effect for round 2
        mock_llm.generate.side_effect = [
            LLMResponse(content=json.dumps(r), parsed=r, model="test", provider="test",
                        tokens_prompt=50, tokens_completion=30, tokens_total=80,
                        confidence_raw=r["confidence"], duration_ms=100.0, success=True)
            for r in [
                {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Strong readiness", "evidence": {"r": 0.9}},
                {"decision": "REJECT", "confidence": 0.85, "reason_summary": "B", "reasoning": "Weak foundation", "evidence": {"r": 0.85}},
                {"decision": "APPROVE", "confidence": 0.88, "reason_summary": "C", "reasoning": "Good profile", "evidence": {"r": 0.88}},
                # Round 2
                {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Still strong", "evidence": {"r": 0.9}},
                {"decision": "APPROVE", "confidence": 0.7, "reason_summary": "B revised", "reasoning": "Reconsidering", "evidence": {"r": 0.7}},
                {"decision": "APPROVE", "confidence": 0.88, "reason_summary": "C", "reasoning": "Still good", "evidence": {"r": 0.88}},
            ]
        ]

        import asyncio
        result = asyncio.run(orch.deliberate(make_ctx(), voters, []))

        assert result.total_rounds == 2
        assert not result.converged  # confidence 0.7 < 0.8 threshold
        assert len(result.rounds) == 2

    def test_vote_shift_rate_tracks_changes(self, mock_llm, make_voters, make_ctx):
        """vote_shift_rate > 0 when voters change decision."""
        voters = make_voters()
        mock_llm.generate.side_effect = [
            # Round 1: mixed
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Ready", "evidence": {}}),
                       parsed={"decision": "APPROVE"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.9, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "REJECT", "confidence": 0.8, "reason_summary": "B", "reasoning": "Not ready", "evidence": {}}),
                       parsed={"decision": "REJECT"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.8, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.85, "reason_summary": "C", "reasoning": "OK", "evidence": {}}),
                       parsed={"decision": "APPROVE"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.85, duration_ms=100.0, success=True),
            # Round 2: one changes
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Ready", "evidence": {}}),
                       parsed={"decision": "APPROVE"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.9, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.75, "reason_summary": "B revised", "reasoning": "Changed mind", "evidence": {}}),
                       parsed={"decision": "APPROVE"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.75, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.85, "reason_summary": "C", "reasoning": "OK", "evidence": {}}),
                       parsed={"decision": "APPROVE"}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=0.85, duration_ms=100.0, success=True),
        ]
        engine = ConsensusEngine(voters=voters)
        orch = SwarmDeliberationOrchestrator(engine, max_rounds=2, convergence_threshold=0.9)

        import asyncio
        result = asyncio.run(orch.deliberate(make_ctx(), voters, []))

        assert result.vote_shift_rate > 0
        assert result.total_rounds == 2

    def test_build_deliberation_context(self, make_ctx):
        """Deliberation context includes previous round voting data."""
        from app.llm.deliberation import RoundResult

        prev_votes = [
            ConsensusVote(voter_name="pedagogical", decision=VoteDecision.APPROVE, confidence=0.9,
                         reason="Ready", evidence={"reasoning": "Cognitive alignment good"}),
            ConsensusVote(voter_name="adaptive", decision=VoteDecision.REJECT, confidence=0.8,
                         reason="Not aligned", evidence={"reasoning": "Pathway mismatch"}),
        ]
        prev_round = RoundResult(round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=prev_votes)

        engine = ConsensusEngine(voters=[])
        orch = SwarmDeliberationOrchestrator(engine)
        ctx = orch._build_deliberation_context(2, [prev_round])

        assert "pedagogical" in ctx
        assert "adaptive" in ctx
        assert "approve" in ctx
        assert "reject" in ctx
        assert "Cognitive alignment" in ctx

    def test_enrich_ctx_injects_deliberation(self, make_ctx):
        """Enriched context has deliberation_context in evidence."""
        engine = ConsensusEngine(voters=[])
        orch = SwarmDeliberationOrchestrator(engine)
        ctx = make_ctx()
        enriched = orch._enrich_ctx(ctx, "deliberation data")
        assert enriched.evidence.get("deliberation_context") == "deliberation data"
        assert enriched.student_id == ctx.student_id
        assert enriched.module_id == ctx.module_id
        assert enriched.score == ctx.score

    def test_heuristic_voters_keep_their_vote(self, mock_llm, make_voters, make_ctx):
        """Heuristic voters' votes stay constant across rounds."""
        heuristic = [MasteryVoter()]
        llm_voters = make_voters([
            {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Ready", "evidence": {}},
            {"decision": "REJECT", "confidence": 0.8, "reason_summary": "B", "reasoning": "Not", "evidence": {}},
            {"decision": "APPROVE", "confidence": 0.85, "reason_summary": "C", "reasoning": "OK", "evidence": {}},
        ])
        mock_llm.generate.side_effect = [
            LLMResponse(content=json.dumps(r), parsed=r, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80,
                       confidence_raw=r["confidence"], duration_ms=100.0, success=True)
            for r in [
                {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Ready", "evidence": {}},
                {"decision": "REJECT", "confidence": 0.8, "reason_summary": "B", "reasoning": "Not", "evidence": {}},
                {"decision": "APPROVE", "confidence": 0.85, "reason_summary": "C", "reasoning": "OK", "evidence": {}},
                # Round 2 - same
                {"decision": "APPROVE", "confidence": 0.9, "reason_summary": "A", "reasoning": "Ready", "evidence": {}},
                {"decision": "REJECT", "confidence": 0.8, "reason_summary": "B", "reasoning": "Not", "evidence": {}},
                {"decision": "APPROVE", "confidence": 0.85, "reason_summary": "C", "reasoning": "OK", "evidence": {}},
            ]
        ]
        engine = ConsensusEngine(voters=llm_voters + heuristic)
        orch = SwarmDeliberationOrchestrator(engine, max_rounds=2, convergence_threshold=0.95)

        import asyncio
        result = asyncio.run(orch.deliberate(make_ctx(score=0.8), llm_voters, heuristic))

        # MasteryVoter (heuristic) should appear in all rounds
        for r in result.rounds:
            names = [v.voter_name for v in r.votes]
            assert "mastery" in names

    def test_aggregate_approve(self, make_ctx):
        """Aggregation produces APPROVE when majority approves."""
        votes = [
            ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8),
        ]
        result = SwarmDeliberationOrchestrator._aggregate(make_ctx(), votes)
        assert result.decision == VoteDecision.APPROVE
        import pytest
        assert result.confidence == pytest.approx(0.85)

    def test_aggregate_reject(self, make_ctx):
        """Any reject triggers REJECT."""
        votes = [
            ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.7),
        ]
        result = SwarmDeliberationOrchestrator._aggregate(make_ctx(), votes)
        assert result.decision == VoteDecision.REJECT
        assert result.confidence == 0.7

    def test_aggregate_all_abstain(self, make_ctx):
        """All abstain → ABSTAIN with 0 confidence."""
        votes = [
            ConsensusVote(voter_name="a", decision=VoteDecision.ABSTAIN, confidence=0.5),
            ConsensusVote(voter_name="b", decision=VoteDecision.ABSTAIN, confidence=0.5),
        ]
        result = SwarmDeliberationOrchestrator._aggregate(make_ctx(), votes)
        assert result.decision == VoteDecision.ABSTAIN
        assert result.confidence == 0.0


# ── MediatorVoter Tests ─────────────────────────────────

class TestMediatorVoter:
    def test_voter_name(self):
        assert MediatorVoter.voter_name == "mediator"

    def test_build_messages_includes_history(self, mock_llm, budget, cal, guard, parser, make_ctx):
        voter = MediatorVoter(mock_llm, budget, cal, guard, parser)
        ctx = make_ctx(evidence={
            "vote_history": "Round 1: pedagogical=APPROVE(0.9)",
            "agent_agendas": "pedagogical: Ready\nadaptive: Not ready",
        })
        messages = voter._build_messages(ctx)
        assert len(messages) == 2
        assert "Vote History" in messages[1]["content"]
        assert "Agent Agendas" in messages[1]["content"]
        assert "Student ID" in messages[1]["content"]

    def test_heuristic_fallback_abstains(self, mock_llm, budget, cal, guard, parser, make_ctx):
        voter = MediatorVoter(mock_llm, budget, cal, guard, parser)
        result = voter._heuristic_vote(make_ctx())
        assert result.decision == VoteDecision.ABSTAIN
        assert result.evidence.get("heuristic")


# ── DeliberationResult Tests ────────────────────────────

class TestDeliberationResult:
    def test_vote_shift_rate_no_rounds(self):
        r = DeliberationResult(ctx=MagicMock())
        assert r.vote_shift_rate == 0.0

    def test_vote_shift_rate_single_round(self):
        r = DeliberationResult(ctx=MagicMock())
        r.rounds.append(RoundResult(round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[]))
        assert r.vote_shift_rate == 0.0

    def test_vote_shift_rate_with_changes(self):
        r = DeliberationResult(ctx=MagicMock())
        r.rounds.append(RoundResult(round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
            ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8),
        ]))
        r.rounds.append(RoundResult(round_number=2, phase=DeliberationPhase.REVOTE, votes=[
            ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.7),
        ]))
        assert r.vote_shift_rate == 0.5

    def test_rounds_to_converge_not_converged(self):
        r = DeliberationResult(ctx=MagicMock(), total_rounds=3, converged=False)
        assert r.rounds_to_converge == 3

    def test_rounds_to_converge_converged(self):
        r = DeliberationResult(ctx=MagicMock(), converged=True)
        r.rounds.append(RoundResult(round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[]))
        r.rounds.append(RoundResult(round_number=2, phase=DeliberationPhase.REVOTE, votes=[], converged=True))
        assert r.rounds_to_converge == 2

    def test_to_dict(self):
        r = DeliberationResult(ctx=MagicMock(), converged=True, total_rounds=2)
        r.final_result = MagicMock()
        r.final_result.decision = VoteDecision.APPROVE
        r.final_result.confidence = 0.85
        d = r.to_dict()
        assert d["converged"] is True
        assert d["total_rounds"] == 2
        assert d["final_decision"] == "approve"


# ── RoundResult Tests ───────────────────────────────────

class TestRoundResult:
    def test_to_dict(self):
        rr = RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=[ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9)],
            converged=True, confidence=0.9,
        )
        d = rr.to_dict()
        assert d["round"] == 1
        assert d["phase"] == "first_vote"
        assert d["converged"] is True
        assert d["decisions"]["a"] == "approve"


# ── DeliberationContext Injection ───────────────────────

class TestDeliberationContextInjection:
    """Verifies that HybridVoter injects deliberation context into prompts."""

    def test_deliberation_context_appended_to_user_message(self, mock_llm, budget, cal, guard, parser, make_ctx):
        """When deliberation_context is in evidence, it gets appended to user prompt."""
        voter = PedagogicalVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0)
        mock_llm.generate.return_value = LLMResponse(
            content=json.dumps({"decision": "APPROVE", "confidence": 0.8, "reason_summary": "OK", "reasoning": "...", "evidence": {}}),
            parsed={"decision": "APPROVE", "confidence": 0.8},
            model="test", provider="test",
            tokens_prompt=50, tokens_completion=30, tokens_total=80,
            confidence_raw=0.8, duration_ms=100.0, success=True,
        )
        ctx = make_ctx(evidence={"deliberation_context": "Agent adaptive: REJECT with confidence 0.8. Reasoning: Pathway mismatch."})

        import asyncio
        asyncio.run(voter._async_vote(ctx))

        # Verify deliberation context was passed in messages
        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs[1]["messages"]
        assert any("Razonamientos de Otros Agentes" in m["content"] for m in messages if m["role"] == "user")

    def test_no_deliberation_context_when_not_provided(self, mock_llm, budget, cal, guard, parser, make_ctx):
        """Without deliberation_context, prompt is unchanged."""
        voter = PedagogicalVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0)
        mock_llm.generate.return_value = LLMResponse(
            content=json.dumps({"decision": "APPROVE", "confidence": 0.8, "reason_summary": "OK", "reasoning": "...", "evidence": {}}),
            parsed={"decision": "APPROVE"},
            model="test", provider="test",
            tokens_prompt=50, tokens_completion=30, tokens_total=80,
            confidence_raw=0.8, duration_ms=100.0, success=True,
        )

        import asyncio
        asyncio.run(voter._async_vote(make_ctx()))

        call_kwargs = mock_llm.generate.call_args
        messages = call_kwargs[1]["messages"]
        user_msg = [m["content"] for m in messages if m["role"] == "user"][0]
        assert "Razonamientos" not in user_msg


# ── Integration: Full deliberation pipeline ────────────

class TestFullDeliberationPipeline:
    def test_multi_round_with_mediation(self, mock_llm, budget, cal, guard, parser, make_ctx):
        """Full pipeline: 3 rounds → mediation when not converged."""
        empty_resp = {"decision": "APPROVE", "confidence": 0.8, "reason_summary": "X", "reasoning": "...", "evidence": {}}
        mediator = MediatorVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0)
        voters = [
            PedagogicalVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0),
            AdaptiveVoter(mock_llm, budget, cal, guard, parser, min_llm_confidence=0.0),
        ]
        mock_llm.generate.side_effect = [
            # Round 1 - mixed
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.6, **empty_resp}), parsed=empty_resp, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.6, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "REJECT", "confidence": 0.7, **empty_resp}), parsed={"decision": "REJECT", **empty_resp}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.7, duration_ms=100.0, success=True),
            # Round 2 - still mixed
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.6, **empty_resp}), parsed=empty_resp, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.6, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "REJECT", "confidence": 0.7, **empty_resp}), parsed={"decision": "REJECT", **empty_resp}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.7, duration_ms=100.0, success=True),
            # Round 3 - still mixed
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.6, **empty_resp}), parsed=empty_resp, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.6, duration_ms=100.0, success=True),
            LLMResponse(content=json.dumps({"decision": "REJECT", "confidence": 0.7, **empty_resp}), parsed={"decision": "REJECT", **empty_resp}, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.7, duration_ms=100.0, success=True),
            # Mediation
            LLMResponse(content=json.dumps({"decision": "APPROVE", "confidence": 0.65, **empty_resp}), parsed=empty_resp, model="test", provider="test",
                       tokens_prompt=50, tokens_completion=30, tokens_total=80, confidence_raw=0.65, duration_ms=100.0, success=True),
        ]
        engine = ConsensusEngine(voters=voters)
        orch = SwarmDeliberationOrchestrator(engine, max_rounds=3, convergence_threshold=0.9, mediator=mediator)

        import asyncio
        result = asyncio.run(orch.deliberate(make_ctx(), voters, []))

        assert result.total_rounds == 3
        assert result.mediation_used
        assert result.final_result is not None
