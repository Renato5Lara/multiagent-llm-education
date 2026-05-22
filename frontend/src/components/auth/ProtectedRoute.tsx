import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useAuthContext } from '@/providers/AuthProvider'
import type { UserRole } from '@/types/auth'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
}

export default function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { isReady, isValidating } = useAuthContext()
  const { isAuthenticated, user } = useAuthStore()
  const location = useLocation()

  if (!isReady || isValidating) {
    return <LoadingScreen />
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const roleHome = `/${user.role === 'admin' ? 'admin' : user.role}`
    return <Navigate to={roleHome} replace />
  }

  return <Outlet />
}

export function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
        <p className="text-muted-foreground text-sm">Cargando...</p>
      </div>
    </div>
  )
}
