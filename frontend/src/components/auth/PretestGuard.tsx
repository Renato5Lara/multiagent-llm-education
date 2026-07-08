import type { ReactNode } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { useKnowledgeTestStatus } from '@/hooks/useKnowledgeTest'

/**
 * PretestGuard — puerta de la Ruta de Aprendizaje.
 *
 * Mientras el estudiante no complete la evaluación diagnóstica de conocimiento
 * (pre-test), no accede a la ruta. Fail-open deliberado: si el status no
 * responde o el banco no está seedeado, el flujo histórico queda intacto; y
 * un estudiante legacy con ruta previa nunca se bloquea (el backend ya lo
 * exime vía pretest_required=false).
 */
export default function PretestGuard({ children }: { children: ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>()
  const { data, isLoading, isError } = useKnowledgeTestStatus(courseId)

  if (isLoading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-neural-glow mx-auto mb-4" />
          <p className="text-neural-muted text-sm">Verificando tu evaluación diagnóstica...</p>
        </div>
      </div>
    )
  }

  if (isError || !data) {
    return <>{children}</>
  }

  if (data.bank_available && data.pretest_required) {
    return <Navigate to={`/estudiante/knowledge-test/${courseId}`} replace />
  }

  return <>{children}</>
}
