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

export interface CycleAggregates {
  n_ciclos: number
  tiempo_promedio_por_concepto_seg: Record<string, number | null>
  tasa_remediacion_global_pct: number | null
  tasa_remediacion_por_concepto_pct: Record<string, number | null>
  frecuencia_modalidad_refuerzo: Record<string, number>
  distribucion_profundidad: Record<string, number>
}

export function useCycleAggregates() {
  return useQuery({
    queryKey: ['research-cycle-aggregates'],
    queryFn: async () => {
      const resp = await api.get<CycleAggregates>('/api/research/cycle-aggregates')
      return resp.data
    },
  })
}

export interface StudentCycleRow {
  student_id: string
  email: string
  concepto: string | null
  intentos: number | null
  resultado: boolean | null
  ayudas: number | null
  tiempo_ms: number | null
  modalidad_diagnosticada: string | null
  modalidad_refuerzo: string | null
  profundidad: string | null
  fecha: string | null
  justificacion: string
}

export function useStudentCycles(studentId: string | null) {
  return useQuery({
    queryKey: ['research-student-cycles', studentId],
    queryFn: async () => {
      const resp = await api.get<{ total: number; rows: StudentCycleRow[] }>(
        `/api/research/students/${studentId}/cycles`
      )
      return resp.data
    },
    enabled: !!studentId,
  })
}
