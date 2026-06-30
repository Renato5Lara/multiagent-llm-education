import type {
  LearningJourneyStep,
  LearningJourneyStepType,
  Phase5E,
} from '@/types/learningJourney'

/**
 * Single source of truth for step creation.
 * Eliminates the scattered `phase: currentPhase` pattern across the builder.
 */
export function createStep(
  id:       string,
  type:     LearningJourneyStepType,
  phase:    Phase5E,
  options?: Partial<Omit<LearningJourneyStep, 'id' | 'type' | 'phase'>>,
): LearningJourneyStep {
  return { id, type, phase, ...options }
}
