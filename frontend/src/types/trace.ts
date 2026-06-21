// ── Source classification ─────────────────────────────────────────

export type EvidenceSource =
  | "shared_memory"
  | "database"
  | "state_dict"
  | "llm_response"
  | "computation";

export type StepType =
  | "data_load"
  | "memory_query"
  | "llm_inference"
  | "rule_evaluation"
  | "computation"
  | "decision"
  | "memory_publish";

// ── Core trace components ─────────────────────────────────────────

export interface AgentEvidence {
  source: EvidenceSource;
  key: string;
  value_summary: unknown;
  confidence: number;
  memory_type: string | null;
  record_id: string | null;
  retrieved_at: string;
}

export interface AgentReasoningStep {
  step_number: number;
  step_type: StepType;
  description: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  elapsed_ms: number | null;
  notes: string | null;
}

export interface DecisionDimension {
  dimension: string;
  result: string;
  signal: string;
  rule: string;
  confidence: number;
  evidence: Record<string, unknown>;
  alternative_considered: string | null;
  alternative_reason: string | null;
}

// ── Top-level trace ───────────────────────────────────────────────

export interface AgentDecisionTrace {
  // Identity
  trace_id: string;
  agent_id: string;
  agent_name: string;
  agent_type: string;

  // Invocation context
  session_id: string | null;
  context_key: string;
  student_id: string;
  course_id: string;

  // Causal chain
  correlation_id: string | null;
  causation_id: string | null;
  sequence: number;

  // Inputs received
  state_inputs: Record<string, unknown>;
  memory_records_queried: number;

  // Reasoning components
  evidence: AgentEvidence[];
  reasoning_steps: AgentReasoningStep[];
  dimensions: DecisionDimension[];

  // Final decision
  decision_summary: string;
  confidence: number;
  output_keys: string[];

  // Performance
  elapsed_ms: number;

  // Outcome
  success: boolean;
  error: string | null;

  // Timestamps — nullable because to_schema_dict() guards against None/falsy
  started_at: string | null;
  completed_at: string | null;
}

// ── Consensus trace ───────────────────────────────────────────────

export interface ConsensusVoteTrace {
  voter_name: string;
  decision: string;
  confidence: number;
  reason: string;
  evidence: Record<string, unknown>;
  elapsed_ms: number | null;
}

export interface ConsensusTrace {
  trace_id: string;
  correlation_id: string | null;
  causation_id: string | null;
  sequence: number;
  module_id: string;
  student_id: string;
  decision: string;
  confidence: number;
  unanimous: boolean;
  approve_ratio: number;
  reject_ratio: number;
  votes: ConsensusVoteTrace[];
  weights_used: Record<string, number>;
  elapsed_ms: number;
  computed_at: string;
}

// ── React visualization ───────────────────────────────────────────

export interface TraceNodeUI {
  id: string;
  agent_name: string;
  agent_type: string;
  sequence: number;
  decision_summary: string;
  confidence: number;
  elapsed_ms: number;
  success: boolean;
  dimensions_count: number;
  evidence_count: number;
  steps_count: number;
}

export interface TraceEdgeUI {
  from_trace_id: string;
  to_trace_id: string;
  from_agent: string;
  to_agent: string;
  label: string;
  memory_keys: string[];
}

// ── API response ──────────────────────────────────────────────────

export interface TraceChainResponse {
  session_id: string | null;
  correlation_id: string | null;
  context_key: string;
  chain: AgentDecisionTrace[];
  consensus: ConsensusTrace | null;
  nodes: TraceNodeUI[];
  edges: TraceEdgeUI[];
  total_agents: number;
  total_elapsed_ms: number;
  pipeline_decision: string | null;
  retrieved_at: string | null;
}

// ── Debate inter-agente ───────────────────────────────────────────

export type DebateState = "no_debate" | "agreement" | "conflict" | "resolved";

export type DebateRecommendation =
  | "retroceder"
  | "simplificar"
  | "cambiar_modalidad"
  | "reforzar"
  | "continuar";

export interface DebateParticipant {
  agent_name: string;
  agent_display_name: string;
  confidence: number;
  proposed_difficulty: string;
  rationale: string;
  trace_id: string;
  is_winner: boolean;
}

