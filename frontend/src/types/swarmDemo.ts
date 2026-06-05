export type DemoDecision = 'approve' | 'reject' | 'abstain'

export interface DemoStudent {
  student_id: string
  name: string
  profile: string
  mastery: number
  motivation: number
  risk: number
  learning_style: string
}

export interface DemoModule {
  module_id: string
  title: string
  topic: string
  difficulty: number
  prerequisite_gap: number
  assessment_score: number
}

export interface DemoEvent<T = Record<string, unknown>> {
  id: number
  session_id: string
  type: string
  payload: T
  created_at: string
}

export interface ConsensusPoint {
  step: number
  agent: string
  decision: DemoDecision
  confidence: number
  approve: number
  reject: number
  abstain: number
}

export interface TrustRecord {
  voter_name: string
  total_votes: number
  correct_votes: number
  incorrect_votes: number
  abstentions: number
  errors: number
  accuracy: number
  disagreement_rate: number
  avg_confidence: number
  confidence_calibration: number
  avg_latency_ms: number
  trust_score: number
  last_vote_at: string | null
}

export interface StartDemoResponse {
  session_id: string
  seed: number
  student: DemoStudent
  module: DemoModule
  events_url: string
  replay_url: string
}

export interface DemoReplay {
  session: {
    session_id: string
    status: string
    seed: number
    student: DemoStudent
    module: DemoModule
    created_at: string
    completed_at: string | null
  }
  events: DemoEvent[]
}

export interface RetrievalQuery {
  id: string
  category: string
  query: string
}

export interface RetrievalSource {
  query_id: string
  title: string
  domain: string
  url: string
  score: number
  confidence: number
  category: string
  summary: string
  rank: number
  grounded_objectives?: string[]
}

export interface RetrievalCompletePayload {
  topic: string
  retrieval_confidence: number
  pedagogical_confidence: number
  diversity_score: number
  contradiction_score: number
  prompt_grounding_score: number
  misconception_coverage: number
  bloom_alignment_score: number
  source_count: number
  unique_domains: number
  bloom_progression: BloomProgressionItem[]
  pedagogical_structure: PedagogicalPhase[]
  multimodal_plan: PromptGeneratedPayload[]
}

export interface BloomProgressionItem {
  level: number
  label: string
  activity: string
  status: 'grounded' | 'target' | 'extension' | string
}

export interface PedagogicalPhase {
  phase: string
  goal: string
  load: 'low' | 'medium' | 'high' | string
}

export interface PromptGeneratedPayload {
  id: string
  modality: string
  bloom_level: number
  prompt: string
  grounded_sources: string[]
  grounding_score: number
}

export interface ContradictionPayload {
  claim_a: string
  claim_b: string
  resolution: string
  severity: string
  confidence: number
  sources: string[]
}

export interface MisconceptionPayload {
  misconception: string
  impact: string
  remediation: string
  confidence: number
  source_url: string
}

export interface ConsistencyPayload {
  status: string
  continuity_score: number
  memory_coherence: number
  narrative_consistency: number
  issues: Array<{ type: string; detail: string; severity: string }>
  shared_memory_keys: string[]
  next_step: string
}

export interface SandboxValidationPayload {
  agent: string
  phase: string
  approved?: boolean
  iterations?: number
  final_feedback?: string
  status?: string
  success?: boolean
  confidence?: number
  sandbox_result?: {
    status?: string
    success?: boolean
    execution_time_ms?: number
    memory_usage_mb?: number
    exit_code?: number | null
    timed_out?: boolean
    stdout_preview?: string
    stderr_preview?: string
    traceback_preview?: string
    violations?: Array<Record<string, unknown>>
  }
  code_preview?: string
  limits?: {
    timeout_seconds: number
    memory_mb: number
  }
}

export type ReplayMode = 'realtime' | 'accelerated' | 'step-by-step' | 'cognitive'

