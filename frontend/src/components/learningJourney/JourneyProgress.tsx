import { cn } from '@/lib/utils'
import type { LearningJourneyStepType, Phase5E } from '@/types/learningJourney'
import { STEP_LABELS, PHASE_5E_CONFIG } from './journeyStepConfig'

interface Props {
  currentIndex: number
  totalSteps:   number
  currentType:  LearningJourneyStepType
  totalXp:      number
  xpFlash:      number | null
  // Sprint 2.1 — fase 5E activa: colorea la barra para que este componente
  // acompañe al narrador pedagógico (FiveEProgressBar) en vez de competir
  // con él. Antes tenía su propio sistema de fases por porcentaje — eliminado
  // para que exista UN único narrador del proceso pedagógico.
  phase?: Phase5E
}

export function JourneyProgress({ currentIndex, totalSteps, currentType, totalXp, xpFlash, phase }: Props) {
  const pct      = totalSteps > 0 ? (currentIndex + 1) / totalSteps : 0
  const barColor = phase ? PHASE_5E_CONFIG[phase].barColor : 'bg-violet-400 dark:bg-violet-600'

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs gap-2">

        {/* Current step type — the phase itself is narrated by FiveEProgressBar */}
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-muted-foreground truncate font-medium">
            {STEP_LABELS[currentType]}
          </span>
        </div>

        {/* Right: XP flash + total + step count */}
        <div className="flex items-center gap-3 shrink-0">
          {xpFlash !== null && (
            <span className={cn(
              'font-bold text-amber-500',
              'animate-in fade-in slide-in-from-right-1 duration-200',
            )}>
              +{xpFlash} XP ✨
            </span>
          )}
          {totalXp > 0 && (
            <span className="font-mono text-amber-600 dark:text-amber-400 font-semibold">
              ⭐ {totalXp}
            </span>
          )}
          <span className="text-muted-foreground tabular-nums font-medium">
            {currentIndex + 1}<span className="text-muted-foreground/50"> / </span>{totalSteps}
          </span>
        </div>
      </div>

      {/* Progress bar — colored by the active 5E phase */}
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
        <div
          className={cn('h-full rounded-full transition-all duration-500', barColor)}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  )
}
