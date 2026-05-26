"""
Memory Rules — Deterministic rules for shared memory operations.

All rules are pure functions with no side effects, designed to
be auditable, testable, and explainable.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── TTL Configuration ─────────────────────────────────────────────

DEFAULT_TTL_SECONDS = 86400 * 7  # 7 days

MEMORY_TYPE_TTL: dict[str, int] = {
    "observation": 86400 * 30,    # 30 days (raw observations last longest)
    "inference": 86400 * 14,       # 14 days (derived conclusions)
    "pattern": 86400 * 7,          # 7 days (patterns refresh frequently)
    "signal": 86400 * 3,           # 3 days (signals are ephemeral)
}


# ── Confidence ────────────────────────────────────────────────────


def compute_memory_confidence(
    records: list,
    recency_weight: float = 0.3,
) -> float:
    """Aggregate confidence from multiple records.

    Uses a weighted average where newer records get slightly more
    weight (recency_weight) and older records get (1 - recency_weight).

    Args:
        records: List of objects with .confidence and .created_at.
        recency_weight: Fraction of weight given to recency ordering.

    Returns:
        float: Aggregated confidence in [0, 1].
    """
    if not records:
        return 0.0

    n = len(records)
    if n == 1:
        return max(0.0, min(1.0, records[0].confidence))

    # Sort by created_at ascending (oldest first)
    sorted_recs = sorted(records, key=lambda r: r.created_at)
    weights = []
    for i in range(n):
        # Newer records get higher weight
        position_weight = (i + 1) / n
        w = recency_weight * position_weight + (1 - recency_weight) * (1.0 / n)
        weights.append(w)

    total_weight = sum(weights)
    normalized_weights = [w / total_weight for w in weights]

    conf = sum(
        max(0.0, min(1.0, r.confidence)) * w
        for r, w in zip(sorted_recs, normalized_weights)
    )
    return max(0.0, min(1.0, conf))


# ── Conflict Resolution ──────────────────────────────────────────


def resolve_conflict(records: list) -> dict[str, Any]:
    """Resolve conflicting observations with the same key.

    Strategy: majority vote on value, with confidence-weighted
    tie-breaking. Returns the winning value dict.

    Args:
        records: List of SharedMemoryRecord with same key.

    Returns:
        dict: The resolved value.
    """
    if not records:
        return {}
    if len(records) == 1:
        return records[0].value or {}

    # Group by serialized value
    from collections import defaultdict
    value_groups: dict[str, list] = defaultdict(list)
    for r in records:
        key = _serialize_value(r.value)
        value_groups[key].append(r)

    # Score each group: count * average confidence
    best_score = -1.0
    best_value = {}
    for val_key, group in value_groups.items():
        avg_conf = sum(r.confidence for r in group) / len(group)
        # Score = votes * conf (majority + confidence)
        score = len(group) * avg_conf
        if score > best_score:
            best_score = score
            best_value = group[0].value or {}

    logger.debug(
        "Conflict resolution: %d groups, winner score=%.3f",
        len(value_groups), best_score,
    )
    return best_value


def _serialize_value(value: Any) -> str:
    """Deterministic serialization for value comparison."""
    import json
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, default=str)
    if isinstance(value, list):
        return json.dumps(value, default=str)
    return str(value)


# ── Staleness ─────────────────────────────────────────────────────


def is_stale(
    record: Any,
    now: datetime | None = None,
) -> bool:
    """Check if a memory record has exceeded its TTL.

    Handles both offset-aware and offset-naive datetimes by
    removing timezone info from `now` if the record's created_at
    is naive (common with SQLite).

    Args:
        record: Object with .ttl_seconds and .created_at.
        now: Current time (defaults to utcnow).

    Returns:
        True if the record is stale.
    """
    if record.ttl_seconds is None:
        return False
    if now is None:
        now = datetime.now(timezone.utc)
    created = record.created_at
    # Handle timezone mismatch (SQLite stores naive datetimes)
    if created.tzinfo is None and now.tzinfo is not None:
        now = now.replace(tzinfo=None)
    elif created.tzinfo is not None and now.tzinfo is None:
        created = created.replace(tzinfo=None)
    elapsed = (now - created).total_seconds()
    return elapsed > record.ttl_seconds


# ── TTL Computation ───────────────────────────────────────────────


def compute_ttl(
    memory_type: str,
    confidence: float | None = None,
) -> int:
    """Compute a deterministic TTL based on memory type and confidence.

    Higher confidence gets longer TTL. Falls back to MEMORY_TYPE_TTL.

    Args:
        memory_type: 'observation', 'inference', 'pattern', 'signal'.
        confidence: Optional confidence to modulate TTL.

    Returns:
        int: TTL in seconds.
    """
    base_ttl = MEMORY_TYPE_TTL.get(memory_type, DEFAULT_TTL_SECONDS)
    if confidence is None:
        return base_ttl
    # Scale 0.5x-1.5x based on confidence
    factor = 0.5 + confidence
    return max(60, int(base_ttl * factor))


# ── Merge ─────────────────────────────────────────────────────────


def merge_observations(
    existing: dict[str, Any],
    new: dict[str, Any],
) -> dict[str, Any]:
    """Merge a new observation into an existing one.

    Deterministic merge: new keys overwrite old keys; for shared
    keys, the value with higher confidence wins.

    Args:
        existing: Current value dict.
        new: New observation value dict.

    Returns:
        dict: Merged value.
    """
    result = dict(existing)
    for key, new_val in new.items():
        if key not in result:
            result[key] = new_val
        elif isinstance(new_val, dict) and isinstance(result[key], dict):
            result[key] = merge_observations(result[key], new_val)
        else:
            # Simple overwrite — the most recent observation wins
            result[key] = new_val
    return result


# ── Source Reliability ────────────────────────────────────────────


def compute_source_reliability(
    records: list,
    trust_scores: dict[str, float] | None = None,
) -> dict[str, float]:
    """Compute reliability per source voter.

    Args:
        records: List of records with .voter_name.
        trust_scores: Optional dict of voter_name -> trust_score.

    Returns:
        dict: voter_name -> reliability in [0, 1].
    """
    from collections import Counter
    counts: Counter = Counter(r.voter_name for r in records)
    total = sum(counts.values())
    if total == 0:
        return {}

    reliability: dict[str, float] = {}
    for voter, count in counts.items():
        base = count / total  # participation ratio
        if trust_scores and voter in trust_scores:
            reliability[voter] = max(0.0, min(1.0, base * trust_scores[voter]))
        else:
            reliability[voter] = base
    return reliability