export interface CognitiveReplayEvent {
  id: number
  session_id: string
  event_type: string
  timestamp: string
  payload: Record<string, unknown>
  trace_id: string
  correlation_id: string
  agent_name: string
  phase: string
  latency_ms: number
  confidence: number | null
  metadata: Record<string, unknown>
  cognitive_label: string
  narrative_step: string
}

export interface CognitiveReplaySummary {
  session_id: string
  event_count: number
  duration_ms: number
  phases: string[]
  agents: string[]
  retrieval_sources: number
  consensus_votes: number
  memory_publications: number
  generated_prompts: number
  contradictions: number
  misconceptions: number
  final_decision: string | null
  final_confidence: number | null
}

export interface CognitiveReplay {
  session: DemoReplay['session']
  events: CognitiveReplayEvent[]
  summary: CognitiveReplaySummary
  modes: ReplayMode[]
}

// ── Memory-Influenced Pedagogical Generation types ──────────────────

export interface AdaptationMetrics {
  adaptation_consistency: number
  personalization_strength: number
  continuity_score: number
  memory_reuse_score: number
  pedagogical_adaptation_quality: number
  longitudinal_coherence: number
  total_weeks: number
  adaptation_count: number
  memory_records_used: number
}

export interface StudentProfile {
  student_id: string
  learning_style?: string
  preferred_modality?: string
  preferred_analogies?: string[]
  pacing?: string
  cognitive_load_trend?: string
  bloom_level_reached?: number
  common_misconceptions?: Array<Record<string, unknown>>
  engagement_pattern?: string
  narrative_persona?: string
  successful_example_types?: string[]
  visual_continuity?: Record<string, unknown>
  adaptation_history?: Array<Record<string, unknown>>
}

export interface AdaptationSignal {
  cognitive_load_trend: string
  engagement_pattern: string
}

export interface InfluenceEvent {
  metrics: AdaptationMetrics
  profile: StudentProfile
  ts: string
}

export interface PromptAdaptationInfo {
  analogy_domain: string | null
  learning_style: string
  tone: string
  phase_labels: string[]
}

export interface AdaptationRationale {
  learning_style: string
  cognitive_load_trend: string
  pacing: string
  analogy_domain: string | null
  bloom_level_reached: number
  bloom_adjusted_reason: string
}

// ── Explainability types ────────────────────────────────────────────

export interface Reason {
  factor: string
  value: unknown
  contribution: number
  evidence: string
}

export interface Explanation {
  dimension: string
  previous_value: unknown
  new_value: unknown
  reasons: Reason[]
  confidence: number
  trace_id: string
}

export interface DecisionGraphNode {
  id: string
  label: string
  type: 'signal' | 'decision'
  dimension?: string
  factor?: string
}

export interface DecisionGraphEdge {
  from: string
  to: string
  label: string
  contribution: number
}

export interface DecisionGraph {
  nodes: DecisionGraphNode[]
  edges: DecisionGraphEdge[]
}

export interface AdaptationExplanation {
  student_id: string
  week_number: number
  explanations: Explanation[]
  decision_graph: DecisionGraph
  metrics: Record<string, unknown>
  generated_at: string
}

export const DIMENSION_LABELS: Record<string, string> = {
  bloom: 'Bloom Level',
  cognitive_load: 'Cognitive Load',
  prompt: 'Prompt Engineering',
  modality: 'Modality',
  pacing: 'Pacing',
  scaffolding: 'Scaffolding',
}

export const DIMENSION_COLORS: Record<string, string> = {
  bloom: 'bg-violet-100 text-violet-800',
  cognitive_load: 'bg-amber-100 text-amber-800',
  prompt: 'bg-blue-100 text-blue-800',
  modality: 'bg-emerald-100 text-emerald-800',
  pacing: 'bg-rose-100 text-rose-800',
  scaffolding: 'bg-cyan-100 text-cyan-800',
}