export interface DebateResolution {
  has_debate_context: boolean;
  has_conflict: boolean;
  adaptive_participant: DebateParticipant;
  evaluation_participant: DebateParticipant | null;
  recommendation: string | null;
  resolved_difficulty: string;
  resolution_reason: string;
  consensus_trace_id: string;
}

// ── Debate helpers (internal) ─────────────────────────────────────

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

// Returns null for empty strings and the literal "none" (Python serializes absence as "none")
function asString(value: unknown): string | null {
  if (typeof value === "string" && value.length > 0 && value !== "none") {
    return value;
  }
  return null;
}

// result may look like "advanced" or "difficulty=advanced" — handles both forms
function extractAdaptiveDifficulty(trace: AgentDecisionTrace): string {
  const diffDim = trace.dimensions.find(
    (d) => d.dimension === "difficulty" || d.dimension === "difficulty_level",
  );
  if (diffDim?.result) {
    const raw = diffDim.result.trim();
    const eqIdx = raw.indexOf("=");
    const value = eqIdx >= 0 ? raw.slice(eqIdx + 1).trim() : raw;
    if (value.length > 0) return value;
  }
  const match = /difficulty(?:_level)?[=:]([^\s,)]+)/.exec(
    trace.decision_summary,
  );
  if (match?.[1]) return match[1];
  return "intermediate";
}

function extractAdaptiveRationale(trace: AgentDecisionTrace): string {
  const diffDim = trace.dimensions.find(
    (d) =>
      d.dimension === "difficulty" ||
      d.dimension === "difficulty_level" ||
      d.dimension === "bloom_range",
  );
  if (diffDim?.signal) return diffDim.signal;
  return trace.decision_summary || "No rationale recorded.";
}

function extractEvaluationRationale(trace: AgentDecisionTrace): string {
  const recDim = trace.dimensions.find(
    (d) => d.dimension === "pedagogical_recommendation",
  );
  if (recDim?.signal) return recDim.signal;
  const clDim = trace.dimensions.find(
    (d) => d.dimension === "cognitive_load_assessment",
  );
  if (clDim?.signal) return clDim.signal;
  return trace.decision_summary || "No rationale recorded.";
}

// Two data sources:
//   "debate_context" evidence item → adaptive_difficulty, evaluation_override, conflict
//   "debate_resolution" dimension  → resolved_difficulty, recommendation
function extractDebateValues(consensusTrace: AgentDecisionTrace): {
  hasDebateContext: boolean;
  hasConflict: boolean;
  adaptiveDifficulty: string;
  evaluationOverride: string;
  resolvedDifficulty: string;
  recommendation: string | null;
} {
  const debateEvidenceItem = consensusTrace.evidence.find(
    (e) => e.key === "debate_context",
  );
  const debateVal = isRecord(debateEvidenceItem?.value_summary)
    ? debateEvidenceItem.value_summary
    : {};

  const debateDim = consensusTrace.dimensions.find(
    (d) => d.dimension === "debate_resolution",
  );
  const debateDimEv = debateDim?.evidence ?? {};

  const hasDebateContext = Boolean(
    debateVal["has_debate_context"] ?? debateDimEv["has_debate_context"] ?? false,
  );
  const hasConflict = Boolean(
    debateVal["conflict"] ?? debateDimEv["conflict"] ?? false,
  );
  const adaptiveDifficulty =
    asString(debateVal["adaptive_difficulty"]) ?? "intermediate";
  const evaluationOverride =
    asString(debateVal["evaluation_override"]) ?? adaptiveDifficulty;
  const resolvedDifficulty =
    asString(debateDimEv["resolved_difficulty"]) ?? adaptiveDifficulty;
  const recommendation =
    asString(debateDimEv["recommendation"]) ??
    asString(debateVal["recommendation"]) ??
    null;

  return {
    hasDebateContext,
    hasConflict,
    adaptiveDifficulty,
    evaluationOverride,
    resolvedDifficulty,
    recommendation,
  };
}

// ── Public debate functions ───────────────────────────────────────

