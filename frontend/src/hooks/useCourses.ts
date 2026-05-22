import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import type { Course, CourseCreate, CourseUpdate, CourseListResponse, EnrollRequest } from '@/types/course'
import { useToast } from '@/hooks/use-toast'

export function useCourses(page = 1, size = 20) {
    return useQuery({
        queryKey: ['courses', { page, size }],
        queryFn: async () => {
            const resp = await api.get<CourseListResponse>('/api/courses', { params: { page, size } })
            return resp.data
        },
    })
}

export function useCourse(id: string | undefined) {
    return useQuery({
        queryKey: ['courses', id],
        queryFn: async () => {
            const resp = await api.get<Course>(`/api/courses/${id}`)
            return resp.data
        },
        enabled: !!id,
    })
}

export function useCreateCourse() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (data: CourseCreate) => {
            const resp = await api.post<Course>('/api/courses', data)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            toast({ title: 'Curso creado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al crear curso', description: getErrorMessage(error) })
        },
    })
}

export function useUpdateCourse() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ id, data }: { id: string; data: CourseUpdate }) => {
            const resp = await api.put<Course>(`/api/courses/${id}`, data)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            toast({ title: 'Curso actualizado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al actualizar curso', description: getErrorMessage(error) })
        },
    })
}

export function useDeleteCourse() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (id: string) => {
            const resp = await api.delete<Course>(`/api/courses/${id}`)
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            toast({ title: 'Curso archivado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al archivar curso', description: getErrorMessage(error) })
        },
    })
}

export function usePublishCourse() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (id: string) => {
            const resp = await api.post(`/api/courses/${id}/publish`)
            return resp.data
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            toast({ title: data.message || 'Curso publicado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al publicar', description: getErrorMessage(error) })
        },
    })
}

export function useEnrollStudents() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async ({ courseId, data }: { courseId: string; data: EnrollRequest }) => {
            const resp = await api.post(`/api/courses/${courseId}/enroll`, data)
            return resp.data
        },
        onSuccess: (data) => {
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            queryClient.invalidateQueries({ queryKey: ['enrollments'] })
            toast({
                title: 'Inscripción completada',
                description: `${data.success} estudiantes inscritos`,
            })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error en inscripción', description: getErrorMessage(error) })
        },
    })
}
