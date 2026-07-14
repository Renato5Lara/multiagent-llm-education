// Dashboard de investigación (Pilar 5) — la MISMA narración en lenguaje
// natural que ya usa la espera en vivo del diagnóstico (useLiveDeliberation),
// ahora persistente: la traza completa de la sesión del estudiante, leída
// una sola vez (sin sondeo, la petición ya terminó hace tiempo). Nunca texto
// de relleno — cada línea viene de un Domain Event real ya persistido
// (RFC-0007 §2.1), la misma fuente que RuntimeConsole usa para el docente
// en vocabulario técnico crudo; esta es la traducción a lenguaje natural,
// nunca una segunda fuente de datos.

import { Loader2, Sparkles } from 'lucide-react'
import { useRuntimeTrace } from '@/hooks/useRuntimeTrace'
import { traducirTraza } from '@/hooks/useLiveDeliberation'

const AGENT_DOT: Record<string, string> = {
  'Agente Diagnóstico':  'bg-neural-glow',
  'Agente Perfil':       'bg-purple-400',
  'Agente Adaptación':   'bg-violet-400',
  'Agente Tutor':        'bg-orange-300',
  'Agente Remediación':  'bg-amber-400',
  'Agente Orientador':   'bg-cyan-300',
  'Agente Evaluador':    'bg-emerald-400',
  'Agente Validación':   'bg-teal-300',
  'Agente Modelo':       'bg-pink-300',
  'Motor de Consenso':   'bg-neural-pulse',
  'Plataforma':          'bg-white/30',
}

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

  if (eventos.length === 0) {
    return (
      <p className="text-sm text-neural-muted/60 text-center py-6">
        Todavía no hay decisiones registradas — aparecerán aquí en cuanto el sistema observe tu primera evidencia real.
      </p>
    )
  }

  return (
    <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
      {eventos.map(ev => (
        <div
          key={ev.key}
          className={`flex items-start gap-2.5 rounded-lg px-3 py-2 ${
            ev.isConsensus ? 'bg-neural-pulse/[0.06] border border-neural-pulse/15' : ''
          }`}
        >
          <span
            className={`mt-1.5 inline-flex rounded-full h-1.5 w-1.5 shrink-0 ${AGENT_DOT[ev.agent] ?? 'bg-neural-glow'}`}
          />
          <p className="text-sm text-neural-text/80 leading-snug">
            <span className="text-neural-glow/70 font-mono text-[10px] uppercase mr-1.5 tracking-wide">
              {ev.agent}
            </span>
            {ev.isConsensus && <Sparkles className="inline h-3 w-3 text-neural-pulse mr-1 -mt-0.5" />}
            {ev.text}
          </p>
        </div>
      ))}
    </div>
  )
}