/**
 * Derives a human-readable explanation of how the inter-agent conflict
 * was resolved. Mirrors _build_resolution_reason() in consensus_mediator.py.
 *
 * resolution_reason is not serialized in AgentDecisionTrace — re-derived here
 * from recommendation + difficulty values extracted from the trace chain.
 */
export function buildResolutionReason(
  recommendation: string | null,
  adaptiveDifficulty: string,
  evaluationOverride: string,
  conflict: boolean,
): string {
  if (!conflict) {
    return `Both agents agreed: the proposed difficulty "${adaptiveDifficulty}" was confirmed by EvaluationAgent. No override was applied.`;
  }

  const reasons: Partial<Record<DebateRecommendation, string>> = {
    retroceder: `EvaluationAgent detected insufficient mastery and reduced the difficulty from "${adaptiveDifficulty}" to "${evaluationOverride}" to support remediation before advancing.`,
    simplificar: `EvaluationAgent detected cognitive overload and reduced the difficulty from "${adaptiveDifficulty}" to "${evaluationOverride}" to prevent the ceiling effect.`,
    cambiar_modalidad: `EvaluationAgent detected sustained low engagement and adjusted the difficulty from "${adaptiveDifficulty}" to "${evaluationOverride}" to trigger a modality change.`,
    reforzar: `EvaluationAgent detected partial mastery and adjusted the difficulty from "${adaptiveDifficulty}" to "${evaluationOverride}" for a reinforcement phase before advancing.`,
    continuar: `EvaluationAgent confirmed that "${evaluationOverride}" is the appropriate difficulty and recommended continuing without remediation.`,
  };

  const reason = reasons[recommendation as DebateRecommendation];
  if (reason) return reason;

  return `EvaluationAgent overrode AdaptiveLearning's proposal "${adaptiveDifficulty}" → "${evaluationOverride}" (recommendation: "${recommendation ?? "unknown"}").`;
}

/**
 * Extracts a DebateResolution from the full agent trace chain.
 *
 * Returns null when AdaptiveLearningAgent or ConsensusMediator traces are absent.
 * Returns has_debate_context=false + evaluation_participant=null when
 * EvaluationAgent did not produce a difficulty override.
 *
 * TODO: if replay / multi-run is added, prefer the trace with highest sequence.
 */
export function extractDebateFromChain(
  chain: AgentDecisionTrace[],
): DebateResolution | null {
  if (chain.length === 0) return null;

  // Both agent_name and agent_type checked for robustness across potential renames
  const adaptiveTrace = chain.find(
    (t) =>
      t.agent_name === "adaptive_learning_agent" ||
      t.agent_type === "adaptive_learning",
  );
  const evaluationTrace = chain.find(
    (t) =>
      t.agent_name === "adaptive_learning_evaluation_agent" ||
      t.agent_type === "adaptive_evaluation",
  );
  const consensusTrace = chain.find(
    (t) =>
      t.agent_name === "consensus_mediator" ||
      t.agent_type === "consensus_mediator",
  );

  if (!adaptiveTrace || !consensusTrace) return null;

  const {
    hasDebateContext,
    hasConflict,
    adaptiveDifficulty,
    evaluationOverride,
    resolvedDifficulty,
    recommendation,
  } = extractDebateValues(consensusTrace);

  const adaptiveParticipant: DebateParticipant = {
    agent_name: adaptiveTrace.agent_name,
    agent_display_name: getAgentDisplayName(adaptiveTrace.agent_name),
    confidence: adaptiveTrace.confidence,
    proposed_difficulty: hasDebateContext
      ? adaptiveDifficulty
      : extractAdaptiveDifficulty(adaptiveTrace),
    rationale: extractAdaptiveRationale(adaptiveTrace),
    trace_id: adaptiveTrace.trace_id,
    is_winner: !hasConflict,
  };

  const evaluationParticipant: DebateParticipant | null =
    evaluationTrace && hasDebateContext
      ? {
          agent_name: evaluationTrace.agent_name,
          agent_display_name: getAgentDisplayName(evaluationTrace.agent_name),
          confidence: evaluationTrace.confidence,
          proposed_difficulty: hasConflict
            ? evaluationOverride
            : adaptiveDifficulty,
          rationale: extractEvaluationRationale(evaluationTrace),
          trace_id: evaluationTrace.trace_id,
          is_winner: hasConflict,
        }
      : null;

  return {
    has_debate_context: hasDebateContext,
    has_conflict: hasConflict,
    adaptive_participant: adaptiveParticipant,
    evaluation_participant: evaluationParticipant,
    recommendation,
    resolved_difficulty: resolvedDifficulty,
    resolution_reason: buildResolutionReason(
      recommendation,
      adaptiveDifficulty,
      evaluationOverride,
      hasConflict,
    ),
    consensus_trace_id: consensusTrace.trace_id,
  };
}

