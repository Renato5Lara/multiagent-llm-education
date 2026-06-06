"""Emergent behavior metrics for swarm deliberation.

Computes interpretable metrics from DeliberationResult:
    - Cognitive diversity: how varied are voter reasoning patterns
    - Deliberation impact: how much deliberation changed the group outcome
    - Polarization index: how spread out (bimodal) confidence becomes
    - Cross-pollination: do voters adopt reasoning from other agents
    - Calibration delta: confidence shift due to deliberation
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import VoteDecision
from app.llm.deliberation import DeliberationResult, RoundResult


@dataclass
class SwarmMetrics:
    """Aggregate emergent behavior metrics for a deliberation session.

    All metrics are normalized to [0, 1] unless noted.
    """

    cognitive_diversity: float = 0.0
    deliberation_impact: float = 0.0
    polarization_index: float = 0.0
    cross_pollination_rate: float = 0.0
    calibration_delta: float = 0.0  # [-1, 1], positive = more confident after deliberation

    def to_dict(self) -> dict[str, Any]:
        return {
            "cognitive_diversity": round(self.cognitive_diversity, 4),
            "deliberation_impact": round(self.deliberation_impact, 4),
            "polarization_index": round(self.polarization_index, 4),
            "cross_pollination_rate": round(self.cross_pollination_rate, 4),
            "calibration_delta": round(self.calibration_delta, 4),
        }

    @classmethod
    def compute(cls, result: DeliberationResult) -> SwarmMetrics:
        """Compute all metrics from a completed deliberation result.

        Args:
            result: Completed DeliberationResult with at least 1 round.

        Returns:
            SwarmMetrics with all fields populated.
        """
        metrics = cls()

        if not result.rounds:
            return metrics

        metrics.cognitive_diversity = _compute_cognitive_diversity(result)
        metrics.deliberation_impact = _compute_deliberation_impact(result)
        metrics.polarization_index = _compute_polarization_index(result)
        metrics.cross_pollination_rate = _compute_cross_pollination_rate(result)
        metrics.calibration_delta = _compute_calibration_delta(result)

        return metrics


# ── N-gram utilities (stdlib only, no NLP dependency) ─────────

def _word_ngrams(text: str, n: int = 2) -> set[str]:
    """Tokenize text into word-level n-grams."""
    words = text.lower().split()
    if len(words) < n:
        return set(words)
    return {' '.join(words[i:i + n]) for i in range(len(words) - n + 1)}


def _jaccard_similarity(a: set[str], b: set[str]) -> float:
    """Compute Jaccard similarity between two sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _jaccard_distance(a: set[str], b: set[str]) -> float:
    """Compute Jaccard distance (1 - similarity) between two sets."""
    return 1.0 - _jaccard_similarity(a, b)


# ── Voter reasoning extraction ──────────────────────────────

def _get_reasoning_text(vote) -> str:
    """Extract reasoning text from a ConsensusVote, looking in multiple places."""
    if vote.evidence:
        reasoning = vote.evidence.get("reasoning", "")
        if reasoning:
            return str(reasoning)
    if vote.evidence:
        reasoning = vote.evidence.get("reason_summary", "")
        if reasoning:
            return str(reasoning)
    return vote.reason or ""


def _get_reasoning_text_safe(vote) -> str:
    """Like _get_reasoning_text but always returns a string."""
    text = _get_reasoning_text(vote)
    return text if isinstance(text, str) else str(text) if text else ""


# ── Cognitive Diversity ──────────────────────────────────────

def _compute_cognitive_diversity(result: DeliberationResult) -> float:
    """Average pairwise Jaccard distance of reasoning across rounds.

    High diversity (close to 1) means very different reasoning patterns.
    Low diversity (close to 0) means voters use similar reasoning (groupthink).
    """
    if not result.rounds:
        return 0.0

    round_scores: list[float] = []
    for round_result in result.rounds:
        votes = round_result.votes
        if len(votes) < 2:
            continue

        ngrams_list = []
        for v in votes:
            text = _get_reasoning_text_safe(v)
            ngrams_list.append(_word_ngrams(text, n=2))

        pairwise_distances: list[float] = []
        for i in range(len(ngrams_list)):
            for j in range(i + 1, len(ngrams_list)):
                pairwise_distances.append(_jaccard_distance(ngrams_list[i], ngrams_list[j]))

        if pairwise_distances:
            round_scores.append(sum(pairwise_distances) / len(pairwise_distances))

    if not round_scores:
        return 0.0

    return sum(round_scores) / len(round_scores)


# ── Deliberation Impact ─────────────────────────────────────

