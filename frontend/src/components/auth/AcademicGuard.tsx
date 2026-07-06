import { Navigate, Outlet } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useActiveExperience } from '@/hooks/useStudent'

/**
 * AcademicGuard — puerta de la experiencia del estudiante.
 *
 * Ya no depende del ciclo (LMS). Pregunta al dominio: ¿cuál es el estado de la
 * experiencia activa? Si el estudiante aún no la inició (NOT_STARTED), lo envía
 * al onboarding; en cualquier otro estado, lo deja continuar.
 */
export default function AcademicGuard() {
  const { data: experience, isLoading, isError } = useActiveExperience()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <Loader2 className="h-12 w-12 animate-spin text-primary mx-auto mb-4" />
          <p className="text-muted-foreground text-sm">Preparando tu experiencia...</p>
        </div>
      </div>
    )
  }

  // Fail-open: si no pudimos resolver la experiencia, no atrapamos al estudiante.
  if (isError) {
    return <Outlet />
  }

  if (experience?.state === 'NOT_STARTED') {
    return <Navigate to="/estudiante/onboarding" replace />
  }

  return <Outlet />
}
