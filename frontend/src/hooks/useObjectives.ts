import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import type { LearningObjective, ObjectiveCreate, ObjectiveUpdate } from '@/types/course'
import { useToast } from '@/hooks/use-toast'

export function useObjectives(courseId: string | undefined) {
    return useQuery({
        queryKey: ['objectives', courseId],
        queryFn: async () => {
            const resp = await api.get<LearningObjective[]>(`/api/courses/${courseId}/objectives`)
            return resp.data
        },
        enabled: !!courseId,
    })
}

export function useCreateObjective() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ courseId, data }: { courseId: string; data: ObjectiveCreate }) => {
            const resp = await api.post<LearningObjective>(`/api/courses/${courseId}/objectives`, data)
            return resp.data
        },
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['objectives', variables.courseId] })
            toast({ title: 'Objetivo creado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al crear objetivo', description: getErrorMessage(error) })
        },
    })
}

export function useUpdateObjective() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ id, data }: { id: string; data: ObjectiveUpdate }) => {
            const resp = await api.put<LearningObjective>(`/api/objectives/${id}`, data)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['objectives'] })
            toast({ title: 'Objetivo actualizado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al actualizar objetivo', description: getErrorMessage(error) })
        },
    })
}

export function useDeleteObjective() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (id: string) => {
            await api.delete(`/api/objectives/${id}`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['objectives'] })
            toast({ title: 'Objetivo eliminado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al eliminar objetivo', description: getErrorMessage(error) })
        },
    })
}
