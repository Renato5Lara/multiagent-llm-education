import { cn } from '@/lib/utils'
import { PHASE_5E_CONFIG, PHASE_5E_ORDER, resolveStepPhase } from './journeyStepConfig'
import type { LearningJourneyStep, Phase5E } from '@/types/learningJourney'

interface Props {
  steps:        LearningJourneyStep[]
  currentIndex: number
}

type PhaseStatus = 'completed' | 'active' | 'pending'

// Accent colors for the active pill border + shadow — matches PHASE_5E_CONFIG
const PHASE_ACTIVE_RING: Record<Phase5E, string> = {
  engage:    'border-amber-400/70  dark:border-amber-500/50  shadow-amber-200/30  dark:shadow-amber-900/30',
  explore:   'border-sky-400/70    dark:border-sky-500/50    shadow-sky-200/30    dark:shadow-sky-900/30',
  explain:   'border-indigo-400/70 dark:border-indigo-500/50 shadow-indigo-200/30 dark:shadow-indigo-900/30',
  elaborate: 'border-teal-400/70   dark:border-teal-500/50   shadow-teal-200/30   dark:shadow-teal-900/30',
  evaluate:  'border-emerald-400/70 dark:border-emerald-500/50 shadow-emerald-200/30 dark:shadow-emerald-900/30',
}

const PHASE_ACTIVE_BG: Record<Phase5E, string> = {
  engage:    'bg-amber-50/70  dark:bg-amber-500/10',
  explore:   'bg-sky-50/70    dark:bg-sky-500/10',
  explain:   'bg-indigo-50/70 dark:bg-indigo-500/10',
  elaborate: 'bg-teal-50/70   dark:bg-teal-500/10',
  evaluate:  'bg-emerald-50/70 dark:bg-emerald-500/10',
}

/**
 * FiveEProgressBar — Sprint 2.1 (rediseño visual)
 *
 * Hace visible el modelo pedagógico 5E como recorrido narrado.
 * Referencia visual: tab navigation de "Contenido Adaptativo" (Theory | Diagram | Video | Code)
 * aplicada al recorrido 5E: Descubre → Explora → Comprende → Practica → Demuestra.
 *
 * Mejoras vs versión anterior:
 *   • Pills más altas (py-2 vs py-1.5) — mejor jerarquía táctil
 *   • Label siempre visible (sin `hidden sm:inline`)
 *   • Phase activa: borde coloreado + fondo sutil + sombra suave
 *   • Frase de transición con animación y tamaño más legible
 */
export function FiveEProgressBar({ steps, currentIndex }: Props) {
  const step = steps[currentIndex]
  if (!step) return null

  const currentPhase: Phase5E = resolveStepPhase(step)
  const currentOrder = PHASE_5E_ORDER.indexOf(currentPhase)

  function statusOf(phase: Phase5E): PhaseStatus {
    const order = PHASE_5E_ORDER.indexOf(phase)
    if (order < currentOrder) return 'completed'
    if (order === currentOrder) return 'active'
    return 'pending'
  }

  const transition = PHASE_5E_CONFIG[currentPhase].transition

  return (
    <div className="space-y-2.5">
      {/* Phase pills */}
      <div className="flex items-center gap-1">
        {PHASE_5E_ORDER.map((phase, i) => {
          const config = PHASE_5E_CONFIG[phase]
          const status = statusOf(phase)
          const isActive = status === 'active'

          return (
            <div key={phase} className="flex items-center gap-1 min-w-0 flex-1">
              <div
                className={cn(
                  'flex items-center justify-center gap-1.5 w-full rounded-lg px-2 py-2 border transition-all duration-500',
                  // Active: colored border + subtle bg + shadow
                  isActive && [
                    PHASE_ACTIVE_RING[phase],
                    PHASE_ACTIVE_BG[phase],
                    'shadow-sm',
                  ],
                  // Completed: muted
                  status === 'completed' && 'border-transparent bg-gray-100/50 dark:bg-white/[0.04]',
                  // Pending: faded
                  status === 'pending'   && 'border-transparent opacity-35',
                )}
              >
                <span className={cn(
                  'text-xs leading-none select-none',
                  status === 'pending' && 'grayscale',
                )}>
                  {status === 'completed' ? '✓' : config.emoji}
                </span>
                <span className={cn(
                  'text-[10px] font-mono font-semibold tracking-wide uppercase truncate',
                  isActive             && config.color,
                  status === 'completed' && 'text-muted-foreground',
                  status === 'pending'   && 'text-muted-foreground',
                )}>
                  {config.label}
                </span>
              </div>
              {i < PHASE_5E_ORDER.length - 1 && (
                <span className="text-muted-foreground/25 text-[10px] shrink-0 select-none">→</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Contextual transition phrase — re-animates on phase change, slightly larger */}
      <p
        key={currentPhase}
        className={cn(
          'text-[11px] italic text-center leading-relaxed',
          'animate-in fade-in slide-in-from-bottom-1 duration-500',
          PHASE_5E_CONFIG[currentPhase].color,
        )}
      >
        {transition}
      </p>
    </div>
  )
}
