import { cn } from '@/lib/utils'
import type { LearningJourneyStepType } from '@/types/learningJourney'
import { STEP_LABELS } from './journeyStepConfig'

interface Props {
  currentIndex: number
  totalSteps:   number
  currentType:  LearningJourneyStepType
  totalXp:      number
  xpFlash:      number | null
}

// Learning phase derived from progress percentage.
const PHASES: ReadonlyArray<{ threshold: number; label: string; color: string; barColor: string }> = [
  { threshold: 0.20, label: '🗺️ Explorando',     color: 'text-sky-600 dark:text-sky-400',         barColor: 'bg-sky-400 dark:bg-sky-600' },
  { threshold: 0.40, label: '🔍 Comprendiendo',   color: 'text-indigo-600 dark:text-indigo-400',   barColor: 'bg-indigo-400 dark:bg-indigo-600' },
  { threshold: 0.60, label: '🛠️ Aplicando',       color: 'text-teal-600 dark:text-teal-400',       barColor: 'bg-teal-400 dark:bg-teal-600' },
  { threshold: 0.80, label: '💡 Reflexionando',   color: 'text-amber-600 dark:text-amber-400',     barColor: 'bg-amber-400 dark:bg-amber-600' },
  { threshold: 1.01, label: '🎯 Evaluando',        color: 'text-emerald-600 dark:text-emerald-400', barColor: 'bg-emerald-400 dark:bg-emerald-600' },
]

function getPhase(pct: number) {
  return PHASES.find(p => pct < p.threshold) ?? PHASES[PHASES.length - 1]
}

export function JourneyProgress({ currentIndex, totalSteps, currentType, totalXp, xpFlash }: Props) {
  const pct   = totalSteps > 0 ? (currentIndex + 1) / totalSteps : 0
  const phase = getPhase(pct)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs gap-2">

        {/* Phase label + step type */}
        <div className="flex items-center gap-2 min-w-0">
          <span className={cn('font-bold truncate transition-colors duration-500', phase.color)}>
            {phase.label}
          </span>
          <span className="text-muted-foreground/50 hidden sm:inline">·</span>
          <span className="text-muted-foreground truncate hidden sm:inline">
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

      {/* Phase-colored progress bar */}
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
        <div
          className={cn('h-full rounded-full transition-all duration-500', phase.barColor)}
          style={{ width: `${pct * 100}%` }}
        />
      </div>
    </div>
  )
}
