import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import api from '@/lib/api'

const ONBOARDING_ROUTES = ['/estudiante/onboarding']

export default function AcademicGuard() {
  const { user, isAuthenticated } = useAuthStore()
  const location = useLocation()

  const isOnboardingRoute = ONBOARDING_ROUTES.includes(location.pathname)

  const { data: onboardingStatus, isLoading, isError } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: async () => {
      const resp = await api.get('/api/students/onboarding/status')
      return resp.data as { has_cycle: boolean; current_cycle: number | null; onboarding_completed: boolean }
    },
    enabled: isAuthenticated && user?.role === 'estudiante',
    retry: false,
    staleTime: 30000,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground text-sm">Verificando estado académico...</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return <Outlet />
  }

  const needsOnboarding = !onboardingStatus?.has_cycle && !user?.current_cycle

  if (needsOnboarding && !isOnboardingRoute) {
    return <Navigate to="/estudiante/onboarding" replace />
  }

  return <Outlet />
}
