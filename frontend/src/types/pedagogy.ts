export interface WeeklyPedagogicalPlanCreate {
  week_number: number
  topic: string
  objectives: string[]
  bloom_target: number
  pedagogical_style: string
  pedagogical_intention: string
  preferred_modality: string
}

export interface WeeklyPedagogicalPlan {
  id: string
  course_id: string
  teacher_id: string
  week_number: number
  topic: string
  objectives: string[]
  bloom_target: number
  pedagogical_style: string
  pedagogical_intention: string
  preferred_modality: string
  orchestration_status: string
  retrieval_summary: Record<string, unknown>
  pedagogical_structure: {
    weekly_sequence?: Array<{ phase: string; focus: string }>
    [key: string]: unknown
  }
  adaptive_plan: Record<string, unknown>
  multimodal_plan: Record<string, unknown>
  prompt_plan: Record<string, unknown>
  consistency_validation: {
    issues?: Array<{ type: string; severity: string }>
    [key: string]: unknown
  }
  consensus_result: {
    decision?: string
    [key: string]: unknown
  }
  generated_at: string
  validated_at: string | null
}

export interface PedagogicalStage {
  phase: string
  focus: string
  bloom_level: number
  content: string
  examples: string[]
}

export interface MisconceptionItem {
  misconception: string
  correction: string
  severity: string
}

export interface MultimodalPrompt {
  modality: string
  prompt: string
  enabled: boolean
}

export interface ModuleOrchestrationResponse {
  module_id: string
  module_title: string
  course_id: string
  course_name: string
  orchestration_status: string
  introduction: string
  pedagogical_explanation: string
  misconceptions: MisconceptionItem[]
  examples: string[]
  real_applications: string[]
  guided_practice: string
  pedagogical_stages: PedagogicalStage[]
  multimodal_prompts: MultimodalPrompt[]
  storyboard: string
  continuity_notes: string
  bloom_progression: Array<{ level: number; label: string; description: string; mastered: boolean }>
  retrieval_evidence: {
    sources_count: number
    confidence: number
    degraded: boolean
    sources: Array<{ title: string; domain: string; relevance: number }>
  }
  confidence: number
  generated_at: string
}
