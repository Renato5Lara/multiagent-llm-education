import { cn } from '@/lib/utils'
import { LearningJourneyStep } from './LearningJourneyStep'
import type { LearningJourneyStep as StepData, Phase5E } from '@/types/learningJourney'
import type { LearningModality } from '@/types/modality'

// D6.4 — Wraps LearningJourneyStep with a 5E phase badge + modality indicator.
// The badge is a lightweight context cue for the student, not a heavy decorator.

const PHASE_CONFIG: Record<Phase5E, { label: string; emoji: string; color: string }> = {
  engage:    { label: 'Engage',    emoji: '⚡', color: 'text-amber-400/80'   },
  explore:   { label: 'Explore',   emoji: '🔍', color: 'text-sky-400/80'     },
  explain:   { label: 'Explain',   emoji: '📖', color: 'text-indigo-400/80'  },
  elaborate: { label: 'Elaborate', emoji: '🛠️', color: 'text-teal-400/80'   },
  evaluate:  { label: 'Evaluate',  emoji: '🎯', color: 'text-emerald-400/80' },
}

interface Props {
  step:       StepData
  modality?:  LearningModality
  onComplete: () => void
  onXp:       (amount: number) => void
}

export function MultimodalRenderer({ step, modality, onComplete, onXp }: Props) {
  const phaseConfig = step.phase ? PHASE_CONFIG[step.phase] : null

  return (
    <div className="space-y-1.5">
      {phaseConfig && (
        <div className="flex items-center gap-1.5 px-1">
          <span className={cn('text-[10px] font-mono font-semibold tracking-widest uppercase', phaseConfig.color)}>
            {phaseConfig.emoji} {phaseConfig.label}
          </span>
          {modality && (
            <span className="text-[10px] text-neural-muted/40 font-mono">
              · personalizado
            </span>
          )}
        </div>
      )}
      <LearningJourneyStep step={step} onComplete={onComplete} onXp={onXp} />
    </div>
  )
}
