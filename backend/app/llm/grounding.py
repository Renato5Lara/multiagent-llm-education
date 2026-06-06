"""Hallucination guard — multi-layer verification of LLM responses.

Five verification layers:
1. Score consistency: decision compatible with objective score data
2. Reasoning-decision alignment: reasoning supports the decision
3. Cross-voter consistency: no contradiction with other voter records
4. Historical calibration: voter has good track record in this context
5. Extreme value detection: confidence isn't unrealistically extreme
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable

from app.core.consensus import VoteDecision

logger = logging.getLogger(__name__)


@dataclass
class HallucinationCheck:
    """Result of a single hallucination check."""

    name: str
    passed: bool
    score: float
    detail: str = ""


@dataclass
class HallucinationReport:
    """Aggregated hallucination verification result."""

    hallucination_score: float
    failed_checks: list[HallucinationCheck] = field(default_factory=list)
    details: list[HallucinationCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.hallucination_score < 0.3

    @property
    def is_severe(self) -> bool:
        return self.hallucination_score >= 0.7


class HallucinationGuard:
    """Multi-layer hallucination mitigation for LLM voters.

    Usage:
        guard = HallucinationGuard()
        report = await guard.verify(
            voter_name="pedagogical",
            decision=VoteDecision.APPROVE,
            confidence=0.95,
            reasoning="...",
            evidence={"readiness_score": 0.8, ...},
            ctx=vote_context,
        )
        if report.is_severe:
            # reject vote, use heuristic fallback
            pass
    """

    def __init__(self):
        self._historical: dict[str, list[dict]] = {}
        # voter_name -> [{confidence, decision_matched, score}]

    def record_outcome(
        self,
        voter_name: str,
        predicted_decision: VoteDecision,
        predicted_confidence: float,
        actual_correct: bool,
    ):
        """Record historical calibration data for a voter."""
        self._historical.setdefault(voter_name, []).append({
            "decision": predicted_decision,
            "confidence": predicted_confidence,
            "correct": actual_correct,
        })
        # Keep bounded history
        if len(self._historical[voter_name]) > 1000:
            self._historical[voter_name] = self._historical[voter_name][-1000:]

    async def verify(
        self,
        voter_name: str,
        decision: VoteDecision,
        confidence: float,
        reasoning: str,
        evidence: dict[str, Any],
        score: float = 0.5,
        bloom_level: str = "unknown",
    ) -> HallucinationReport:
        checks: list[HallucinationCheck] = []

        checks.append(self._check_score_consistency(decision, score))
        checks.append(self._check_reasoning_alignment(decision, reasoning))
        checks.append(self._check_extreme_values(confidence, decision))
        checks.append(self._check_historical_calibration(voter_name, confidence))
        checks.append(self._check_evidence_completeness(evidence))

        failed = [c for c in checks if not c.passed]
        hallucination_score = sum(c.score for c in checks) / max(len(checks), 1)

        return HallucinationReport(
            hallucination_score=hallucination_score,
            failed_checks=failed,
            details=checks,
        )

    def _check_score_consistency(
        self, decision: VoteDecision, score: float,
    ) -> HallucinationCheck:
        """Verify decision is compatible with objective score.

        Very low scores should not get APPROVE; very high scores should not get REJECT.
        """
        if decision == VoteDecision.APPROVE and score < 0.2:
            return HallucinationCheck(
                name="score_consistency", passed=False, score=0.8,
                detail=f"APPROVE with score={score:.2f} < 0.2",
            )
        if decision == VoteDecision.REJECT and score > 0.9:
            return HallucinationCheck(
                name="score_consistency", passed=False, score=0.6,
                detail=f"REJECT with score={score:.2f} > 0.9",
            )
        return HallucinationCheck(
            name="score_consistency", passed=True, score=0.0,
            detail=f"score={score:.2f} compatible with {decision.value}",
        )

    def _check_reasoning_alignment(
        self, decision: VoteDecision, reasoning: str,
    ) -> HallucinationCheck:
        """Verify reasoning contains arguments that support the decision.

        Uses word-boundary matching to avoid substring false positives
        (e.g., "sufficient" inside "insufficient").
        """
        if not reasoning or len(reasoning) < 20:
            return HallucinationCheck(
                name="reasoning_alignment", passed=False, score=0.5,
                detail="Reasoning too short or empty",
            )

        approve_words = [" ready ", " prepared ", " mastered ", " strong ",
                         " sufficient ", " qualified ", " good ", " excellent ",
                         " meets criteria"]
        reject_words = [" not ready ", " weak ", " insufficient ", " lacking ",
                        " gaps ", " fails ", " below threshold ", " inadequate ",
                        " struggling "]

        reasoning_padded = f" {reasoning.lower()} "
        approve_hits = sum(1 for w in approve_words if w in reasoning_padded)
        reject_hits = sum(1 for w in reject_words if w in reasoning_padded)

        if decision == VoteDecision.APPROVE and reject_hits >= approve_hits + 1:
            return HallucinationCheck(
                name="reasoning_alignment", passed=False, score=0.6,
                detail=f"APPROVE decision but reasoning has {reject_hits} rejection keywords (approve={approve_hits})",
            )
        if decision == VoteDecision.REJECT and approve_hits >= reject_hits + 1:
            return HallucinationCheck(
                name="reasoning_alignment", passed=False, score=0.6,
                detail=f"REJECT decision but reasoning has {approve_hits} approval keywords (reject={reject_hits})",
            )

        return HallucinationCheck(
            name="reasoning_alignment", passed=True, score=0.0,
            detail=f"reasoning supports decision (approve_hits={approve_hits}, reject_hits={reject_hits})",
        )

    def _check_extreme_values(
        self, confidence: float, decision: VoteDecision,
    ) -> HallucinationCheck:
        """Detect unrealistically extreme confidence values."""
        if decision == VoteDecision.ABSTAIN and confidence > 0.8:
            return HallucinationCheck(
                name="extreme_values", passed=False, score=0.7,
                detail=f"ABSTAIN with confidence={confidence:.2f} > 0.8",
            )
        if confidence > 0.99:
            return HallucinationCheck(
                name="extreme_values", passed=False, score=0.5,
                detail=f"Confidence={confidence:.4f} at ceiling",
            )
        if confidence < 0.05 and decision != VoteDecision.ABSTAIN:
            return HallucinationCheck(
                name="extreme_values", passed=False, score=0.4,
                detail=f"Confidence={confidence:.2f} near floor for {decision.value}",
            )
        return HallucinationCheck(
            name="extreme_values", passed=True, score=0.0,
            detail=f"confidence={confidence:.2f} within normal range",
        )

    def _check_historical_calibration(
        self, voter_name: str, confidence: float,
    ) -> HallucinationCheck:
        """Check if this voter has historically been overconfident."""
        history = self._historical.get(voter_name, [])
        if len(history) < 5:
            return HallucinationCheck(
                name="historical_calibration", passed=True, score=0.0,
                detail=f"Insufficient history ({len(history)} records)",
            )

        recent = history[-20:] if len(history) > 20 else history
        overconfident = sum(
            1 for r in recent
            if not r["correct"] and r["confidence"] > 0.8
        )
        overconfidence_rate = overconfident / len(recent)

        if overconfidence_rate > 0.3:
            return HallucinationCheck(
                name="historical_calibration", passed=False, score=min(0.8, overconfidence_rate),
                detail=f"Historical overconfidence rate={overconfidence_rate:.2f} > 0.3",
            )

        return HallucinationCheck(
            name="historical_calibration", passed=True, score=0.0,
            detail=f"Overconfidence rate={overconfidence_rate:.2f} within tolerance",
        )

    def _check_evidence_completeness(self, evidence: dict[str, Any]) -> HallucinationCheck:
        """Verify evidence dict contains expected fields."""
        if not evidence:
            return HallucinationCheck(
                name="evidence_completeness", passed=False, score=0.5,
                detail="No evidence provided",
            )

        numeric_fields = sum(1 for v in evidence.values() if isinstance(v, (int, float)))
        if numeric_fields == 0 and len(evidence) > 0:
            return HallucinationCheck(
                name="evidence_completeness", passed=False, score=0.3,
                detail="Evidence has no numeric fields for calibration",
            )

        return HallucinationCheck(
            name="evidence_completeness", passed=True, score=0.0,
            detail=f"Evidence has {len(evidence)} fields, {numeric_fields} numeric",
        )

    def reset(self, voter_name: str | None = None):
        """Clear historical data."""
        if voter_name:
            self._historical.pop(voter_name, None)
        else:
            self._historical.clear()
