import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { useToast } from '@/hooks/use-toast'
import type { WeeklyPedagogicalPlan, WeeklyPedagogicalPlanCreate } from '@/types/pedagogy'

export function useWeeklyPedagogicalPlans(courseId: string | undefined) {
  return useQuery({
    queryKey: ['pedagogy', courseId, 'weekly-plans'],
    queryFn: async () => {
      const resp = await api.get<WeeklyPedagogicalPlan[]>(`/api/pedagogy/courses/${courseId}/weekly-plans`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useGenerateWeeklyPedagogicalPlan() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, data }: { courseId: string; data: WeeklyPedagogicalPlanCreate }) => {
      const resp = await api.post<WeeklyPedagogicalPlan>(`/api/pedagogy/courses/${courseId}/weekly-plans`, data)
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['pedagogy', variables.courseId, 'weekly-plans'] })
      toast({ title: 'Orquestacion pedagogica generada' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al orquestar plan', description: getErrorMessage(error) })
    },
  })
}

export function useValidateWeeklyPedagogicalPlan() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async (planId: string) => {
      const resp = await api.post<WeeklyPedagogicalPlan>(`/api/pedagogy/weekly-plans/${planId}/validate`)
      return resp.data
    },
    onSuccess: (plan) => {
      queryClient.invalidateQueries({ queryKey: ['pedagogy', plan.course_id, 'weekly-plans'] })
      toast({ title: 'Plan validado por docente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al validar plan', description: getErrorMessage(error) })
    },
  })
}
