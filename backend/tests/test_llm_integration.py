"""Tests for the LLM integration layer (Phase 0 infrastructure)."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.consensus import VoteDecision
from app.llm import (
    BudgetPeriod,
    BudgetStatus,
    ConfidenceCalibrator,
    HallucinationGuard,
    LLMConfig,
    LLMResponseParser,
    LLMService,
    ParseError,
    ProviderKind,
    TokenBudget,
    TokenBudgetTracker,
)
from app.llm.grounding import HallucinationCheck, HallucinationReport
from app.llm.response_parser import ParsedVote


# ── Config Tests ─────────────────────────────────────────────

class TestLLMConfig:
    def test_default_config(self):
        cfg = LLMConfig()
        assert cfg.model == "gpt-4o-mini"
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 1024

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-4o")
        monkeypatch.setenv("LLM_TEMPERATURE", "0.5")
        monkeypatch.setenv("LLM_MAX_TOKENS", "2048")
        monkeypatch.setenv("LLM_PROVIDER", "anthropic")
        cfg = LLMConfig.from_env()
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.5
        assert cfg.max_tokens == 2048
        assert cfg.provider_kind == ProviderKind.ANTHROPIC

    def test_default_configs_have_budgets(self):
        from app.llm.config import DEFAULT_LLM_CONFIGS
        for name, cfg in DEFAULT_LLM_CONFIGS.items():
            assert cfg.budget_tokens_per_day > 0
            assert cfg.model


# ── TokenBudgetTracker Tests ────────────────────────────────

class TestTokenBudgetTracker:
    def test_check_budget_within_limit(self):
        tracker = TokenBudgetTracker()
        assert tracker.check_budget("test_voter", 100, 1000)
        status = tracker.get_status("test_voter")
        assert status.within_budget
        assert status.limit_tokens == 1000

    def test_check_budget_exceeded(self):
        tracker = TokenBudgetTracker()
        assert not tracker.check_budget("poor_voter", 1000, 500)

    def test_check_budget_unlimited(self):
        tracker = TokenBudgetTracker()
        assert tracker.check_budget("unlimited_voter", 1_000_000, limit_tokens=0)
        assert tracker.check_budget("unlimited_voter", 1_000_000, limit_tokens=-1)

    @pytest.mark.asyncio
    async def test_record_usage_updates_budget(self):
        tracker = TokenBudgetTracker()
        assert tracker.check_budget("voter_a", 300, 500)
        await tracker.record_usage("voter_a", 300)
        status = tracker.get_status("voter_a")
        assert status.used_tokens == 300
        assert status.remaining_tokens == 200

    @pytest.mark.asyncio
    async def test_record_usage_exceeds(self):
        tracker = TokenBudgetTracker()
        await tracker.record_usage("exceed_voter", 400)
        assert not tracker.check_budget("exceed_voter", 200, 500)
        await tracker.record_usage("exceed_voter", 100)
        assert not tracker.check_budget("exceed_voter", 50, 500)

    @pytest.mark.asyncio
    async def test_reset_clears_usage(self):
        tracker = TokenBudgetTracker()
        await tracker.record_usage("voter_a", 400)
        tracker.reset("voter_a")
        status = tracker.get_status("voter_a")
        assert status.used_tokens == 0

    @pytest.mark.asyncio
    async def test_reset_all(self):
        tracker = TokenBudgetTracker()
        await tracker.record_usage("v1", 100)
        await tracker.record_usage("v2", 200)
        tracker.reset()
        assert tracker.get_status("v1").used_tokens == 0
        assert tracker.get_status("v2").used_tokens == 0

    @pytest.mark.asyncio
    async def test_get_all_status(self):
        tracker = TokenBudgetTracker()
        await tracker.record_usage("v1", 100)
        await tracker.record_usage("v2", 200)
        statuses = tracker.get_all_status()
        assert "v1" in statuses
        assert "v2" in statuses
        assert statuses["v1"]["used_tokens"] == 100

    def test_budget_status_fields(self):
        s = BudgetStatus(within_budget=True, used_tokens=100, limit_tokens=1000, remaining_tokens=900, reset_in_seconds=3600.0)
        assert s.within_budget
        assert s.remaining_tokens == 900

    def test_auto_window_reset(self):
        tracker = TokenBudgetTracker()
        budget = TokenBudget(voter_name="test", used_tokens=500, limit_tokens=1000, window_start=time.time() - 86401)
        tracker._budgets["test"] = budget
        assert tracker.check_budget("test", 600, 1000)
        assert budget.used_tokens == 0


# ── ConfidenceCalibrator Tests ──────────────────────────────

class TestConfidenceCalibrator:
    def test_initial_discount_applied(self):
        cal = ConfidenceCalibrator(min_samples=10)
        calibrated = cal.calibrate(0.95, "new_voter")
        assert calibrated == pytest.approx(0.95 * 0.85)

    def test_initial_discount_not_applied_with_sufficient_data(self):
        cal = ConfidenceCalibrator(min_samples=2)
        cal.record_outcome("voter", 0.9, True)
        cal.record_outcome("voter", 0.8, True)
        calibrated = cal.calibrate(0.9, "voter")
        assert calibrated != 0.9 * 0.85

    def test_record_outcome_tracks_data(self):
        cal = ConfidenceCalibrator()
        cal.record_outcome("voter", 0.9, True)
        cal.record_outcome("voter", 0.7, False)
        assert len(cal._calibration_data["voter"]) == 2

    def test_compute_ece_perfect_calibration(self):
        cal = ConfidenceCalibrator(n_bins=5)
        for i in range(50):
            conf = 0.1 + (i % 5) * 0.2
            correct = (i % 5) <= 2
            cal.record_outcome("perfect", conf, correct)
        ece = cal.compute_ece("perfect")
        assert ece >= 0.0

    def test_compute_ece_miscalibrated(self):
        cal = ConfidenceCalibrator(n_bins=5)
        for _ in range(50):
            cal.record_outcome("overconfident", 0.9, False)
        ece = cal.compute_ece("overconfident")
        assert ece > 0.1

    def test_compute_mce(self):
        cal = ConfidenceCalibrator(n_bins=5)
        for _ in range(50):
            cal.record_outcome("voter", 0.9, False)
        mce = cal.compute_mce("voter")
        assert mce > 0.0
        assert mce >= cal.compute_ece("voter")

    def test_get_calibration_snapshot(self):
        cal = ConfidenceCalibrator()
        cal.record_outcome("v1", 0.9, True)
        snap = cal.get_calibration_snapshot()
        assert "v1" in snap
        assert "ece" in snap["v1"]
        assert "n_samples" in snap["v1"]
        assert snap["v1"]["n_samples"] == 1

    def test_reset_single_voter(self):
        cal = ConfidenceCalibrator()
        cal.record_outcome("v1", 0.9, True)
        cal.record_outcome("v2", 0.8, False)
        cal.reset("v1")
        assert "v1" not in cal._calibration_data
        assert "v2" in cal._calibration_data

    def test_reset_all(self):
        cal = ConfidenceCalibrator()
        cal.record_outcome("v1", 0.9, True)
        cal.record_outcome("v2", 0.8, False)
        cal.reset()
        assert len(cal._calibration_data) == 0

    def test_calibrate_clamps_values(self):
        cal = ConfidenceCalibrator()
        assert 0.0 <= cal.calibrate(-0.5, "x") <= 1.0
        assert 0.0 <= cal.calibrate(1.5, "x") <= 1.0


# ── ResponseParser Tests ─────────────────────────────────────

class TestLLMResponseParser:
    def setup_method(self):
        self.parser = LLMResponseParser()

    def test_parse_valid_json(self):
        content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.85,
            "reason_summary": "Student is ready",
            "reasoning": "The student has mastered all prerequisites.",
            "evidence": {"readiness": 0.9}
        })
        result = self.parser.parse_vote(content)
        assert result.decision == VoteDecision.APPROVE
        assert result.confidence == 0.85
        assert result.reason_summary == "Student is ready"

    def test_parse_markdown_code_block(self):
        content = """Here is my analysis:
