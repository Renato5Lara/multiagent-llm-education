import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'

export interface ResearchSummary {
  group_label: string
  n_students_pretested: number
  n_students_posttested: number
  n_compared: number
  avg_pre_pct: number | null
  avg_post_pct: number | null
  avg_absolute_gain: number | null
  avg_normalized_gain: number | null
  level_distribution_pre: Record<string, number>
  level_distribution_post: Record<string, number>
  avg_path_generation_ms: number | null
  avg_ai_orchestration_ms: number | null
  avg_tutor_latency_ms: number | null
  avg_pre_duration_seconds: number | null
  avg_post_duration_seconds: number | null
  students_by_profile: Record<string, number>
  paths_generated: number
  tutor_messages_total: number
  avg_tutor_messages_per_student: number
}

export interface ResearchStudentRow {
  student_id: string
  group: string
  pre_pct: number | null
  post_pct: number | null
  absolute_gain: number | null
  normalized_gain: number | null
  level: string | null
  pre_level: string | null
  post_level: string | null
  path_generation_ms: number | null
  ai_time_ms: number | null
  total_time_seconds: number | null
  profile: string | null
  course: string
  date: string | null
}

export function useResearchSummary() {
  return useQuery({
    queryKey: ['research-summary'],
    queryFn: async () => {
      const resp = await api.get<ResearchSummary>('/api/research/summary')
      return resp.data
    },
  })
}

export function useResearchStudents() {
  return useQuery({
    queryKey: ['research-students'],
    queryFn: async () => {
      const resp = await api.get<{ total: number; rows: ResearchStudentRow[] }>('/api/research/students')
      return resp.data
    },
  })
}
