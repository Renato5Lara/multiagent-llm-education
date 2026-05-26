import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '@/lib/api'
import { getErrorMessage } from '@/lib/errors'
import { useToast } from '@/hooks/use-toast'
import type { CycleInfo, InstitutionalCourse, TeacherAssignment } from '@/types/curriculum'

export function useCurriculumCycles() {
    return useQuery({
        queryKey: ['curriculum', 'cycles'],
        queryFn: async () => {
            const resp = await api.get<CycleInfo[]>('/api/curriculum/cycles')
            return resp.data
        },
        staleTime: 5 * 60 * 1000,
    })
}

export function useCurriculumCourses(cycle?: number) {
    return useQuery({
        queryKey: ['curriculum', 'courses', cycle],
        queryFn: async () => {
            const params = cycle ? { cycle } : {}
            const resp = await api.get<InstitutionalCourse[]>('/api/curriculum/courses', { params })
            return resp.data
        },
        staleTime: 5 * 60 * 1000,
    })
}

export function useTeacherAssignments() {
    return useQuery({
        queryKey: ['curriculum', 'teacher-assignments'],
        queryFn: async () => {
            const resp = await api.get<TeacherAssignment[]>('/api/curriculum/teacher-assignments')
            return resp.data
        },
    })
}

export function useAssignTeacherCourse() {
    const queryClient = useQueryClient()
    const { toast } = useToast()

    return useMutation({
        mutationFn: async (institutionalCourseId: string) => {
            const resp = await api.post<TeacherAssignment>('/api/curriculum/teacher-assignments', {
                institutional_course_id: institutionalCourseId,
            })
            return resp.data
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['curriculum', 'teacher-assignments'] })
            queryClient.invalidateQueries({ queryKey: ['courses'] })
            toast({ title: 'Curso asignado exitosamente' })
        },
        onError: (error) => {
            toast({ variant: 'destructive', title: 'Error al asignar curso', description: getErrorMessage(error) })
        },
    })
}