```json
{
  "decision": "REJECT",
  "confidence": 0.72,
  "reason_summary": "Not ready",
  "reasoning": "Missing prerequisites.",
  "evidence": {"gaps": ["concept_x"]}
}
```"""
        result = self.parser.parse_vote(content)
        assert result.decision == VoteDecision.REJECT
        assert result.confidence == 0.72

    def test_parse_embedded_object(self):
        content = "Some text { \"decision\": \"ABSTAIN\", \"confidence\": 0.5, \"reason_summary\": \"Unsure\", \"reasoning\": \"Need more data\", \"evidence\": {} } trailing"
        result = self.parser.parse_vote(content)
        assert result.decision == VoteDecision.ABSTAIN

    def test_parse_empty_raises(self):
        with pytest.raises(ParseError, match="Empty response"):
            self.parser.parse_vote(None)
        with pytest.raises(ParseError, match="Empty response"):
            self.parser.parse_vote("")
        with pytest.raises(ParseError, match="Empty response"):
            self.parser.parse_vote("   ")

    def test_parse_invalid_raises(self):
        with pytest.raises(ParseError, match="Cannot extract JSON"):
            self.parser.parse_vote("This is not JSON at all")

    def test_parse_decision_variants(self):
        parser = LLMResponseParser()
        for variant in ["APPROVE", "approve", "Approve", "APPROVED", "ACCEPT", "PASS", "YES"]:
            content = json.dumps({"decision": variant, "confidence": 0.8, "reason_summary": "ok", "reasoning": "...", "evidence": {}})
            assert parser.parse_vote(content).decision == VoteDecision.APPROVE

        for variant in ["REJECT", "reject", "DENY", "FAIL", "FALSE"]:
            content = json.dumps({"decision": variant, "confidence": 0.8, "reason_summary": "no", "reasoning": "...", "evidence": {}})
            assert parser.parse_vote(content).decision == VoteDecision.REJECT

        for variant in ["ABSTAIN", "abstain", "UNSURE", "NEUTRAL"]:
            content = json.dumps({"decision": variant, "confidence": 0.5, "reason_summary": "?", "reasoning": "...", "evidence": {}})
            assert parser.parse_vote(content).decision == VoteDecision.ABSTAIN

    def test_parse_confidence_clamping(self):
        parser = LLMResponseParser()
        cases = [("1.5", 1.0), ("-0.5", 0.0), ("0.75", 0.75), ("abc", 0.5)]
        for raw_val, expected in cases:
            content = json.dumps({"decision": "APPROVE", "confidence": raw_val, "reason_summary": "x", "reasoning": "...", "evidence": {}})
            assert parser.parse_vote(content).confidence == expected

    def test_parsed_vote_has_all_fields(self):
        content = json.dumps({
            "decision": "APPROVE",
            "confidence": 0.9,
            "reason_summary": "Ready",
            "reasoning": "Step-by-step analysis...",
            "evidence": {"score": 0.95, "factors": ["a", "b"]}
        })
        r = self.parser.parse_vote(content)
        assert isinstance(r, ParsedVote)
        assert r.evidence["score"] == 0.95


# ── HallucinationGuard Tests ────────────────────────────────

class TestHallucinationGuard:
    def setup_method(self):
        self.guard = HallucinationGuard()

    def test_score_consistency_approve_low_score(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.APPROVE,
            confidence=0.9, reasoning="Good enough",
            evidence={"score": 0.8}, score=0.15,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "score_consistency" in failed_names
        assert report.hallucination_score > 0

    def test_score_consistency_reject_high_score(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.REJECT,
            confidence=0.9, reasoning="Bad",
            evidence={}, score=0.95,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "score_consistency" in failed_names

    def test_reasoning_alignment_mismatch(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.APPROVE,
            confidence=0.9, reasoning="The student is not ready, weak foundation, insufficient preparation",
            evidence={}, score=0.6,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "reasoning_alignment" in failed_names

    def test_extreme_confidence_abstain(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.ABSTAIN,
            confidence=0.95, reasoning="Not sure",
            evidence={}, score=0.5,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "extreme_values" in failed_names

    def test_extreme_confidence_ceiling(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.APPROVE,
            confidence=0.999, reasoning="Perfect student",
            evidence={"readiness": 0.9}, score=0.8,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "extreme_values" in failed_names

    def test_empty_evidence(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.APPROVE,
            confidence=0.8, reasoning="Good",
            evidence={}, score=0.7,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "evidence_completeness" in failed_names

    def test_passes_all_checks(self):
        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="test", decision=VoteDecision.APPROVE,
            confidence=0.8, reasoning="The student has strong readiness and good preparation, meets criteria for advancement",
            evidence={"readiness": 0.85, "alignment": 0.9}, score=0.7,
        ))
        assert len(report.failed_checks) == 0
        assert report.hallucination_score < 0.3

    def test_historical_overconfidence_detected(self):
        for _ in range(10):
            self.guard.record_outcome("overconfident", VoteDecision.APPROVE, 0.95, False)

        import asyncio
        report = asyncio.run(self.guard.verify(
            voter_name="overconfident", decision=VoteDecision.APPROVE,
            confidence=0.9, reasoning="Good",
            evidence={"r": 0.8}, score=0.7,
        ))
        failed_names = [c.name for c in report.failed_checks]
        assert "historical_calibration" in failed_names

    def test_hallucination_report_properties(self):
        r = HallucinationReport(hallucination_score=0.1)
        assert r.passed
        assert not r.is_severe

        r = HallucinationReport(hallucination_score=0.5)
        assert not r.passed
        assert not r.is_severe

        r = HallucinationReport(hallucination_score=0.8)
        assert not r.passed
        assert r.is_severe

    def test_reset(self):
        self.guard.record_outcome("v1", VoteDecision.APPROVE, 0.9, True)
        self.guard.record_outcome("v2", VoteDecision.APPROVE, 0.8, False)
        self.guard.reset("v1")
        assert "v1" not in self.guard._historical
        assert "v2" in self.guard._historical
        self.guard.reset()
        assert len(self.guard._historical) == 0


# ── LLMService Tests (with mock) ────────────────────────────

class TestLLMService:
    @pytest.mark.asyncio
    async def test_budget_exceeded_returns_early(self):
        tracker = TokenBudgetTracker()
        service = LLMService(budget_tracker=tracker)
        response = await service.generate(
            messages=[{"role": "user", "content": "test"}],
            voter_name="poor_voter",
            config=LLMConfig(max_tokens=100, budget_tokens_per_day=10),
        )
        assert not response.success
        assert response.error == "budget_exceeded"

    @pytest.mark.asyncio
    async def test_estimate_tokens(self):
        tokens = LLMService._estimate_tokens(
            [{"role": "user", "content": "Hello world"}], max_tokens=100
        )
        assert tokens > 100

    @pytest.mark.asyncio
    async def test_try_parse_json_valid(self):
        assert LLMService._try_parse_json('{"a": 1}') == {"a": 1}

    @pytest.mark.asyncio
    async def test_try_parse_json_invalid(self):
        assert LLMService._try_parse_json("not json") is None

    @pytest.mark.asyncio
    async def test_try_parse_json_embedded(self):
        result = LLMService._try_parse_json("Text before {\"key\": \"value\"} text after")
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_extract_json_confidence(self):
        assert LLMService._extract_json_confidence({"confidence": 0.85}) == 0.85
        assert LLMService._extract_json_confidence({"confidence": 1.5}) == 1.0
        assert LLMService._extract_json_confidence({}) == 0.5
        assert LLMService._extract_json_confidence(None) == 0.5

    @pytest.mark.asyncio
    async def test_openai_compatible_call(self):
        tracker = TokenBudgetTracker()
        service = LLMService(budget_tracker=tracker)

        mock_response = {
            "choices": [{"message": {"content": '{"decision": "APPROVE", "confidence": 0.85, "reason_summary": "ok", "reasoning": "...", "evidence": {}}'}}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
        }
        service._client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value=mock_response)
        mock_resp.raise_for_status = MagicMock()
        service._client.post = AsyncMock(return_value=mock_resp)

        response = await service.generate(
            messages=[{"role": "user", "content": "test"}],
            voter_name="test_voter",
            config=LLMConfig(
                provider_kind=ProviderKind.OPENAI_COMPATIBLE,
                model="gpt-4o-mini",
                base_url="https://test.api.com/v1",
                api_key="test-key",
                budget_tokens_per_day=100000,
            ),
        )
        assert response.success
        assert response.parsed is not None
        assert response.parsed["decision"] == "APPROVE"
        assert response.tokens_total == 80

        # Verify token usage was recorded
        status = tracker.get_status("test_voter")
        assert status.used_tokens == 80

    @pytest.mark.asyncio
    async def test_openai_compatible_http_error(self):
        tracker = TokenBudgetTracker()
        service = LLMService(budget_tracker=tracker)

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("API Error"))
        service._client.post = AsyncMock(return_value=mock_resp)

        response = await service.generate(
            messages=[{"role": "user", "content": "test"}],
            voter_name="test_voter",
            config=LLMConfig(
                provider_kind=ProviderKind.OPENAI_COMPATIBLE,
                model="gpt-4o-mini",
                base_url="https://test.api.com/v1",
                api_key="test-key",
                max_retries=0,
                budget_tokens_per_day=100000,
            ),
        )
        assert not response.success
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_close(self):
        service = LLMService()
        service._client = AsyncMock()
        await service.close()
        service._client.aclose.assert_called_once()


# ── Prompt Template Tests ───────────────────────────────────

class TestPrompts:
    def test_pedagogical_prompts_exist(self):
        from app.llm.prompts.pedagogical import PEDAGOGICAL_SYSTEM_PROMPT, PEDAGOGICAL_VOTE_PROMPT
        assert len(PEDAGOGICAL_SYSTEM_PROMPT) > 50
        assert "{student_id}" in PEDAGOGICAL_VOTE_PROMPT
        assert "{module_id}" in PEDAGOGICAL_VOTE_PROMPT
        assert "{decision" in PEDAGOGICAL_VOTE_PROMPT or "decision" in PEDAGOGICAL_VOTE_PROMPT

    def test_adaptive_prompts_exist(self):
        from app.llm.prompts.adaptive import ADAPTIVE_SYSTEM_PROMPT, ADAPTIVE_VOTE_PROMPT
        assert len(ADAPTIVE_SYSTEM_PROMPT) > 50
        assert "{student_id}" in ADAPTIVE_VOTE_PROMPT

    def test_evaluation_prompts_exist(self):
        from app.llm.prompts.evaluation import EVALUATION_SYSTEM_PROMPT, EVALUATION_VOTE_PROMPT
        assert len(EVALUATION_SYSTEM_PROMPT) > 50
        assert "{student_id}" in EVALUATION_VOTE_PROMPT

    def test_deliberation_prompts_exist(self):
        from app.llm.prompts.deliberation import (
            DELIBERATION_SYSTEM_PROMPT, DELIBERATION_VOTE_PROMPT,
            MEDIATION_SYSTEM_PROMPT, MEDIATION_PROMPT,
        )
        assert len(DELIBERATION_SYSTEM_PROMPT) > 50
        assert "{previous_decision}" in DELIBERATION_VOTE_PROMPT
        assert "{agent_agendas}" in MEDIATION_PROMPT

    def test_all_prompts_exported(self):
        from app.llm.prompts import (
            PEDAGOGICAL_SYSTEM_PROMPT, PEDAGOGICAL_VOTE_PROMPT,
            ADAPTIVE_SYSTEM_PROMPT, ADAPTIVE_VOTE_PROMPT,
            EVALUATION_SYSTEM_PROMPT, EVALUATION_VOTE_PROMPT,
            DELIBERATION_SYSTEM_PROMPT, DELIBERATION_VOTE_PROMPT,
            MEDIATION_SYSTEM_PROMPT, MEDIATION_PROMPT,
        )
        assert PEDAGOGICAL_SYSTEM_PROMPT
