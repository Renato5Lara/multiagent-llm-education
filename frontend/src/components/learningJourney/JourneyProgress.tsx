import { Progress } from '@/components/ui/progress'
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

export function JourneyProgress({ currentIndex, totalSteps, currentType, totalXp, xpFlash }: Props) {
  const pct = totalSteps > 0 ? ((currentIndex + 1) / totalSteps) * 100 : 0

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-muted-foreground">
          {STEP_LABELS[currentType]}
        </span>

        <div className="flex items-center gap-3">
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
          <span className="text-muted-foreground tabular-nums">
            {currentIndex + 1} / {totalSteps}
          </span>
        </div>
      </div>

      <Progress value={pct} className="h-1.5 transition-all duration-500" />
    </div>
  )
}
