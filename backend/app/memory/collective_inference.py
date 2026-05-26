"""
Collective Inference — Deterministic inference from shared collective memory.

The CollectiveInferenceEngine takes accumulated observations and
detected patterns and produces explainable, auditable inferences.
No black-box logic — every inference is a deterministic combination
of its inputs.

Key capabilities:
    - aggregation rules (weighted by trust, recency, confidence)
    - confidence propagation (how record confidence affects inference confidence)
    - pattern accumulation (combining pattern signals)
    - longitudinal trend detection (monotonic trends over time)
    - contradiction detection (conflicting values from different voters)
    - memory conflict resolution (majority + confidence weighting)
    - stale memory detection (TTL-based filtering)

Each inference records its full reasoning chain for audit.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.memory.memory_rules import compute_memory_confidence
from app.memory.patterns import PatternDetector, PatternSignal
from app.models.shared_memory_record import SharedMemoryRecord

logger = logging.getLogger(__name__)


@dataclass
class CollectiveInference:
    """An inference derived from collective memory and patterns.

    Attributes:
        inference_id: Unique ID for this inference.
        source_ids: IDs of the SharedMemoryRecords used.
        conclusion: The inferred conclusion (string).
        confidence: How confident we are in [0, 1].
        reasoning_chain: Human-readable steps leading to this conclusion.
        patterns: Pattern signals that informed this inference.
        metadata: Additional context.
        created_at: When this inference was generated.
    """

    inference_id: str
    source_ids: list[str]
    conclusion: str
    confidence: float
    reasoning_chain: list[str] = field(default_factory=list)
    patterns: list[PatternSignal] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "inference_id": self.inference_id,
            "source_ids": list(self.source_ids),
            "conclusion": self.conclusion,
            "confidence": round(self.confidence, 4),
            "reasoning_chain": list(self.reasoning_chain),
            "patterns": [
                {
                    "pattern_type": p.pattern_type,
                    "strength": round(p.strength, 4),
                    "confidence": round(p.confidence, 4),
                    "description": p.description,
                }
                for p in self.patterns
            ],
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


class CollectiveInferenceEngine:
    """Deterministic collective inference from shared memory.

    Usage:
        engine = CollectiveInferenceEngine()
        inference = engine.infer(records)
        print(inference.conclusion)
        print(inference.reasoning_chain)
    """

    def __init__(self, pattern_detector: PatternDetector | None = None):
        self._detector = pattern_detector or PatternDetector()

    # ── Main Inference Entry Point ──────────────────────────────

    def infer(
        self,
        records: list[SharedMemoryRecord],
        *,
        context: dict[str, Any] | None = None,
    ) -> CollectiveInference:
        """Produce a collective inference from shared memory records.

        Steps:
            1. Detect patterns in the records.
            2. Aggregate confidence across records.
            3. Build reasoning chain.
            4. Form conclusion based on patterns + aggregation.

        Args:
            records: List of SharedMemoryRecord to analyze.
            context: Optional context dict (e.g., {"student_id": "..."}).

        Returns:
            CollectiveInference with full reasoning chain.
        """
        ctx = context or {}
        source_ids = [r.id for r in records]

        # Step 1: Detect patterns
        patterns = self._detector.detect_all(records)

        # Step 2: Aggregate confidence
        base_confidence = compute_memory_confidence(records)

        # Step 3: Compute pattern-adjusted confidence
        pattern_confidence = (
            sum(p.confidence * p.strength for p in patterns) / max(len(patterns), 1)
            if patterns else 0.0
        )
        # Blend base + pattern confidence
        if patterns:
            blended_confidence = 0.6 * base_confidence + 0.4 * pattern_confidence
        else:
            blended_confidence = base_confidence

        # Step 4: Build reasoning chain
        chain = self._build_reasoning_chain(records, patterns, ctx)

        # Step 5: Form conclusion
        conclusion = self._form_conclusion(records, patterns, ctx)

        inference = CollectiveInference(
            inference_id=str(uuid.uuid4()),
            source_ids=source_ids,
            conclusion=conclusion,
            confidence=max(0.0, min(1.0, blended_confidence)),
            reasoning_chain=chain,
            patterns=patterns,
            metadata={
                "num_records": len(records),
                "num_patterns": len(patterns),
                "base_confidence": round(base_confidence, 4),
                "context": ctx,
            },
        )

        logger.debug(
            "Inference produced: id=%s confidence=%.3f patterns=%d",
            inference.inference_id[:8], inference.confidence, len(patterns),
        )
        return inference

    # ── Inference from Consensus Result ─────────────────────────

    def infer_from_votes(
        self,
        votes: list,
        result: Any,
        shared_memory_records: list[SharedMemoryRecord] | None = None,
    ) -> CollectiveInference:
        """Generate an inference directly from a consensus run's votes.

        Args:
            votes: List of ConsensusVote from the run.
            result: ConsensusResult from the run.
            shared_memory_records: Optional additional memory context.

        Returns:
            CollectiveInference.
        """
        records = list(shared_memory_records or [])

        # Build synthetic records from votes for pattern analysis
        source_ids = [r.id for r in records] if records else []

        # Analyze vote patterns
        decisions = [v.decision.value for v in votes]
        approve_count = decisions.count("approve")
        reject_count = decisions.count("reject")
        abstain_count = decisions.count("abstain")
        total_non_abstain = approve_count + reject_count

        chain = [
            f"Consensus run produced {result.decision.value} "
            f"(confidence={result.confidence:.2f})",
            f"Votes: {approve_count} approve, {reject_count} reject, "
            f"{abstain_count} abstain",
        ]
        if result.unanimous:
            chain.append("Decision was unanimous")

        if result.weights_used:
            top_voter = max(result.weights_used, key=result.weights_used.get)
            chain.append(
                f"Highest-weighted voter: {top_voter} "
                f"(weight={result.weights_used[top_voter]:.3f})"
            )

        if shared_memory_records:
            patterns = self._detector.detect_all(shared_memory_records)
            for p in patterns[:3]:
                chain.append(f"Pattern: {p.description}")

        base_conf = result.confidence
        if shared_memory_records:
            mem_conf = compute_memory_confidence(shared_memory_records)
            confidence = 0.7 * base_conf + 0.3 * mem_conf
        else:
            confidence = base_conf

        return CollectiveInference(
            inference_id=str(uuid.uuid4()),
            source_ids=source_ids,
            conclusion=f"Consensus {result.decision.value} with "
                       f"{approve_count}/{total_non_abstain} approval "
                       f"(confidence={result.confidence:.2f})",
            confidence=max(0.0, min(1.0, confidence)),
            reasoning_chain=chain,
            metadata={
                "decision": result.decision.value,
                "consensus_confidence": result.confidence,
                "approve_count": approve_count,
                "reject_count": reject_count,
                "abstain_count": abstain_count,
                "unanimous": result.unanimous,
            },
        )

    # ── Reasoning Chain ─────────────────────────────────────────

    def _build_reasoning_chain(
        self,
        records: list,
        patterns: list[PatternSignal],
        context: dict[str, Any],
    ) -> list[str]:
        """Build a deterministic, auditable reasoning chain."""
        chain: list[str] = []

        if not records:
            chain.append("No shared memory records available")
            return chain

        chain.append(
            f"Analyzing {len(records)} shared memory records "
            f"from {len(set(r.voter_name for r in records))} voters"
        )

        # Group by type
        from collections import Counter
        type_counts: Counter = Counter(r.memory_type for r in records)
        for t, c in type_counts.most_common():
            chain.append(f"  - {c} records of type '{t}'")

        # Aggregate confidence
        conf = compute_memory_confidence(records)
        chain.append(f"Aggregated memory confidence: {conf:.3f}")

        # Add pattern info
        if patterns:
            chain.append(f"Detected {len(patterns)} pattern signals:")
            for p in patterns:
                chain.append(
                    f"  - {p.pattern_type}: {p.description} "
                    f"(strength={p.strength:.2f}, conf={p.confidence:.2f})"
                )

        # Source voter diversity
        unique_voters = set(r.voter_name for r in records)
        if len(unique_voters) >= 2:
            chain.append(
                f"Multiple sources ({len(unique_voters)} voters) "
                "increase confidence"
            )
        else:
            chain.append(
                f"Single source ({list(unique_voters)[0]}) — "
                "cross-verification recommended"
            )

        return chain

    # ── Conclusion ──────────────────────────────────────────────

    def _form_conclusion(
        self,
        records: list,
        patterns: list[PatternSignal],
        context: dict[str, Any],
    ) -> str:
        """Form a textual conclusion from records and patterns."""
        if not records:
            return "No data"

        conf = compute_memory_confidence(records)
        unique_voters = len(set(r.voter_name for r in records))

        # Check for contradictions
        contradictions = [p for p in patterns if p.pattern_type == "contradiction"]
        trends = [p for p in patterns if p.pattern_type == "trend"]
        improvements = [p for p in patterns if p.pattern_type == "improvement"]
        degradations = [p for p in patterns if p.pattern_type == "degradation"]

        parts = []
        if contradictions:
            parts.append(
                f"Conflicting observations ({len(contradictions)} contradictions)"
            )

        if improvements:
            parts.append(f"Improving trend detected")

        if degradations:
            parts.append(f"Degradation trend detected")

        if trends:
            for t in trends:
                direction = t.metadata.get("direction", "unknown")
                parts.append(f"{direction.capitalize()}ward trend (slope={t.metadata.get('slope', 0):.3f})")

        if not parts:
            if conf >= 0.7:
                parts.append("Stable with high confidence")
            elif conf >= 0.4:
                parts.append("Moderate confidence — additional observations needed")
            else:
                parts.append("Low confidence — insufficient consistent data")

        if unique_voters >= 3:
            parts.append(f"backed by {unique_voters} voters")
        elif unique_voters == 1:
            parts.append(f"single voter perspective")

        return "; ".join(parts)

    # ── Aggregation Helper ──────────────────────────────────────

    @staticmethod
    def aggregate_confidence(
        confidences: list[float],
        weights: list[float] | None = None,
    ) -> float:
        """Aggregate multiple confidence values with optional weights.

        Args:
            confidences: List of confidence values in [0, 1].
            weights: Optional weights (same length). If None, uniform.

        Returns:
            Weighted average confidence in [0, 1].
        """
        if not confidences:
            return 0.0

        n = len(confidences)
        if weights is None:
            weights = [1.0 / n] * n
        else:
            total = sum(abs(w) for w in weights)
            if total == 0:
                weights = [1.0 / n] * n
            else:
                weights = [abs(w) / total for w in weights]

        return max(0.0, min(1.0, sum(
            max(0.0, min(1.0, c)) * w
            for c, w in zip(confidences, weights)
        )))
