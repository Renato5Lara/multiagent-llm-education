"""
Swarm Orchestration Layer — lifecycle, orchestration, synchronization,
event propagation, and anomaly detection for the multi-agent educational swarm.
"""

from app.swarm.lifecycle import SwarmPhase, PhaseStatus, SwarmLifecycle
from app.swarm.orchestrator import SwarmOrchestrator
from app.swarm.events import SwarmEventType, SwarmEvent, SwarmEventBus
from app.swarm.synchronization import PhaseGate, SwarmFence, ContextLock
from app.swarm.detectors import (
    BottleneckDetector,
    RaceConditionDetector,
    ContextInconsistencyDetector,
    PropagationFailureDetector,
)
from app.swarm.metrics import SwarmActivationMetrics, swarm_metrics
from app.swarm.agent_factory import AgentFactory

__all__ = [
    "SwarmPhase", "PhaseStatus", "SwarmLifecycle",
    "SwarmOrchestrator",
    "SwarmEventType", "SwarmEvent", "SwarmEventBus",
    "PhaseGate", "SwarmFence", "ContextLock",
    "BottleneckDetector", "RaceConditionDetector",
    "ContextInconsistencyDetector", "PropagationFailureDetector",
    "SwarmActivationMetrics", "swarm_metrics",
    "AgentFactory",
]
