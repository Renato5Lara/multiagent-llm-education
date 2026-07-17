// Lista presentacional de eventos ya traducidos (traducirTraza) — extraída
// de AgentDecisionTimeline para que Modo Evidencia (StudentTrajectory,
// RFC-0007 §5) narre la MISMA traza con el mismo estilo, sin volver a
// pedirla por red (ya llega dentro de la trayectoria) ni duplicar el mapa
// de colores por agente.
import { Sparkles } from 'lucide-react'
import type { LiveDeliberationEvent } from '@/hooks/useLiveDeliberation'

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

interface DeliberationEventListProps {
  eventos: LiveDeliberationEvent[]
}

export function DeliberationEventList({ eventos }: DeliberationEventListProps) {
  if (eventos.length === 0) {
    return (
      <p className="text-sm text-neural-muted/60 text-center py-6">
        Todavía no hay decisiones registradas — aparecerán aquí en cuanto el sistema observe su primera evidencia real.
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
