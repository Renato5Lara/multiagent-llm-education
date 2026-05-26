import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import type { Competency } from '@/types/student'
import { useToast } from '@/hooks/use-toast'

export function useCompetencies(type?: string) {
  return useQuery({
    queryKey: ['competencies', type],
    queryFn: async () => {
      const url = type ? `/api/competencies?competency_type=${type}` : '/api/competencies'
      const resp = await api.get<{ competencies: Competency[]; total: number }>(url)
      return resp.data.competencies
    },
  })
}

export function useInstitutionalCompetencies() {
  return useQuery({
    queryKey: ['competencies', 'institutional'],
    queryFn: async () => {
      const resp = await api.get<{ competencies: Competency[]; total: number }>('/api/competencies/institutional')
      return resp.data.competencies
    },
  })
}

export function useCareerCompetencies() {
  return useQuery({
    queryKey: ['competencies', 'career'],
    queryFn: async () => {
      const resp = await api.get<{ competencies: Competency[]; total: number }>('/api/competencies/career')
      return resp.data.competencies
    },
  })
}

export function useCourseCompetencies(courseId: string | undefined) {
  return useQuery({
    queryKey: ['course-competencies', courseId],
    queryFn: async () => {
      const resp = await api.get<Competency[]>(`/api/competencies/course/${courseId}`)
      return resp.data
    },
    enabled: !!courseId,
  })
}

export function useAssignCompetencies() {
  const queryClient = useQueryClient()
  const { toast } = useToast()

  return useMutation({
    mutationFn: async ({ courseId, competencyIds }: { courseId: string; competencyIds: string[] }) => {
      const resp = await api.post(`/api/competencies/course/${courseId}/assign`, { competency_ids: competencyIds })
      return resp.data
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['course-competencies', variables.courseId] })
      queryClient.invalidateQueries({ queryKey: ['competencies'] })
      toast({ title: 'Competencias asignadas exitosamente' })
    },
    onError: (error) => {
      toast({ variant: 'destructive', title: 'Error al asignar competencias', description: getErrorMessage(error) })
    },
  })
}
