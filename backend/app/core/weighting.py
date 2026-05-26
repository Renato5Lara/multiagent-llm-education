"""
Adaptive Weighting — Computes dynamic voter weights for weighted consensus.

Combines trust scores and specialization affinities into
a single weight per voter. Weights are normalized so that
the sum equals the number of voters (preserving magnitude).

Weight formula:
    raw_weight = trust_score * specialization_affinity * base_weight
    normalized_weight = raw_weight * len(voters) / sum(raw_weights)

This is deterministic: same inputs → same outputs.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.trust import TrustSystem
from app.core.specialization import SpecializationTracker

logger = logging.getLogger(__name__)

DEFAULT_BASE_WEIGHT = 1.0


def compute_weights(
    voter_names: list[str],
    trust_system: TrustSystem | None = None,
    specialization_tracker: SpecializationTracker | None = None,
    context_key: str | None = None,
) -> dict[str, float]:
    """Compute adaptive weights for all voters.

    Args:
        voter_names: Names of all registered voters.
        trust_system: Optional TrustSystem for trust scores.
        specialization_tracker: Optional SpecializationTracker for affinities.
        context_key: Optional context key for specialization affinity.

    Returns:
        Dict mapping voter_name to normalized weight.
    """
    voter_names = list(voter_names)
    n = len(voter_names)
    if n == 0:
        return {}

    raw: dict[str, float] = {}
    for name in voter_names:
        trust = trust_system.get_trust(name) if trust_system else 1.0
        affinity = (
            specialization_tracker.get_affinity(name, context_key)
            if specialization_tracker and context_key
            else 1.0
        )
        raw[name] = trust * affinity * DEFAULT_BASE_WEIGHT

    total = sum(raw.values())
    if total == 0:
        return {name: 1.0 for name in voter_names}

    return {name: (raw[name] / total) * n for name in voter_names}


def compute_weights_detailed(
    voter_names: list[str],
    trust_system: TrustSystem | None = None,
    specialization_tracker: SpecializationTracker | None = None,
    context_key: str | None = None,
) -> dict[str, dict[str, float]]:
    """Compute weights with a breakdown per component (trust, affinity, final).

    Returns:
        Dict mapping voter_name to {trust, affinity, raw_weight, final_weight}.
    """
    n = len(voter_names)
    if n == 0:
        return {}

    details: dict[str, dict[str, float]] = {}
    raw: dict[str, float] = {}

    for name in voter_names:
        trust = trust_system.get_trust(name) if trust_system else 1.0
        affinity = (
            specialization_tracker.get_affinity(name, context_key)
            if specialization_tracker and context_key
            else 1.0
        )
        raw_weight = trust * affinity * DEFAULT_BASE_WEIGHT
        raw[name] = raw_weight
        details[name] = {
            "trust": round(trust, 4),
            "affinity": round(affinity, 4),
            "raw_weight": round(raw_weight, 4),
        }

    total = sum(raw.values())
    if total > 0:
        for name in voter_names:
            final_weight = (raw[name] / total) * n
            details[name]["final_weight"] = round(final_weight, 4)
    else:
        for name in voter_names:
            details[name]["final_weight"] = 1.0

    return details
