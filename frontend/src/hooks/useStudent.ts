import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api, { getErrorMessage } from '@/lib/api'
import type { DiagnosticResult, LearningPath, PathModule, AgentPlan } from '@/types/student'
import { useToast } from '@/hooks/use-toast'

export function useSubmitDiagnostic() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, answers }: { courseId: string; answers: Record<string, number> }) => {
      const resp = await api.post<DiagnosticResult>(`/api/estudiante/diagnostic/${courseId}`, { answers })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['diagnostic', variables.courseId] })
      toast({ title: 'Diagnóstico guardado exitosamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al guardar diagnóstico', description: getErrorMessage(error) })
    },
  })
}

export function useDiagnostic(courseId: string | undefined) {
  return useQuery({
    queryKey: ['diagnostic', courseId],
    queryFn: async () => {
      const resp = await api.get<DiagnosticResult>(`/api/estudiante/diagnostic/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useGeneratePath() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (courseId: string) => {
      const resp = await api.post<LearningPath>(`/api/estudiante/path/${courseId}`)
      return resp.data
    },
    onSuccess: (_data, courseId) => {
      queryClient.invalidateQueries({ queryKey: ['learning-path', courseId] })
      toast({ title: 'Ruta de aprendizaje generada' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al generar ruta', description: getErrorMessage(error) })
    },
  })
}

export function useLearningPath(courseId: string | undefined) {
  return useQuery({
    queryKey: ['learning-path', courseId],
    queryFn: async () => {
      const resp = await api.get<LearningPath>(`/api/estudiante/path/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useUpdateModule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ moduleId, status, score }: { moduleId: string; status: string; score?: number }) => {
      const resp = await api.patch<PathModule>(`/api/estudiante/module/${moduleId}`, { status, score })
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['learning-path'] })
    },
  })
}

export function useAgentGeneratePlan() {
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, answers }: { courseId: string; answers: Record<string, number> }) => {
      const resp = await api.post<AgentPlan>('/api/agents/generate-plan', { course_id: courseId, answers })
      return resp.data
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error del agente', description: getErrorMessage(error) })
    },
  })
}

export function useStartEvaluation() {
  return useMutation({
    mutationFn: async (courseId: string) => {
      const resp = await api.post(`/api/estudiante/evaluation/${courseId}/start`)
      return resp.data
    },
  })
}

export function useSubmitEvaluation() {
  return useMutation({
    mutationFn: async ({ attemptId, answers }: { attemptId: string; answers: Record<number, number> }) => {
      const resp = await api.post(`/api/estudiante/evaluation/${attemptId}/submit`, { answers })
      return resp.data
    },
  })
}
