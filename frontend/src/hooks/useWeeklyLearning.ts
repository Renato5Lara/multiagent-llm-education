import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { useToast } from '@/hooks/use-toast'
import type {
  WeeklyPlan,
  WeeklyPlanCreate,
  WeekDetailResponse,
  StructureTemplate,
  PlanValidation,
} from '@/types/weeklyLearning'

export function useTemplates() {
  return useQuery({
    queryKey: ['weekly-learning', 'templates'],
    queryFn: async () => {
      const resp = await api.get<{ templates: StructureTemplate[] }>('/api/weekly-learning/templates')
      return resp.data.templates
    },
    staleTime: 1000 * 60 * 60,
  })
}

export function useCreatePlan() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, data }: { courseId: string; data: WeeklyPlanCreate }) => {
      const resp = await api.post<WeeklyPlan>(`/api/weekly-learning/courses/${courseId}/plan`, data)
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', variables.courseId] })
      toast({ title: 'Plan semanal creado', description: 'La estructura semanal ha sido generada exitosamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al crear plan', description: getErrorMessage(error) })
    },
  })
}

export function useWeeklyPlan(courseId: string | undefined) {
  return useQuery({
    queryKey: ['weekly-plan', courseId],
    queryFn: async () => {
      const resp = await api.get<WeeklyPlan>(`/api/weekly-learning/courses/${courseId}/plan`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useWeekDetail(courseId: string | undefined, weekNumber: number | undefined) {
  return useQuery({
    queryKey: ['week-detail', courseId, weekNumber],
    queryFn: async () => {
      const resp = await api.get<WeekDetailResponse>(
        `/api/weekly-learning/courses/${courseId}/weeks/${weekNumber}`
      )
      return resp.data
    },
    enabled: !!courseId && !!weekNumber,
  })
}

export function useOrchestrateWeek() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, weekNumber }: { courseId: string; weekNumber: number }) => {
      const resp = await api.post<WeekDetailResponse>(
        `/api/weekly-learning/courses/${courseId}/weeks/${weekNumber}/orchestrate`
      )
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['week-detail', variables.courseId, variables.weekNumber] })
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', variables.courseId] })
      toast({ title: 'Semana orquestada', description: 'Contenido pedagógico generado exitosamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al orquestar', description: getErrorMessage(error) })
    },
  })
}

export function useValidatePlan(courseId: string | undefined) {
  return useQuery({
    queryKey: ['weekly-plan-validation', courseId],
    queryFn: async () => {
      const resp = await api.get<PlanValidation>(`/api/weekly-learning/courses/${courseId}/validate`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useDeletePlan() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (courseId: string) => {
      await api.delete(`/api/weekly-learning/courses/${courseId}/plan`)
    },
    onSuccess: (_data, courseId) => {
      queryClient.invalidateQueries({ queryKey: ['weekly-plan', courseId] })
      toast({ title: 'Plan eliminado' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al eliminar', description: getErrorMessage(error) })
    },
  })
}
