import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { filterToReferenceModules } from '@/lib/experiences'
import type {
  DiagnosticResult,
  LearningPath,
  PathModule,
  StudentProfile,
  LearningPathDetail,
  CourseProgress,
  StudentProgressEntry,
  AdaptiveDecision,
} from '@/types/student'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'
import { useToast } from '@/hooks/use-toast'

export function useSubmitDiagnostic() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, answers }: { courseId: string; answers: Record<string, number> }) => {
      // La deliberación real encadena 5 agentes LLM (Diagnóstico → Perfil →
      // Adaptación → Tutor → Consenso): 30-45s+ observados, igual que
      // useModuleOrchestration — mismo motivo, mismo ajuste.
      const resp = await api.post<DiagnosticResult>(`/api/students/diagnostic/${courseId}`, { answers }, {
        timeout: 120_000,
      })
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

export function useAdaptiveContent(topicSlug: string | undefined, courseId: string | undefined) {
  return useQuery({
    queryKey: ['adaptive-content', topicSlug, courseId],
    queryFn: async () => {
      const resp = await api.get<import('@/types/student').AdaptiveContentResponse>(
        `/api/students/adaptive-content/${topicSlug}?course_id=${courseId}`,
      )
      return resp.data
    },
    enabled: !!topicSlug && !!courseId,
    staleTime: Infinity,
  })
}

export function useAdaptiveDecision(courseId: string | undefined) {
  return useQuery({
    queryKey: ['adaptive-decision', courseId],
    queryFn: async () => {
      const resp = await api.get<AdaptiveDecision>(`/api/students/adaptive-decision/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
    staleTime: Infinity, // diagnostic-derived, changes only when re-diagnosed
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

export type ExperienceState = 'NOT_STARTED' | 'READY' | 'IN_PROGRESS' | 'COMPLETED'

export interface ActiveExperience {
  slug: string | null
  title: string | null
  state: ExperienceState
}

/**
 * useActiveExperience — identidad de dominio del recorrido del estudiante.
 * Devuelve { slug, title, state }; deliberadamente NO expone ningún id de curso.
 * Es la única fuente para saber "cuál es la experiencia activa" y su estado.
 */
export function useActiveExperience() {
  return useQuery({
    queryKey: ['active-experience'],
    queryFn: async () => {
      const resp = await api.get<ActiveExperience>('/api/students/experience')
      return resp.data
    },
    retry: false,
    staleTime: 30000,
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
      // PED-004 — modo módulo de referencia: los módulos legacy no se muestran
      // ni se alcanzan. Filtrar aquí cubre TODAS las superficies que consumen
      // la ruta (página de ruta, dashboard y la navegación post-completado).
      return { ...resp.data, items: filterToReferenceModules(resp.data.items) }
    },
    enabled: !!courseId,
  })
}

export function useUpdateModule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (
      { moduleId, status, score, durationMinutes }:
      { moduleId: string; status: string; score?: number; courseId?: string; durationMinutes?: number },
    ) => {
      const resp = await api.patch<PathModule>(`/api/students/module/${moduleId}`, {
        status, score, duration_minutes: durationMinutes,
      })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
      if (variables.courseId) {
        queryClient.invalidateQueries({ queryKey: ['learning-path', variables.courseId] })
      }
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

export type ModuleOrchestrationResult = ModuleOrchestrationResponse & {
  session_id: string | null
}

export function useModuleOrchestration() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (moduleId: string) => {
      // LLM orchestration can take 60-120s; use a dedicated timeout instead of
      // the global 30s so the UI doesn't abort a legitimate long-running request.
      const resp = await api.post<ModuleOrchestrationResult>(`/api/students/module/${moduleId}/orchestrate`, undefined, {
        timeout: 120_000,
      })
      return resp.data
    },
    onSuccess: (_data, moduleId) => {
      queryClient.invalidateQueries({ queryKey: ['student-profile'] })
      queryClient.invalidateQueries({ queryKey: ['my-courses'] })
      queryClient.invalidateQueries({ queryKey: ['learning-path'] })
      queryClient.invalidateQueries({ queryKey: ['module', moduleId] })
      toast({ title: 'Módulo orquestado correctamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al orquestar módulo', description: getErrorMessage(error) })
    },
  })
}

/**
 * Misión Activa — persiste el cursor del recorrido (paso, completados, XP).
 * Silencioso a propósito: la continuidad nunca interrumpe al estudiante
 * (un fallo aquí solo significa que el próximo ingreso retoma un paso atrás).
 */
export function useUpdateMissionProgress() {
  return useMutation({
    mutationFn: async ({ moduleId, currentIndex, completedStepIds, totalXp }: {
      moduleId: string
      currentIndex: number
      completedStepIds: string[]
      totalXp: number
    }) => {
      const resp = await api.patch(`/api/students/module/${moduleId}/mission-progress`, {
        current_index: currentIndex,
        completed_step_ids: completedStepIds,
        total_xp: totalXp,
      })
      return resp.data
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
      // Dispara Diagnosticar → Remediar/Orientar → Consenso sobre LLM real
      // (mismo motivo que useSubmitDiagnostic/useModuleOrchestration).
      const resp = await api.post(`/api/students/evaluation/${attemptId}/submit`, { answers }, {
        timeout: 120_000,
      })
      return resp.data
    },
  })
}

export interface CycleEvidencePayload {
  courseId: string
  competencia: string
  attempts: number
  solved: boolean
}

/** Evaluación continua (refinamiento de experiencia, jul 2026): la
 *  evidencia de resolver la práctica de un ciclo entra al Runtime real
 *  en el momento en que ocurre, sin esperar la Evaluación de Módulo
 *  separada. Fire-and-forget desde la UI — nunca bloquea al estudiante
 *  ni su avance (mismo criterio best-effort del propio endpoint). */
export function useSubmitCycleEvidence() {
  return useMutation({
    mutationFn: async (payload: CycleEvidencePayload) => {
      const resp = await api.post('/api/students/cycle-evidence', {
        course_id: payload.courseId,
        competencia: payload.competencia,
        attempts: payload.attempts,
        solved: payload.solved,
      }, { timeout: 120_000 })
      return resp.data
    },
  })
}
