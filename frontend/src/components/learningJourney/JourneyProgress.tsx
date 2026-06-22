import { Progress } from '@/components/ui/progress'
import { cn } from '@/lib/utils'
import type { LearningJourneyStepType } from '@/types/learningJourney'

export const STEP_LABELS: Record<LearningJourneyStepType, string> = {
  // Existing
  did_you_know:    '💡 Curiosidad',
  prior_knowledge: '🧭 Punto de partida',
  concept:         '📖 Concepto',
  question:        '🔎 Pregunta',
  example:         '🧠 Ejemplo',
  challenge:       '🎯 Reto',
  application:     '🚀 Aplicación',
  reflection:      '🧘 Reflexión',
  evaluation:      '📋 Evaluación',
  // Sprint L3
  micro_question:  '❓ Pregunta rápida',
  prediction:      '🔮 Predicción',
  mini_activity:   '✏️ Mini actividad',
  curiosity:       '✨ Curiosidad',
  analogy:         '🌀 Analogía',
  media_prompt:    '🎨 Recurso multimedia',
}

// Color accent per step type — used by cards and progress indicator
export const STEP_COLORS: Record<LearningJourneyStepType, string> = {
  // Existing
  did_you_know:    'amber',
  prior_knowledge: 'sky',
  concept:         'indigo',
  question:        'violet',
  example:         'blue',
  challenge:       'orange',
  application:     'emerald',
  reflection:      'gray',
  evaluation:      'purple',
  // Sprint L3
  micro_question:  'cyan',
  prediction:      'fuchsia',
  mini_activity:   'teal',
  curiosity:       'yellow',
  analogy:         'green',
  media_prompt:    'rose',
}

interface Props {
  currentIndex: number
  totalSteps:   number
  currentType:  LearningJourneyStepType
  totalXp:      number
  xpFlash:      number | null
}

/**
 * JourneyProgress — Sprint J1
 *
 * Barra de progreso del Learning Journey. Muestra:
 * - Tipo del paso actual (con label semántico)
 * - Contador N / Total
 * - XP acumulado + flash animado al ganar XP
 * - Barra lineal de progreso
 */
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
