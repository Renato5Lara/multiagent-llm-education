export interface WeeklyPlanCreate {
  thematic_line: string
  objectives: string[]
  pedagogical_intention: string
  total_weeks: number
}

export interface WeekSummary {
  id: string
  week_number: number
  theme: string
  bloom_target: number
  bloom_label: string
  objectives: string[]
  orchestration_status: string
  confidence: number | null
  generated_at: string | null
}

export interface WeeklyPlan {
  id: string
  course_id: string
  teacher_id: string
  total_weeks: number
  thematic_line: string
  pedagogical_intention: string
  bloom_progression: number[]
  week_themes: string[]
  status: string
  weeks: WeekSummary[]
  created_at: string
  updated_at: string
}

export interface PedagogicalStageItem {
  phase: string
  focus: string
  bloom_level: number
  content: string
  examples: string[]
}

export interface MisconceptionItemSchema {
  misconception: string
  correction: string
  severity: string
}

export interface MultimodalPromptSchema {
  modality: string
  prompt: string
  enabled: boolean
}

export interface WeekContentResponse {
  id: string
  week_id: string
  introduction: string
  pedagogical_explanation: string
  examples: string[]
  guided_practice: string
  storyboard: string | null
  continuity_notes: string | null
  pedagogical_stages: PedagogicalStageItem[]
  retrieval_evidence: Record<string, unknown>
  swarm_trace: Record<string, unknown>
  created_at: string
}

export interface WeekDetailResponse {
  id: string
  week_number: number
  plan_id: string
  theme: string
  bloom_target: number
  bloom_label: string
  objectives: string[]
  misconceptions: MisconceptionItemSchema[]
  real_applications: string[]
  recommended_modality: string | null
  multimodal_prompts: MultimodalPromptSchema[]
  evaluation_criteria: string[]
  orchestration_status: string
  confidence: number | null
  content: WeekContentResponse | null
  generated_at: string | null
}

export interface StructureTemplate {
  total_weeks: number
  name: string
}

export interface ValidationIssue {
  type: string
  severity: string
  message: string
}

export interface PlanValidation {
  valid: boolean
  issues: ValidationIssue[]
  health_score: number
}
