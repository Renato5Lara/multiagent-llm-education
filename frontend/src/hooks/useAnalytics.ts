import { useQuery } from '@tanstack/react-query'
import api from '@/lib/api'
import { useAuthStore } from '@/stores/authStore'
import type { DocenteAnalyticsResponse } from '@/types/analytics'

const dashboardKey = ['analytics', 'dashboard']

export function useCourseAccess(courseId: string | undefined) {
    return useQuery({
        queryKey: ['analytics', 'course-access', courseId],
        queryFn: async () => {
            const resp = await api.get(`/api/analytics/course-access/${courseId}`)
            return resp.data
        },
        enabled: !!courseId,
        staleTime: 30 * 1000,
    })
}

export function useCurriculumStatus() {
    return useQuery({
        queryKey: ['analytics', 'curriculum-status'],
        queryFn: async () => {
            const resp = await api.get('/api/analytics/curriculum-status')
            return resp.data
        },
        staleTime: 30 * 1000,
    })
}

export function useDocenteAnalytics() {
    const role = useAuthStore((s) => s.user?.role) || 'docente'
    return useQuery({
        queryKey: [...dashboardKey, role],
        queryFn: async () => {
            const resp = await api.get<DocenteAnalyticsResponse>('/api/analytics/dashboard')
            return resp.data
        },
        staleTime: 60 * 1000,
    })
}
