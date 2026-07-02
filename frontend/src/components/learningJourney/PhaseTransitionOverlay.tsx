import { useEffect } from 'react'
import { cn } from '@/lib/utils'
import { PHASE_5E_CONFIG, PHASE_5E_ORDER } from './journeyStepConfig'
import type { Phase5E } from '@/types/learningJourney'

interface Props {
  phase:      Phase5E | null
  onDismiss:  () => void
  /** ms antes del auto-dismiss — default 2600 */
  duration?:  number
}

// Gradiente de fondo por fase — referencia: dark palette Neural Swarm
const PHASE_BG: Record<Phase5E, string> = {
  engage:    'bg-gradient-to-br from-amber-950   via-stone-950   to-slate-950',
  explore:   'bg-gradient-to-br from-sky-950     via-cyan-950    to-slate-950',
  explain:   'bg-gradient-to-br from-indigo-950  via-violet-950  to-slate-950',
  elaborate: 'bg-gradient-to-br from-teal-950    via-emerald-950 to-slate-950',
  evaluate:  'bg-gradient-to-br from-emerald-950 via-green-950   to-slate-950',
}

// Línea de acento superior e inferior (thin accent bar — referencia: Swarm Monitor)
const PHASE_ACCENT: Record<Phase5E, string> = {
  engage:    'bg-amber-400',
  explore:   'bg-sky-400',
  explain:   'bg-indigo-400',
  elaborate: 'bg-teal-400',
  evaluate:  'bg-emerald-400',
}

// Feed de agentes por fase — evoca "Agent Decision Stream" del Swarm Monitor
// No menciona arquitectura técnica; habla en lenguaje del aprendizaje.
const PHASE_AGENTS: Record<Phase5E, readonly string[]> = {
  engage: [
    '[CORE]  Preparando detonador de curiosidad...',
    '[S-01]  Rastreo cognitivo activado',
  ],
  explore: [
    '[S-02]  Análisis de intuición previa completo',
    '[CORE]  Explorando patrones de conocimiento',
  ],
  explain: [
    '[CORE]  Construyendo modelo conceptual adaptado',
    '[S-04]  Sincronizando explicación con tu perfil',
  ],
  elaborate: [
    '[S-01]  Vinculando concepto a contexto real',
    '[S-03]  Calibrando nivel de práctica',
  ],
  evaluate: [
    '[CORE]  Midiendo comprensión final',
    '[S-04]  Generando evaluación adaptativa',
  ],
}

/**
 * PhaseTransitionOverlay — Sprint 2.1 (rediseño visual)
 *
 * Hace del cambio de fase 5E un momento de aventura, no un cambio de tarjeta.
 * Referencia visual: pantallas "Swarm Monitor" y "Contenido Adaptativo".
 *
 * Estructura:
 *   • Fondo glassmorphism oscuro con gradiente de la fase
 *   • Barra de acento superior (thin accent bar) con color de la fase
 *   • Emoji grande animado con float
 *   • Número de etapa + nombre en grande + frase de transición
 *   • Feed de agentes (evoca Agent Decision Stream del Swarm Monitor)
 *   • Auto-dismiss o click para adelantar
 */
export function PhaseTransitionOverlay({ phase, onDismiss, duration = 2600 }: Props) {
  useEffect(() => {
    if (!phase) return
    const timer = setTimeout(onDismiss, duration)
    return () => clearTimeout(timer)
  }, [phase, onDismiss, duration])

  if (!phase) return null

  const config = PHASE_5E_CONFIG[phase]
  const number = PHASE_5E_ORDER.indexOf(phase) + 1

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Entrando a la etapa: ${config.label}`}
      onClick={onDismiss}
      className={cn(
        'fixed inset-0 z-50 flex flex-col items-center justify-center cursor-pointer',
        PHASE_BG[phase],
        'animate-in fade-in duration-400',
      )}
    >
      {/* Accent bar top */}
      <div className={cn('absolute top-0 left-0 right-0 h-[3px]', PHASE_ACCENT[phase])} />

      {/* Main content */}
      <div className="flex flex-col items-center gap-6 px-8 max-w-xs text-center select-none">

        {/* Animated phase emoji */}
        <span
          className="text-8xl leading-none"
          style={{ animation: 'float 2s ease-in-out infinite' }}
          aria-hidden="true"
        >
          {config.emoji}
        </span>

        {/* Stage label + phase name */}
        <div className="space-y-2">
          <p className="text-[11px] font-mono font-semibold tracking-[0.3em] uppercase text-white/40">
            Etapa {number} de {PHASE_5E_ORDER.length}
          </p>
          <h2 className={cn('text-5xl font-extrabold tracking-tight leading-none', config.color)}>
            {config.label}
          </h2>
        </div>

        {/* Transition phrase */}
        <p className="text-base text-white/70 leading-relaxed font-medium">
          {config.transition}
        </p>

        {/* Agent Decision Stream mini-feed — referencia: Swarm Monitor */}
        <div
          className="w-full rounded-xl border border-white/[0.08] bg-white/[0.04] px-4 py-3.5 space-y-2 text-left"
          aria-label="Actividad del enjambre"
        >
          <p className="text-[9px] font-mono font-bold tracking-[0.3em] text-white/30 uppercase mb-1">
            Enjambre Neural · en proceso
          </p>
          {PHASE_AGENTS[phase].map((msg, i) => (
            <p key={i} className="text-[11px] font-mono text-white/40 leading-relaxed">
              {msg}
            </p>
          ))}
        </div>

        {/* Dismiss hint */}
        <p className="text-[10px] font-mono text-white/20 tracking-widest uppercase mt-2">
          Toca para continuar
        </p>
      </div>

      {/* Accent bar bottom */}
      <div className={cn('absolute bottom-0 left-0 right-0 h-[3px] opacity-40', PHASE_ACCENT[phase])} />
    </div>
  )
}
