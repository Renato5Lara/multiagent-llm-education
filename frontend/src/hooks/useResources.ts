import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api, { getErrorMessage } from '@/lib/api'
import type { Resource, ResourceObjectiveAssociation } from '@/types/resource'
import { useToast } from '@/hooks/use-toast'

export function useResources(courseId: string | undefined) {
    return useQuery({
        queryKey: ['resources', courseId],
        queryFn: async () => {
            const resp = await api.get<Resource[]>(`/api/courses/${courseId}/resources`)
            return resp.data
        },
        enabled: !!courseId,
    })
}

export function useUploadResource() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ courseId, file }: { courseId: string; file: File }) => {
            const formData = new FormData()
            formData.append('file', file)
            const resp = await api.post<Resource>(`/api/courses/${courseId}/resources`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' },
            })
            return resp.data
        },
        onSuccess: (_data, variables) => {
            queryClient.invalidateQueries({ queryKey: ['resources', variables.courseId] })
            toast({ title: 'Recurso subido exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al subir recurso', description: getErrorMessage(error) })
        },
    })
}

export function useDeleteResource() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (resourceId: string) => {
            await api.delete(`/api/resources/${resourceId}`)
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['resources'] })
            toast({ title: 'Recurso eliminado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al eliminar recurso', description: getErrorMessage(error) })
        },
    })
}

export function useAssociateObjectives() {
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ resourceId, data }: { resourceId: string; data: ResourceObjectiveAssociation }) => {
            const resp = await api.post(`/api/resources/${resourceId}/objectives`, data)
            return resp.data
        },
        onSuccess: () => {
            toast({ title: 'Objetivos asociados exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al asociar objetivos', description: getErrorMessage(error) })
        },
    })
}
