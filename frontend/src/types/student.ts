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

export interface AgentPlan {
  learning_profile?: {
    learning_style: string
    pace: string
    collaboration: string
    motivation: string
    preferred_bloom_levels: number[]
  }
  recommendations?: string[]
  path_plan?: {
    modules: Array<{
      title: string
      description: string
      order: number
      bloom_level: number
      recommended_resource_types: string[]
      estimated_duration: string
    }>
  }
  resource_recommendations?: Record<string, { resources: Array<{ id: string; filename: string; type: string }> }>
  evaluation_plan?: Array<{
    module_title: string
    questions: Array<{
      question: string
      options: string[]
      correct: number
    }>
    passing_score: number
  }>
}

export interface Competency {
  id: string
  name: string
  description: string | null
  competency_type: 'institutional' | 'career' | 'course'
  cycle: number | null
  active: boolean
  created_at: string
}