def _compute_deliberation_impact(result: DeliberationResult) -> float:
    """How much deliberation changed the group's output.

    Combines:
      - Vote shift rate (fraction of LLM voters that changed decision)
      - Confidence shift rate (normalized absolute confidence change)
    """
    if len(result.rounds) < 2:
        return 0.0

    first_round = result.rounds[0]
    last_round = result.rounds[-1]

    first_votes = {v.voter_name: v for v in first_round.votes}
    last_votes = {v.voter_name: v for v in last_round.votes}

    llm_voter_names = [name for name in first_votes if name in last_votes]
    if not llm_voter_names:
        return 0.0

    # Vote shift rate (already computed in DeliberationResult)
    vote_shift = result.vote_shift_rate

    # Confidence shift rate
    conf_changes: list[float] = []
    for name in llm_voter_names:
        delta = abs(last_votes[name].confidence - first_votes[name].confidence)
        conf_changes.append(delta)

    avg_conf_shift = statistics.mean(conf_changes) if conf_changes else 0.0
    conf_shift_rate = avg_conf_shift  # already in [0, 1] since confidence is in [0, 1]

    return (vote_shift + conf_shift_rate) / 2.0


# ── Polarization Index ──────────────────────────────────────

def _compute_polarization_index(result: DeliberationResult) -> float:
    """Measure confidence spread in the final round.

    Uses coefficient of variation (std/mean) of confidence scores.
    Higher values indicate more polarized (spread out) confidences.
    Normalized to [0, 1].
    """
    if not result.rounds:
        return 0.0

    last = result.rounds[-1]
    confidences = [v.confidence for v in last.votes]
    if len(confidences) < 2:
        return 0.0

    mean_conf = statistics.mean(confidences)
    if mean_conf == 0.0:
        return 1.0

    std_conf = statistics.stdev(confidences)
    # Normalize: max CV for [0,1] bounded data with given mean
    # CV = std/mean, max possible std at a given mean on [0,1] is sqrt(mean*(1-mean))
    max_std = math.sqrt(mean_conf * (1.0 - mean_conf))
    if max_std == 0.0:
        return 0.0

    polarization = (std_conf / mean_conf) / (max_std / mean_conf)
    return min(1.0, polarization)


# ── Cross-pollination Rate ──────────────────────────────────

def _compute_cross_pollination_rate(result: DeliberationResult) -> float:
    """Fraction of LLM voters whose reasoning became more similar to other agents' reasoning.

    For each LLM voter active in rounds 1 and N:
      - Compute self_sim = Jaccard(reasoning_round1, reasoning_roundN)
      - Compute other_sim_max = max similarity with any other voter's round 1 reasoning
      - If other_sim_max > self_sim * 1.2, marked as cross-pollinated
    """
    if len(result.rounds) < 2:
        return 0.0

    first = result.rounds[0]
    last = result.rounds[-1]

    first_map = {v.voter_name: v for v in first.votes}
    last_map = {v.voter_name: v for v in last.votes}

    # Only consider voters present in both rounds
    shared_names = [n for n in first_map if n in last_map]
    if len(shared_names) < 2:
        return 0.0

    # Pre-compute round 1 n-grams for all voters
    r1_ngrams = {}
    for name in shared_names:
        text = _get_reasoning_text_safe(first_map[name])
        r1_ngrams[name] = _word_ngrams(text, n=2)

    cross_count = 0
    total = 0

    for name in shared_names:
        last_text = _get_reasoning_text_safe(last_map[name])
        last_ngrams = _word_ngrams(last_text, n=2)

        if not r1_ngrams[name] or not last_ngrams:
            continue

        # Self-similarity: how similar is final reasoning to own initial reasoning
        self_sim = _jaccard_similarity(r1_ngrams[name], last_ngrams)

        # Max similarity to any other voter's round 1 reasoning
        other_sims = [
            _jaccard_similarity(r1_ngrams[other], last_ngrams)
            for other in shared_names
            if other != name
        ]

        if not other_sims:
            continue

        max_other_sim = max(other_sims)
        total += 1

        if max_other_sim > self_sim * 1.2:
            cross_count += 1

    if total == 0:
        return 0.0

    return cross_count / total


# ── Calibration Delta ───────────────────────────────────────

def _compute_calibration_delta(result: DeliberationResult) -> float:
    """Change in average confidence between round 1 and the final round.

    Positive values indicate the group became more confident after deliberation.
    Negative values indicate the group became more cautious.
    Range: [-1, 1]
    """
    if len(result.rounds) < 2:
        return 0.0

    first = result.rounds[0]
    last = result.rounds[-1]

    first_map = {v.voter_name: v.confidence for v in first.votes}
    last_map = {v.voter_name: v.confidence for v in last.votes}

    shared_names = [n for n in first_map if n in last_map]
    if not shared_names:
        return 0.0

    first_avg = statistics.mean(first_map[n] for n in shared_names)
    last_avg = statistics.mean(last_map[n] for n in shared_names)

    return last_avg - first_avg
