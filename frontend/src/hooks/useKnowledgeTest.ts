import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'

export type KnowledgeTestKind = 'pre' | 'post'

export interface KnowledgeTestQuestion {
  id: string
  module_number: number
  topic: string
  text: string
  options: string[]
  difficulty: string
}

export interface KnowledgeAttemptSummary {
  attempt_id: string
  kind: KnowledgeTestKind
  status: 'in_progress' | 'completed'
  started_at: string
  completed_at: string | null
  score: number | null
  total_questions: number | null
  percentage: number | null
  level: string | null
  level_label: string | null
  duration_seconds: number | null
}

export interface KnowledgeTestStatus {
  bank_available: boolean
  pretest_required: boolean
  has_learning_path: boolean
  pretest: KnowledgeAttemptSummary | null
  posttest: KnowledgeAttemptSummary | null
}

export interface KnowledgeTestStartResponse {
  attempt_id: string
  kind: KnowledgeTestKind
  status: string
  started_at: string
  total_questions: number
  resumed: boolean
  questions: KnowledgeTestQuestion[]
}

export interface KnowledgeTestResult {
  attempt_id: string
  kind: KnowledgeTestKind
  status: string
  score: number | null
  total_questions: number | null
  percentage: number | null
  level: string | null
  level_label: string | null
  duration_seconds: number | null
  started_at: string | null
  completed_at: string | null
  module_breakdown: Record<string, { correct: number; total: number; pct: number }> | null
  mastered_modules: number[]
  critical_modules: number[]
}

export interface ExperimentComparison {
  student_id: string
  course_id: string
  pre_percentage: number
  post_percentage: number
  absolute_gain: number
  percent_gain: number | null
  normalized_gain: number | null
  pre_level: string
  post_level: string
  pre_duration_seconds: number | null
  post_duration_seconds: number | null
  group_label: string
  computed_at: string
}

export function useKnowledgeTestStatus(courseId: string | undefined) {
  return useQuery({
    queryKey: ['knowledge-test-status', courseId],
    queryFn: async () => {
      const resp = await api.get<KnowledgeTestStatus>(`/api/students/knowledge-test/${courseId}/status`)
      return resp.data
    },
    enabled: !!courseId,
    retry: false,
    staleTime: 30000,
  })
}

export function useStartKnowledgeTest() {
  return useMutation({
    mutationFn: async ({ courseId, kind }: { courseId: string; kind: KnowledgeTestKind }) => {
      const resp = await api.post<KnowledgeTestStartResponse>(
        `/api/students/knowledge-test/${courseId}/start`,
        { kind },
      )
      return resp.data
    },
  })
}

export function useSubmitKnowledgeTest() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ attemptId, answers }: { attemptId: string; answers: Record<string, number> }) => {
      const resp = await api.post<KnowledgeTestResult>(
        `/api/students/knowledge-test/attempt/${attemptId}/submit`,
        { answers },
      )
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['knowledge-test-status'] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-test-result'] })
      queryClient.invalidateQueries({ queryKey: ['knowledge-comparison'] })
    },
  })
}

export function useKnowledgeTestResult(courseId: string | undefined, kind: KnowledgeTestKind, enabled = true) {
  return useQuery({
    queryKey: ['knowledge-test-result', courseId, kind],
    queryFn: async () => {
      const resp = await api.get<KnowledgeTestResult>(
        `/api/students/knowledge-test/${courseId}/result?kind=${kind}`,
      )
      return resp.data
    },
    enabled: !!courseId && enabled,
    retry: false,
  })
}

export function useKnowledgeComparison(courseId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['knowledge-comparison', courseId],
    queryFn: async () => {
      const resp = await api.get<ExperimentComparison>(
        `/api/students/knowledge-test/${courseId}/comparison`,
      )
      return resp.data
    },
    enabled: !!courseId && enabled,
    retry: false,
  })
}
