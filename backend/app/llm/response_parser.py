"""Response parser — extracts structured data from LLM responses.

Handles:
- Direct JSON parsing
- JSON extraction from markdown code blocks
- Schema validation
- Type coercion for confidence, decision, and evidence fields
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from app.core.consensus import VoteDecision

logger = logging.getLogger(__name__)


class ParseError(Exception):
    """Raised when LLM response cannot be parsed."""


@dataclass
class ParsedVote:
    """Structured vote parsed from an LLM response."""

    decision: VoteDecision
    confidence: float
    reason_summary: str
    reasoning: str
    evidence: dict[str, Any]


class LLMResponseParser:
    """Parses and validates structured JSON from LLM responses.

    Expected format:
        {
            "decision": "APPROVE" | "REJECT" | "ABSTAIN",
            "confidence": 0.0-1.0,
            "reason_summary": "...",
            "reasoning": "...",
            "evidence": { ... }
        }
    """

    def parse_vote(self, content: str | None) -> ParsedVote:
        """Parse LLM response into a structured vote.

        Attempts:
        1. Direct JSON parse
        2. JSON extraction from ```json ... ``` blocks
        3. JSON extraction from standalone {...} objects
        4. Regex-based field extraction as last resort
        """
        if not content or not content.strip():
            raise ParseError("Empty response content")

        raw = self._extract_json(content)
        return self._validate_vote(raw)

    def _extract_json(self, content: str) -> dict[str, Any]:
        # Strategy 1: Direct parse
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Markdown code blocks
        m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Strategy 3: First { ... } block
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        raise ParseError(f"Cannot extract JSON from response: {content[:200]}...")

    def _validate_vote(self, raw: dict[str, Any]) -> ParsedVote:
        decision_raw = raw.get("decision", "ABSTAIN")
        decision = self._parse_decision(decision_raw)

        confidence = self._parse_float(raw.get("confidence", 0.5), 0.5, 0.0, 1.0)
        reason_summary = str(raw.get("reason_summary", "") or "")
        reasoning = str(raw.get("reasoning", "") or "")
        evidence = raw.get("evidence", {})
        if not isinstance(evidence, dict):
            evidence = {}

        return ParsedVote(
            decision=decision,
            confidence=confidence,
            reason_summary=reason_summary[:500],
            reasoning=reasoning[:5000],
            evidence=evidence,
        )

    def _parse_decision(self, value: Any) -> VoteDecision:
        if isinstance(value, VoteDecision):
            return value
        if isinstance(value, str):
            upper = value.strip().upper()
            if upper in ("APPROVE", "APPROVED", "ACCEPT", "YES", "TRUE", "PASS"):
                return VoteDecision.APPROVE
            if upper in ("REJECT", "REJECTED", "DENY", "NO", "FALSE", "FAIL"):
                return VoteDecision.REJECT
            if upper in ("ABSTAIN", "ABSTAINED", "NEUTRAL", "UNSURE", "UNCERTAIN"):
                return VoteDecision.ABSTAIN
        return VoteDecision.ABSTAIN

    def _parse_float(
        self, value: Any, default: float, min_val: float = 0.0, max_val: float = 1.0,
    ) -> float:
        try:
            v = float(value)
            return max(min_val, min(max_val, v))
        except (TypeError, ValueError):
            return default
