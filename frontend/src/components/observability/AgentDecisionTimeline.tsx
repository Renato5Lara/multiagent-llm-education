// Dashboard de investigación (Pilar 5) — la MISMA narración en lenguaje
// natural que ya usa la espera en vivo del diagnóstico (useLiveDeliberation),
// ahora persistente: la traza completa de la sesión del estudiante, leída
// una sola vez (sin sondeo, la petición ya terminó hace tiempo). Nunca texto
// de relleno — cada línea viene de un Domain Event real ya persistido
// (RFC-0007 §2.1), la misma fuente que RuntimeConsole usa para el docente
// en vocabulario técnico crudo; esta es la traducción a lenguaje natural,
// nunca una segunda fuente de datos. El render en sí vive en
// DeliberationEventList (reutilizado también por Modo Evidencia, RFC-0007 §5,
// que ya trae la traza dentro de la trayectoria y no necesita este fetch).

import { Loader2 } from 'lucide-react'
import { useRuntimeTrace } from '@/hooks/useRuntimeTrace'
import { traducirTraza } from '@/hooks/useLiveDeliberation'
import { DeliberationEventList } from './DeliberationEventList'

interface AgentDecisionTimelineProps {
  sessionId: string | undefined
}

export function AgentDecisionTimeline({ sessionId }: AgentDecisionTimelineProps) {
  const { data, isLoading, isError } = useRuntimeTrace(sessionId)
  const eventos = traducirTraza(data)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 py-6 justify-center text-sm text-neural-muted">
        <Loader2 className="h-4 w-4 animate-spin" /> Leyendo la traza real de tu sesión…
      </div>
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-neural-muted/60 text-center py-6">
        No se pudo leer la traza de esta sesión todavía.
      </p>
    )
  }

  return <DeliberationEventList eventos={eventos} />
}
