"""
Schemas for the Agent Decision Trace system.

Every agent in the swarm produces a structured AgentDecisionTrace after
each invocation. Traces are chained by correlation_id (same per swarm run)
and causation_id (previous agent's trace_id), enabling full reasoning
auditability from ResearchAgent → PedagogicalAgent → AdaptiveLearningAgent
→ ConsensusEngine.

Used for:
  - Thesis defensibility (explicit reasoning record)
  - GET /api/trace/session/{session_id} — chain visualization
  - React "thinking window" component
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Source classification ─────────────────────────────────────────

class EvidenceSource(str, Enum):
    SHARED_MEMORY = "shared_memory"
    DATABASE = "database"
    STATE_DICT = "state_dict"
    LLM_RESPONSE = "llm_response"
    COMPUTATION = "computation"


class StepType(str, Enum):
    DATA_LOAD = "data_load"
    MEMORY_QUERY = "memory_query"
    LLM_INFERENCE = "llm_inference"
    RULE_EVALUATION = "rule_evaluation"
    COMPUTATION = "computation"
    DECISION = "decision"
    MEMORY_PUBLISH = "memory_publish"


# ── Core trace components ─────────────────────────────────────────

class AgentEvidence(BaseModel):
    """A single piece of evidence the agent read before deciding.

    Each evidence item corresponds to one SharedMemory record, one DB
    query result, or one value from the incoming state dict.
    """
    source: EvidenceSource
    key: str = Field(..., description="SharedMemory key or state dict field name")
    value_summary: Any = Field(
        ...,
        description="Truncated value (max 512 chars for strings, first 3 items for lists)",
    )
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    memory_type: str | None = Field(
        default=None,
        description="SharedMemory memory_type: observation | inference | pattern | signal",
    )
    record_id: str | None = Field(
        default=None,
        description="SharedMemoryRecord.id if source is shared_memory",
    )
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )


class AgentReasoningStep(BaseModel):
    """One intermediate reasoning step inside analyze().

    Agents register steps to show: I loaded X → computed Y → applied rule Z.
    This makes the reasoning chain explicit and auditable.
    """
    step_number: int = Field(..., ge=1)
    step_type: StepType
    description: str = Field(..., description="Human-readable description of this step")
    inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Key inputs consumed by this step",
    )
    outputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Key outputs produced by this step",
    )
    elapsed_ms: float | None = None
    notes: str | None = None


class DecisionDimension(BaseModel):
    """One axis of the agent's multi-dimensional decision.

    Aligns with AdaptiveLearningAgent._build_adaptation_rationale() pattern:
    {dimension: {result, signal, rule}} — extended with confidence + evidence.

    Examples:
      - dimension="difficulty_level", result="intermediate",
        signal="avg_bloom=2.8", rule="bloom>=2.5 AND <4 → intermediate"
      - dimension="bloom_range", result="[2, 4]",
        signal="student_score=0.62", rule="score<0.7 → don't advance bloom"
    """
    dimension: str = Field(..., description="Name of the decision axis")
    result: str = Field(..., description="Value decided for this dimension")
    signal: str = Field(..., description="Key signal observed that drove this decision")
    rule: str = Field(..., description="Rule or threshold applied")
    confidence: float = Field(..., ge=0.0, le=1.0)
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data for this dimension",
    )
    alternative_considered: str | None = Field(
        default=None,
        description="Alternative value that was evaluated and rejected",
    )
    alternative_reason: str | None = Field(
        default=None,
        description="Why the alternative was rejected",
    )


# ── Top-level trace ───────────────────────────────────────────────

class AgentDecisionTrace(BaseModel):
    """Complete decision trace for one agent invocation.

    Stored in result["_decision_trace"] by BaseAgent.run() and
    persisted to agent_decision_traces table by TraceStore.
    """

    # Identity
    trace_id: str = Field(..., description="UUID for this specific trace")
    agent_id: str = Field(..., description="Runtime agent instance ID (from BaseAgent)")
    agent_name: str
    agent_type: str

    # Invocation context
    session_id: str | None = Field(
        default=None,
        description="LearningSession.id if this trace is part of a student session",
    )
    context_key: str = Field(..., description="Swarm context key (shared across agents in one run)")
    student_id: str
    course_id: str

    # Causal chain — links agents in order
    correlation_id: str | None = Field(
        default=None,
        description="Shared across ALL agents in one swarm run",
    )
    causation_id: str | None = Field(
        default=None,
        description="trace_id of the agent that directly caused this invocation",
    )
    sequence: int = Field(
        default=0,
        description="Position in the causal chain (0=first agent)",
    )

    # Inputs received
    state_inputs: dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized snapshot of state dict keys (no large blobs)",
    )
    memory_records_queried: int = Field(
        default=0,
        description="Total SharedMemory records read during analyze()",
    )

    # Reasoning components
    evidence: list[AgentEvidence] = Field(
        default_factory=list,
        description="Evidence items read from SharedMemory/DB/state",
    )
    reasoning_steps: list[AgentReasoningStep] = Field(
        default_factory=list,
        description="Ordered intermediate reasoning steps",
    )
    dimensions: list[DecisionDimension] = Field(
        default_factory=list,
        description="Per-axis decisions with signal + rule + confidence",
    )

    # Final decision
    decision_summary: str = Field(
        default="",
        description="One-line human-readable summary of what was decided",
    )
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    output_keys: list[str] = Field(
        default_factory=list,
        description="Top-level keys produced in the output dict (no values)",
    )

    # Performance
    elapsed_ms: float = Field(default=0.0)

    # Outcome
    success: bool = True
    error: str | None = None

    # Timestamps
    started_at: str
    completed_at: str

    def to_ui_node(self) -> "TraceNodeUI":
        return TraceNodeUI(
            id=self.trace_id,
            agent_name=self.agent_name,
            agent_type=self.agent_type,
            sequence=self.sequence,
            decision_summary=self.decision_summary,
            confidence=self.confidence,
            elapsed_ms=self.elapsed_ms,
            success=self.success,
            dimensions_count=len(self.dimensions),
            evidence_count=len(self.evidence),
            steps_count=len(self.reasoning_steps),
        )


# ── Consensus trace ───────────────────────────────────────────────

class ConsensusVoteTrace(BaseModel):
    """Single voter's contribution to consensus — for the chain view."""
    voter_name: str
    decision: str
    confidence: float
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    elapsed_ms: float | None = None


