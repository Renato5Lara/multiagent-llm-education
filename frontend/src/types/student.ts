export interface DiagnosticResult {
  id: string
  student_id: string
  course_id: string
  answers: Record<string, number>
  profile?: {
    dominant_modality?: string
    modality_scores?: Record<string, number>
    learning_style?: string
    pace?: string
    collaboration?: string
    motivation?: string
    recommendations?: string[]
  } | null
  modality_scores?: Record<string, number>
  dominant_modality?: string
  completed_at: string
}

export interface StudentProfile {
  id: string
  student_id: string
  preferred_modalities: string[]
  dominant_style: string | null
  updated_at: string
}

export interface PathModule {
  id: string
  title: string
  description?: string
  order: number
  status: string
  bloom_level?: number
  resource_id?: string
  score?: number
  completed_at?: string
}

export interface LearningPath {
  id: string
  student_id: string
  course_id: string
  total_modules: number
  completed_modules: number
  status: string
  modules: PathModule[]
}

export interface LearningPathItem {
  id: string
  title: string
  description?: string
  order: number
  status: string
  // Distingue, dentro de los ítems 'available', el frente de trabajo real
  // (a dónde navegar) de los que están disponibles por ya dominados y
  // saltables. Corrección de adaptación por nivel (auditoría causal, ago. 2026).
  is_frontier?: boolean
  resource_id?: string
  resource_type?: string
  competencies: string[]
}

export interface LearningPathDetail {
  course_id: string
  course_name: string
  dominant_modality: string | null
  preferred_modalities: string[]
  items: LearningPathItem[]
}

export interface CourseProgress {
  course_id: string
  course_name: string
  course_code: string
  cycle: number
  total_resources: number
  completed_resources: number
  progress_percentage: number
  has_diagnostic: boolean
  has_learning_path: boolean
  dominant_modality: string | null
  is_active_experience: boolean
}

export interface StudentProgressEntry {
  id: string
  student_id: string
  course_id: string
  resource_id: string | null
  completed: boolean
  completed_at?: string
  progress_percentage: number
  created_at: string
  updated_at: string
}

export interface EvaluationAttempt {
  id: string
  student_id: string
  course_id: string
  module_id?: string
  score?: number
  max_score: number
  passed: number
  attempted_at: string
  completed_at?: string
}

// ── D4.1 — Adaptive decision ───────────────────────────────────────────────────

export interface AdaptiveDecision {
  content_order: string[]
  content_type_labels: Record<string, string>
  skip_hint_topics: string[]
  emphasis_topics: string[]
  emphasis_topic_labels: string[]
  strategy_description: string
  prior_emphasis: string
  modality_label: string
}

// ── D4.2 — Content library ─────────────────────────────────────────────────────

export type ContentType = 'theory' | 'example' | 'video' | 'diagram' | 'game' | 'simulation' | 'exercise'

// Matches backend ContentBlockResponse
export interface ContentBlockItem {
  type: string
  title: string
  body?: string | null
  code?: string | null
  language?: string | null
  is_placeholder: boolean
  placeholder_sprint?: string | null
  estimated_minutes: number
}

// Matches backend AdaptiveContentResponse
export interface AdaptiveContentResponse {
  topic_slug: string
  modality: string
  blocks: ContentBlockItem[]
  total_minutes: number
}

// Richer interface reserved for D4.4 full render (not yet used by API)
export interface AdaptiveModuleContent {
  module_id: string
  content_order: ContentType[]
  blocks: ContentBlockItem[]
  estimated_minutes: number
}

// ── Competency ─────────────────────────────────────────────────────────────────

export interface Competency {
  id: string
  name: string
  description: string | null
  competency_type: 'institutional' | 'career' | 'course'
  cycle: number | null
  active: boolean
  created_at: string
}
