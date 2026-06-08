"""Tests for SwarmMetrics and SharedMemoryStore integration (Phase 3)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.consensus import (
    ConsensusEngine,
    ConsensusVote,
    VoteContext,
    VoteDecision,
)
from app.llm.deliberation import (
    DeliberationPhase,
    DeliberationResult,
    RoundResult,
    SwarmDeliberationOrchestrator,
)
from app.llm.metrics import (
    SwarmMetrics,
    _compute_calibration_delta,
    _compute_cognitive_diversity,
    _compute_cross_pollination_rate,
    _compute_deliberation_impact,
    _compute_polarization_index,
    _get_reasoning_text_safe,
    _jaccard_distance,
    _jaccard_similarity,
    _word_ngrams,
)


# ── N-gram utility tests ─────────────────────────────────

class TestNgramUtils:
    def test_word_ngrams_basic(self):
        result = _word_ngrams("a b c d", n=2)
        assert "a b" in result
        assert "b c" in result
        assert "c d" in result
        assert len(result) == 3

    def test_word_ngrams_shorter_than_n(self):
        result = _word_ngrams("hello", n=2)
        assert result == {"hello"}

    def test_word_ngrams_empty(self):
        assert _word_ngrams("") == set()

    def test_word_ngrams_case_insensitive(self):
        result = _word_ngrams("Hello World", n=1)
        assert "hello" in result
        assert "world" in result

    def test_jaccard_similarity_identical(self):
        a = {"a", "b", "c"}
        assert _jaccard_similarity(a, a) == 1.0

    def test_jaccard_similarity_disjoint(self):
        a = {"a", "b"}
        b = {"c", "d"}
        assert _jaccard_similarity(a, b) == 0.0

    def test_jaccard_similarity_partial(self):
        a = {"a", "b", "c"}
        b = {"b", "c", "d"}
        assert _jaccard_similarity(a, b) == 0.5

    def test_jaccard_similarity_empty(self):
        assert _jaccard_similarity(set(), {"a"}) == 0.0
        assert _jaccard_similarity(set(), set()) == 0.0

    def test_jaccard_distance(self):
        assert _jaccard_distance({"a", "b"}, {"a", "b"}) == 0.0
        assert _jaccard_distance({"a"}, {"b"}) == 1.0


# ── Reasoning extraction ─────────────────────────────────

class TestReasoningExtraction:
    def test_reasoning_from_evidence(self):
        vote = ConsensusVote(voter_name="t", decision=VoteDecision.APPROVE, confidence=0.8,
                             evidence={"reasoning": "deep analysis"})
        assert _get_reasoning_text_safe(vote) == "deep analysis"

    def test_reasoning_from_reason_summary(self):
        vote = ConsensusVote(voter_name="t", decision=VoteDecision.APPROVE, confidence=0.8,
                             evidence={"reason_summary": "summary"})
        assert _get_reasoning_text_safe(vote) == "summary"

    def test_reasoning_from_reason_field(self):
        vote = ConsensusVote(voter_name="t", decision=VoteDecision.APPROVE, confidence=0.8,
                             reason="fallback reason")
        assert _get_reasoning_text_safe(vote) == "fallback reason"

    def test_reasoning_fallback_empty(self):
        vote = ConsensusVote(voter_name="t", decision=VoteDecision.APPROVE, confidence=0.8)
        assert _get_reasoning_text_safe(vote) == ""


# ── Cognitive Diversity ──────────────────────────────────

class TestCognitiveDiversity:
    def test_single_round_identical_reasoning(self):
        """All voters use identical reasoning → diversity = 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="Student is ready for this module"),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8,
                              reason="Student is ready for this module"),
            ],
        ))
        diversity = _compute_cognitive_diversity(result)
        assert diversity == 0.0

    def test_single_round_different_reasoning(self):
        """All voters use completely different reasoning → diversity ≈ 1."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="alpha beta gamma delta epsilon zeta eta theta"),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="one two three four five six seven eight nine ten"),
            ],
        ))
        diversity = _compute_cognitive_diversity(result)
        assert diversity > 0.5

    def test_single_voter(self):
        """Single voter → diversity = 0 (no pairs)."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="Some reasoning here"),
            ],
        ))
        assert _compute_cognitive_diversity(result) == 0.0

    def test_averages_across_rounds(self):
        """Diversity averages over all rounds."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE,
            votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="identical text here"),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8,
                              reason="identical text here"),
            ],
        ))
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE,
            votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="completely different unique singular"),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8,
                              reason="unrelated distinct separate various"),
            ],
        ))
        diversity = _compute_cognitive_diversity(result)
        assert 0.0 < diversity < 1.0
        # Should be > 0 since round 2 has high diversity
        assert diversity > 0.3


# ── Deliberation Impact ──────────────────────────────────

class TestDeliberationImpact:
    def test_single_round(self):
        """Single round → impact = 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ],
        ))
        assert _compute_deliberation_impact(result) == 0.0

    def test_vote_shift_and_confidence_change(self):
        """Voter changes decision and confidence → impact > 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="initial"),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="initial"),
            ],
        ))
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.95,
                              reason="revised"),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.65,
                              reason="revised"),
            ],
        ))
        impact = _compute_deliberation_impact(result)
        assert impact > 0.0


# ── Polarization Index ──────────────────────────────────

class TestPolarizationIndex:
    def test_all_same_confidence(self):
        """All same confidence → polarization = 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.8),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8),
            ],
        ))
        assert _compute_polarization_index(result) == 0.0

    def test_high_spread(self):
        """Spread out confidences → high polarization."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.95),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.1),
            ],
        ))
        polarization = _compute_polarization_index(result)
        assert polarization > 0.5

    def test_single_voter(self):
        """Single voter → polarization = 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.8),
            ],
        ))
        assert _compute_polarization_index(result) == 0.0

    def test_no_rounds(self):
        assert _compute_polarization_index(DeliberationResult(ctx=MagicMock())) == 0.0


