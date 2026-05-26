"""
Shared Collective Memory package.

Provides deterministic memory, pattern detection, and collective
inference for the consensus swarm — without LLMs, embeddings, or
external dependencies.
"""

from app.memory.memory_rules import (
    compute_memory_confidence,
    resolve_conflict,
    is_stale,
    compute_ttl,
    merge_observations,
    compute_source_reliability,
    DEFAULT_TTL_SECONDS,
    MEMORY_TYPE_TTL,
)
from app.memory.shared_memory import SharedMemoryStore
from app.memory.patterns import PatternSignal, PatternDetector
from app.memory.collective_inference import (
    CollectiveInference,
    CollectiveInferenceEngine,
)

__all__ = [
    "SharedMemoryStore",
    "PatternSignal",
    "PatternDetector",
    "CollectiveInference",
    "CollectiveInferenceEngine",
    "compute_memory_confidence",
    "resolve_conflict",
    "is_stale",
    "compute_ttl",
    "merge_observations",
    "compute_source_reliability",
    "DEFAULT_TTL_SECONDS",
    "MEMORY_TYPE_TTL",
]