/**
 * Returns the overall debate state from a DebateResolution.
 * "conflict" is reserved for timeline components (intermediate banner between cards).
 * "resolved" is the overall state when a conflict was detected and settled.
 */
export function getDebateState(resolution: DebateResolution): DebateState {
  if (!resolution.has_debate_context) return "no_debate";
  if (!resolution.has_conflict) return "agreement";
  return "resolved";
}

/** Returns the short display label for a debate state (used in ConsensusBadge). */
export function getDebateStateLabel(state: DebateState): string {
  const LABELS: Record<DebateState, string> = {
    no_debate: "No Debate",
    agreement: "Agreement",
    conflict: "Conflict Detected",
    resolved: "Consensus Reached",
  };
  return LABELS[state];
}

/**
 * Returns a full human-readable description of the debate state.
 * Appends the raw recommendation when state is conflict/resolved.
 * Used as aria-label and tooltip text in ConsensusBadge.
 */
export function getDebateStateDescription(
  state: DebateState,
  recommendation?: string | null,
): string {
  const DESCRIPTIONS: Record<DebateState, string> = {
    no_debate:
      "EvaluationAgent did not generate a difficulty override. No inter-agent debate occurred.",
    agreement:
      "Both agents agreed on the proposed difficulty. No conflict was detected.",
    conflict:
      "AdaptiveLearning and EvaluationAgent proposed different difficulty levels.",
    resolved:
      "ConsensusMediator resolved the inter-agent conflict and produced a final difficulty decision.",
  };
  const base = DESCRIPTIONS[state];
  if (!recommendation || state === "no_debate" || state === "agreement") {
    return base;
  }
  return `${base} Pedagogical Recommendation: ${recommendation}.`;
}

// ── UI enumerations ───────────────────────────────────────────────

export type TraceTab =
  | "summary"
  | "evidence"
  | "dimensions"
  | "reasoning"
  | "raw";

export type ConfidenceLevel = "high" | "medium" | "low";

// ── Pipeline order (usado por MiniPipelineTimeline) ───────────────

export const PIPELINE_AGENTS = [
  "research_agent",
  "structural_pedagogical_agent",
  "adaptive_learning_agent",
  "adaptive_learning_evaluation_agent",
  "multimodal_planning_agent",
  "prompt_engineering_agent",
  "consistency_agent",
  "consensus_mediator",
] as const;

export type PipelineAgentName = (typeof PIPELINE_AGENTS)[number];

// ── Helpers ───────────────────────────────────────────────────────

export function getConfidenceLevel(confidence: number): ConfidenceLevel {
  if (confidence >= 0.85) return "high";
  if (confidence >= 0.65) return "medium";
  return "low";
}

export function getAgentDisplayName(agentName: string): string {
  const names: Record<string, string> = {
    research_agent: "Research Agent",
    structural_pedagogical_agent: "Structural Pedagogical Agent",
    adaptive_learning_agent: "Adaptive Learning Agent",
    adaptive_learning_evaluation_agent: "Evaluation Agent",
    multimodal_planning_agent: "Multimodal Planning Agent",
    prompt_engineering_agent: "Prompt Engineering Agent",
    consistency_agent: "Consistency Agent",
    consensus_mediator: "Consensus Mediator",
  };
  return names[agentName] ?? agentName;
}

export function formatElapsedMs(elapsed: number): string {
  if (!elapsed || elapsed <= 0) return "—";
  if (elapsed < 1000) return `${Math.round(elapsed)} ms`;
  return `${(elapsed / 1000).toFixed(2)} s`;
}
