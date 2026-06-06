import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import type {
  DiagnosticResult,
  LearningPath,
  PathModule,
  AgentPlan,
  StudentProfile,
  LearningPathDetail,
  CourseProgress,
  StudentProgressEntry,
} from '@/types/student'
import { useToast } from '@/hooks/use-toast'

export function useSubmitDiagnostic() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, answers }: { courseId: string; answers: Record<string, number> }) => {
      const resp = await api.post<DiagnosticResult>(`/api/students/diagnostic/${courseId}`, { answers })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['diagnostic', variables.courseId] })
      queryClient.invalidateQueries({ queryKey: ['student-profile'] })
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
      queryClient.invalidateQueries({ queryKey: ['learning-path', variables.courseId] })
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
      const resp = await api.get<DiagnosticResult>(`/api/students/diagnostic/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useStudentProfile() {
  return useQuery({
    queryKey: ['student-profile'],
    queryFn: async () => {
      const resp = await api.get<StudentProfile>('/api/students/profile')
      return resp.data
    },
  })
}

export function useSaveStudentProfile() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (data: { preferred_modalities: string[]; dominant_style: string | null }) => {
      const resp = await api.post<StudentProfile>('/api/students/profile', data)
      return resp.data
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['student-profile'] })
      toast({ title: 'Perfil de aprendizaje guardado' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al guardar perfil', description: getErrorMessage(error) })
    },
  })
}

export function useMyCourses() {
  return useQuery({
    queryKey: ['my-courses'],
    queryFn: async () => {
      const resp = await api.get<CourseProgress[]>('/api/students/my-courses')
      return resp.data
    },
  })
}

export function useGeneratePath() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (courseId: string) => {
      const resp = await api.post<LearningPath>(`/api/students/learning-path/${courseId}`)
      return resp.data
    },
    onSuccess: (_data, courseId) => {
      queryClient.invalidateQueries({ queryKey: ['learning-path', courseId] })
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
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
      const resp = await api.get<LearningPathDetail>(`/api/students/learning-path/${courseId}`)
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
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
    },
  })
}

export function useUpdateProgress() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, resourceId, progressPercentage }: { courseId: string; resourceId?: string; progressPercentage?: number }) => {
      const resp = await api.post<StudentProgressEntry>(`/api/students/progress/${courseId}`, {
        resource_id: resourceId,
        progress_percentage: progressPercentage,
      })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
      queryClient.invalidateQueries({ queryKey: ['course-progress', variables.courseId] })
      toast({ title: 'Progreso actualizado' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al actualizar progreso', description: getErrorMessage(error) })
    },
  })
}

export function useCourseProgress(courseId: string | undefined) {
  return useQuery({
    queryKey: ['course-progress', courseId],
    queryFn: async () => {
      const resp = await api.get(`/api/students/progress/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useAgentGeneratePlan() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, answers }: { courseId: string; answers: Record<string, number> }) => {
      const resp = await api.post<AgentPlan>('/api/agents/generate-plan', { course_id: courseId, answers })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['learning-path', variables.courseId] })
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
      toast({ title: 'Plan generado exitosamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error del agente', description: getErrorMessage(error) })
    },
  })
}

export function useAcademicSummary() {
  return useQuery({
    queryKey: ['academic-summary'],
    queryFn: async () => {
      const resp = await api.get('/api/students/academic/summary')
      return resp.data as {
        current_cycle: number | null
        total_courses: number
        completed_diagnostics: number
        total_modules: number
        completed_modules: number
        progress_percentage: number
        dominant_modality: string | null
        has_onboarded: boolean
      }
    },
  })
}

export function useTutorChat() {
  return useMutation({
    mutationFn: async ({ courseId, message, context }: {
      courseId: string
      message: string
      context?: Record<string, unknown>
    }) => {
      const resp = await api.post('/api/students/tutor/chat', {
        message,
        course_id: courseId,
        context: context || {},
      })
      return resp.data as { response: string }
    },
  })
}

export function useStartEvaluation() {
  return useMutation({
    mutationFn: async (courseId: string) => {
      const resp = await api.post(`/api/students/evaluation/${courseId}/start`)
      return resp.data
    },
  })
}

export function useSubmitEvaluation() {
  return useMutation({
    mutationFn: async ({ attemptId, answers }: { attemptId: string; answers: Record<number, number> }) => {
      const resp = await api.post(`/api/students/evaluation/${attemptId}/submit`, { answers })
      return resp.data
    },
  })
}