# ── Cross-pollination Rate ──────────────────────────────

class TestCrossPollinationRate:
    def test_less_than_two_rounds(self):
        """Single round → no cross-pollination possible."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
            ],
        ))
        assert _compute_cross_pollination_rate(result) == 0.0

    def test_no_shared_reasoning_change(self):
        """Voters keep identical reasoning across rounds → no cross-pollination."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="stable position on this matter"),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="different perspective entirely"),
            ],
        ))
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="stable position on this matter"),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="different perspective entirely"),
            ],
        ))
        rate = _compute_cross_pollination_rate(result)
        assert rate == 0.0

    def test_cross_pollination_detected(self):
        """Voter adopts language from another voter → cross-pollination."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="alpha beta gamma delta epsilon"),
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="zeta eta theta iota kappa"),
            ],
        ))
        # Voter "a" now uses voter "b"'s reasoning style
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="theta iota kappa zeta eta"),  # similar to b's r1
                ConsensusVote(voter_name="b", decision=VoteDecision.REJECT, confidence=0.8,
                              reason="zeta eta theta iota kappa"),  # unchanged
            ],
        ))
        rate = _compute_cross_pollination_rate(result)
        assert rate > 0.0


# ── Calibration Delta ───────────────────────────────────

class TestCalibrationDelta:
    def test_single_round(self):
        """Single round → delta = 0."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.8),
            ],
        ))
        assert _compute_calibration_delta(result) == 0.0

    def test_confidence_increases(self):
        """Confidence goes up → positive delta."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.6),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.6),
            ],
        ))
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.8),
            ],
        ))
        delta = _compute_calibration_delta(result)
        assert delta > 0.0

    def test_confidence_decreases(self):
        """Confidence goes down (more cautious) → negative delta."""
        result = DeliberationResult(ctx=MagicMock())
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.9),
            ],
        ))
        result.rounds.append(RoundResult(
            round_number=2, phase=DeliberationPhase.REVOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.5),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.5),
            ],
        ))
        delta = _compute_calibration_delta(result)
        assert delta < 0.0


# ── SwarmMetrics.compute ────────────────────────────────

class TestSwarmMetricsCompute:
    def test_empty_result(self):
        """Empty result → all metrics default to 0."""
        result = DeliberationResult(ctx=MagicMock())
        metrics = SwarmMetrics.compute(result)
        assert metrics.cognitive_diversity == 0.0
        assert metrics.deliberation_impact == 0.0
        assert metrics.polarization_index == 0.0
        assert metrics.cross_pollination_rate == 0.0
        assert metrics.calibration_delta == 0.0

    def test_single_round_full_metrics(self):
        """Fully converged single round → measurable metrics."""
        result = DeliberationResult(ctx=MagicMock(), converged=True, total_rounds=1)
        result.rounds.append(RoundResult(
            round_number=1, phase=DeliberationPhase.FIRST_VOTE, votes=[
                ConsensusVote(voter_name="a", decision=VoteDecision.APPROVE, confidence=0.9,
                              reason="strong cognitive readiness"),
                ConsensusVote(voter_name="b", decision=VoteDecision.APPROVE, confidence=0.85,
                              reason="excellent pathway alignment"),
                ConsensusVote(voter_name="c", decision=VoteDecision.APPROVE, confidence=0.88,
                              reason="good evaluation metrics"),
            ],
        ))
        result.final_result = MagicMock()
        result.final_result.decision = VoteDecision.APPROVE
        result.final_result.confidence = 0.85

        metrics = SwarmMetrics.compute(result)
        # Cognitive diversity should be > 0 since reasoning differs
        assert metrics.cognitive_diversity > 0.0
        # Single round → no deliberation impact
        assert metrics.deliberation_impact == 0.0
        assert metrics.polarization_index >= 0.0
        assert metrics.cross_pollination_rate == 0.0
        assert metrics.calibration_delta == 0.0

    def test_to_dict_format(self):
        """to_dict returns all expected keys."""
        metrics = SwarmMetrics(
            cognitive_diversity=0.5,
            deliberation_impact=0.3,
            polarization_index=0.1,
            cross_pollination_rate=0.0,
            calibration_delta=0.2,
        )
        d = metrics.to_dict()
        assert set(d.keys()) == {
            "cognitive_diversity", "deliberation_impact",
            "polarization_index", "cross_pollination_rate",
            "calibration_delta",
        }
        assert d["cognitive_diversity"] == 0.5


# ── SharedMemoryStore Integration ───────────────────────

class TestSharedMemoryStoreIntegration:
    @pytest.mark.asyncio
    async def test_publishes_round_observations(self):
        """Orchestrator publishes round 1 votes to shared memory."""
        store = AsyncMock()
        voter = MagicMock()
        voter.voter_name = "test_voter"
        voter.vote.return_value = ConsensusVote(
            voter_name="test_voter", decision=VoteDecision.APPROVE,
            confidence=0.8, reason="test",
        )

        engine = ConsensusEngine(voters=[voter])
        orch = SwarmDeliberationOrchestrator(engine)
        ctx = MagicMock()
        ctx.student_id = "stu-001"
        ctx.module_id = "mod-001"
        ctx.evidence = {}
        ctx.shared_memory = None

        await orch.deliberate(ctx, [voter], [], shared_memory_store=store)

        # Should have published at least one observation
        assert store.publish_observation.called

    @pytest.mark.asyncio
    async def test_publishes_final_result_on_convergence(self):
        """Orchestrator publishes final result when converged."""
        store = AsyncMock()
        voter = MagicMock()
        voter.voter_name = "test_voter"
        voter.vote.return_value = ConsensusVote(
            voter_name="test_voter", decision=VoteDecision.APPROVE,
            confidence=0.95, reason="ready",
        )

        engine = ConsensusEngine(voters=[voter])
        orch = SwarmDeliberationOrchestrator(engine, convergence_threshold=0.8)
        ctx = MagicMock()
        ctx.student_id = "stu-001"
        ctx.module_id = "mod-001"
        ctx.evidence = {}
        ctx.shared_memory = None

        result = await orch.deliberate(ctx, [voter], [], shared_memory_store=store)

        assert result.converged
        # Should have called publish for both round and final
        assert store.publish_observation.call_count >= 2

    @pytest.mark.asyncio
    async def test_no_store_skips_publishing(self):
        """Without store, orchestrator does not publish."""
        voter = MagicMock()
        voter.voter_name = "test_voter"
        voter.vote.return_value = ConsensusVote(
            voter_name="test_voter", decision=VoteDecision.APPROVE,
            confidence=0.8, reason="ready",
        )

        engine = ConsensusEngine(voters=[voter])
        orch = SwarmDeliberationOrchestrator(engine)
        ctx = MagicMock()
        ctx.student_id = "stu-001"
        ctx.module_id = "mod-001"
        ctx.evidence = {}
        ctx.shared_memory = None

        result = await orch.deliberate(ctx, [voter], [])
        assert result.converged  # works as before

    @pytest.mark.asyncio
    async def test_publish_error_does_not_block(self):
        """Publish failures are logged but don't crash the orchestrator."""
        store = AsyncMock()
        store.publish_observation.side_effect = RuntimeError("store down")
        voter = MagicMock()
        voter.voter_name = "test_voter"
        voter.vote.return_value = ConsensusVote(
            voter_name="test_voter", decision=VoteDecision.APPROVE,
            confidence=0.95, reason="ready",
        )

        engine = ConsensusEngine(voters=[voter])
        orch = SwarmDeliberationOrchestrator(engine, convergence_threshold=0.8)
        ctx = MagicMock()
        ctx.student_id = "stu-001"
        ctx.module_id = "mod-001"
        ctx.evidence = {}
        ctx.shared_memory = None

        result = await orch.deliberate(ctx, [voter], [], shared_memory_store=store)
        assert result.converged  # still works despite store failure
