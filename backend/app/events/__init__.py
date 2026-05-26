"""
Event management for the multi-agent swarm.

Components:
  - OutboxService:         Event Outbox pattern (existing)
  - IdempotencyService:    Enterprise idempotency lifecycle management
  - DedupEventBus:         Exactly-once event dispatch
  - IdempotentConsumer:    Exactly-once event processing
  - ReplayGuard:           Replay attack/redelivery detection
  - IdempotentSharedMemory: Memory dedup wrapper
  - IdempotentConsensusGuard: Phase-level consensus idempotency
  - IdempotentUnitOfWork:  Outbox dedup and double-commit guard
  - DistributedDedupEngine: Cross-process dedup with 3-layer protection
  - RetryHandler:          Retry-safe processing with exponential backoff
  - EventReplayService:    Safe outbox event replay with idempotency
  - RiskDetectors:         Consistency, race, replay, duplicate risk analysis
  - Middleware:            FastAPI middleware for automatic key propagation
  - PropagationTTL:        Depth, time, decay, anti-feedback-loop protection
"""

from app.events.outbox import OutboxService, outbox_service
from app.events.idempotency import (
    IdempotencyService,
    IdempotencyKeyGenerator,
    IdempotencyConflict,
    IdempotencyError,
    idempotency_service,
)
from app.events.dedup import (
    DedupEventBus,
    IdempotentConsumer,
    ReplayGuard,
    ReplayDetected,
)
from app.events.integration import (
    IdempotentSharedMemory,
    IdempotentConsensusGuard,
    IdempotentUnitOfWork,
    get_idempotency_key_from_propagation,
)
from app.events.distributed import (
    DistributedDedupEngine,
    distributed_dedup,
    extract_dedup_keys_from_propagation,
)
from app.events.retry import (
    RetryHandler,
    RetryExhaustedError,
    CircuitBreaker,
    CircuitBreakerOpenError,
    retry_stats,
)
from app.events.replay import (
    EventReplayService,
    event_replay_service,
)
from app.events.risk_detectors import (
    RiskReport,
    IdempotencyRiskAnalysis,
    risk_analysis,
)
from app.events.middleware import (
    make_idempotency_middleware,
)
from app.events.propagation_ttl import (
    PropagationTTL,
    PropagationTTLManager,
    PropagationLifecycle,
    PropagationState,
    PropagationStopReason,
    PropagationRateTracker,
    PropagationError,
    PropagationStoppedError,
    FeedbackLoopError,
    DAGCycleError,
    PropagationStormError,
    propagation_lifecycle,
    ttl_event_guard,
    ttl_consensus_hook,
)

__all__ = [
    "OutboxService",
    "outbox_service",
    "IdempotencyService",
    "IdempotencyKeyGenerator",
    "IdempotencyConflict",
    "IdempotencyError",
    "idempotency_service",
    "DedupEventBus",
    "IdempotentConsumer",
    "ReplayGuard",
    "ReplayDetected",
    "IdempotentSharedMemory",
    "IdempotentConsensusGuard",
    "IdempotentUnitOfWork",
    "get_idempotency_key_from_propagation",
    "DistributedDedupEngine",
    "distributed_dedup",
    "extract_dedup_keys_from_propagation",
    "RetryHandler",
    "RetryExhaustedError",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "retry_stats",
    "EventReplayService",
    "event_replay_service",
    "RiskReport",
    "IdempotencyRiskAnalysis",
    "risk_analysis",
    "make_idempotency_middleware",
    "PropagationTTL",
    "PropagationTTLManager",
    "PropagationLifecycle",
    "PropagationState",
    "PropagationStopReason",
    "PropagationRateTracker",
    "PropagationError",
    "PropagationStoppedError",
    "FeedbackLoopError",
    "DAGCycleError",
    "PropagationStormError",
    "propagation_lifecycle",
    "ttl_event_guard",
    "ttl_consensus_hook",
]
