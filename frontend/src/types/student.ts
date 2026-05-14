export interface DiagnosticResult {
  id: string
  student_id: string
  course_id: string
  answers: Record<string, number>
  profile?: {
    learning_style: string
    pace: string
    collaboration: string
    motivation: string
    recommendations: string[]
  } | null
  completed_at: string
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
