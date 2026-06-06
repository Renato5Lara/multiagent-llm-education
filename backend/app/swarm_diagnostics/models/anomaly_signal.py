"""
AnomalySignal — A detected anomaly within the swarm.

Each signal carries:
    - detector: which detector raised it
    - anomaly_type: classification (propagation_failure, conflict, loop, storm, ...)
    - severity: CRITICAL / WARNING / INFO
    - scope: what entity is affected (student:abc, module:xyz, global)
    - metric_value: the measured value that triggered detection
    - threshold: the threshold that was exceeded
    - evidence: supporting data (record IDs, timestamps, traces)
    - recommendation: suggested remediation
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AnomalyType(str, Enum):
    PROPAGATION_FAILURE = "propagation_failure"
    CONSENSUS_CONFLICT = "consensus_conflict"
    EMERGENT_BEHAVIOR = "emergent_behavior"
    DELEGATION_LOOP = "delegation_loop"
    RETRY_STORM = "retry_storm"
    DEADLOCK = "deadlock"
    STALE_MEMORY = "stale_memory"
    AGENT_DIVERGENCE = "agent_divergence"
    EVENT_STORM = "event_storm"
    SYNC_DELAY = "sync_delay"
    TRUST_DECAY = "trust_decay"
    MEMORY_FRAGMENTATION = "memory_fragmentation"
    PROPAGATION_STORM = "propagation_storm"
    RECURSIVE_AMPLIFICATION = "recursive_amplification"
    DAG_TRAVERSAL_PITFALL = "dag_traversal_pitfall"

    # ── Consensus timeout hazards ───────────────────────────────
    HUNG_CONSENSUS = "hung_consensus"
    CASCADING_DELAY = "cascading_delay"
    QUORUM_INSTABILITY = "quorum_instability"

    # ── Circuit breaker hazards ─────────────────────────────────
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"
    RETRY_STORM_AGENT = "retry_storm_agent"
    CASCADING_FAILURE = "cascading_failure"
    RECOVERY_INSTABILITY = "recovery_instability"

    # ── Agent health hazards ─────────────────────────────────────
    DEGRADED_AGENT = "degraded_agent"
    HALLUCINATION = "hallucination"
    SLOW_AGENT = "slow_agent"
    COGNITIVE_DRIFT = "cognitive_drift"
    DECISION_FLIPPING = "decision_flipping"


@dataclass
class AnomalySignal:
    anomaly_id: str
    detector_name: str
    anomaly_type: AnomalyType | str
    severity: Severity
    scope: str
    title: str
    description: str
    metric_value: float | None = None
    threshold: float | None = None
    evidence: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_id": self.anomaly_id,
            "detector_name": self.detector_name,
            "anomaly_type": self.anomaly_type.value if isinstance(self.anomaly_type, AnomalyType) else self.anomaly_type,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "scope": self.scope,
            "title": self.title,
            "description": self.description,
            "metric_value": self.metric_value,
            "threshold": self.threshold,
            "evidence": self.evidence,
            "recommendation": self.recommendation,
            "created_at": self.created_at.isoformat(),
            "correlation_id": self.correlation_id,
        }