class ConsensusTrace(BaseModel):
    """ConsensusEngine run captured as a trace node."""
    trace_id: str
    correlation_id: str | None = None
    causation_id: str | None = None
    sequence: int

    module_id: str
    student_id: str
    decision: str
    confidence: float
    unanimous: bool
    approve_ratio: float
    reject_ratio: float
    votes: list[ConsensusVoteTrace] = Field(default_factory=list)
    weights_used: dict[str, float] = Field(default_factory=dict)

    elapsed_ms: float = 0.0
    computed_at: str


# ── Swarm run container ───────────────────────────────────────────

class SwarmRunTrace(BaseModel):
    """All agent traces from a single swarm orchestration run.

    One SwarmRunTrace = one pedagogical session or one swarm activation.
    """
    correlation_id: str
    session_id: str | None = None
    context_key: str
    student_id: str
    course_id: str

    agent_traces: list[AgentDecisionTrace] = Field(default_factory=list)
    consensus_trace: ConsensusTrace | None = None

    total_elapsed_ms: float = 0.0
    agent_count: int = 0
    started_at: str
    completed_at: str | None = None


# ── API response ──────────────────────────────────────────────────

class TraceNodeUI(BaseModel):
    """Lightweight node for React visualization."""
    id: str
    agent_name: str
    agent_type: str
    sequence: int
    decision_summary: str
    confidence: float
    elapsed_ms: float
    success: bool
    dimensions_count: int
    evidence_count: int
    steps_count: int


class TraceEdgeUI(BaseModel):
    """Directed edge between two trace nodes in the React graph."""
    from_trace_id: str
    to_trace_id: str
    from_agent: str
    to_agent: str
    label: str = Field(..., description="What was passed: 'findings', 'adaptation plan', etc.")
    memory_keys: list[str] = Field(
        default_factory=list,
        description="SharedMemory keys that carried the data across",
    )


class TraceChainResponse(BaseModel):
    """Complete response for GET /api/trace/session/{session_id}.

    Contains the full chain plus UI-ready nodes and edges for React.
    """
    session_id: str | None
    correlation_id: str | None
    context_key: str

    # Full traces (for detail panels)
    chain: list[AgentDecisionTrace] = Field(
        default_factory=list,
        description="Ordered agent traces, sorted by sequence",
    )
    consensus: ConsensusTrace | None = None

    # React visualization
    nodes: list[TraceNodeUI] = Field(default_factory=list)
    edges: list[TraceEdgeUI] = Field(default_factory=list)

    # Summary
    total_agents: int = 0
    total_elapsed_ms: float = 0.0
    pipeline_decision: str | None = None
    retrieved_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
