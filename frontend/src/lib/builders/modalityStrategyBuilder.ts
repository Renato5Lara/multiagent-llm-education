/**
 * Modality-Depth Matrix — D6.5.1
 *
 * Each modality produces a DIFFERENT pedagogical strategy, not just a
 * different component. The strategies differ in:
 *   - depth (how many concepts / examples)
 *   - rhythm (how steps are sequenced)
 *   - interaction type (image, video, analogy, prediction, practice)
 *   - pace (tight loops vs extended reading sequences)
 *
 * Visual      : minimal text · images · diagrams · tight loops
 * Reading     : full depth · analogies · long examples · reflective questions
 * Audio       : short summaries · video prompts · curiosity facts
 * Kinesthetic : prediction-first · mini activities · Code Lab
 */

import type { LearningJourneyStep, Phase5E } from '@/types/learningJourney'
import type { LearningModality }             from '@/types/modality'
import { createStep }                         from './stepFactory'
import {
  makeMicroQuestion,
  makeAnalogy,
  makeMiniActivity,
  makeKinestheticPrediction,
  makeCuriosity,
} from './interactiveStepFactory'
import { makeMediaPromptForced } from './mediaPromptFactory'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StrategyOptions {
  conceptPool:  ReadonlyArray<{ id: string; text: string }>
  examples:     ReadonlyArray<string>
  moduleTitle:  string
}

function p(i: number, halfLen: number): Phase5E {
  return i < halfLen ? 'explore' : 'explain'
}

// ── Visual ────────────────────────────────────────────────────────────────────
// Rhythm: concept → image → (repeat) — tight, visual loops
// Depth:  max 4 concepts, 1 example only — avoid overwhelming with text

function buildVisual({ conceptPool, examples, moduleTitle }: StrategyOptions): LearningJourneyStep[] {
  const steps: LearningJourneyStep[] = []
  const shown = conceptPool.slice(0, 4)          // cap text — visuals don't need all paragraphs
  const half  = Math.ceil(shown.length / 2)

  shown.forEach(({ id, text }, i) => {
    const ph = p(i, half)
    steps.push(createStep(id, 'concept', ph, { content: text, xpReward: 2 }))
    steps.push({
      ...makeMediaPromptForced(moduleTitle, text, i, 'image'),
      phase: ph,
    })
    // Every pair: a short reflective tap
    if ((i + 1) % 2 === 0) {
      steps.push({ ...makeMicroQuestion(i), phase: ph })
    }
  })

  // Single example — visual learners read it as a diagram reference
  if (examples[0]) {
    steps.push(createStep('example-0', 'example', 'explain', {
      content: examples[0], xpReward: 3,
    }))
  }

  return steps
}

// ── Reading ───────────────────────────────────────────────────────────────────
// Rhythm: 3 concepts → analogy → long example → micro-question
// Depth:  all concepts, all examples — maximum textual richness

function buildReading({ conceptPool, examples, moduleTitle }: StrategyOptions): LearningJourneyStep[] {
  const steps: LearningJourneyStep[] = []
  const half  = Math.ceil(conceptPool.length / 2)

  conceptPool.forEach(({ id, text }, i) => {
    const ph = p(i, half)
    steps.push(createStep(id, 'concept', ph, { content: text, xpReward: 2 }))

    // Every 3 concepts: analogy consolidates understanding, then a question
    if ((i + 1) % 3 === 0) {
      steps.push({ ...makeAnalogy(moduleTitle, i),   phase: ph })
      steps.push({ ...makeMicroQuestion(i + 200),    phase: ph })
    }
  })

  // All examples — reading learners benefit from varied, long examples
  examples.forEach((ex, i) => {
    steps.push(createStep(`example-${i}`, 'example', 'explain', {
      content: ex, xpReward: 3,
    }))
    // After every second example: reflective question
    if (i % 2 === 0) {
      steps.push({ ...makeMicroQuestion(i + 300), phase: 'explain' as Phase5E })
    }
  })

  return steps
}

// ── Audio ─────────────────────────────────────────────────────────────────────
// Rhythm: concept (key sentence) → video → curiosity (every pair)
// Depth:  max 4 concepts, 1 example — audio learners absorb narration, not walls of text

function buildAudio({ conceptPool, examples, moduleTitle }: StrategyOptions): LearningJourneyStep[] {
  const steps: LearningJourneyStep[]  = []
  const shown         = conceptPool.slice(0, 4)
  const half          = Math.ceil(shown.length / 2)
  let   curiosityCount = 0

  shown.forEach(({ id, text }, i) => {
    const ph = p(i, half)
    steps.push(createStep(id, 'concept', ph, { content: text, xpReward: 2 }))
    steps.push({
      ...makeMediaPromptForced(moduleTitle, text, i, 'video'),
      phase: ph,
    })
    // Curiosity after every pair — audio learners love surprising facts
    if ((i + 1) % 2 === 0) {
      steps.push({ ...makeCuriosity(moduleTitle, curiosityCount++), phase: ph })
    }
  })

  // One example — framed as a "case study to listen to"
  if (examples[0]) {
    steps.push(createStep('example-0', 'example', 'explain', {
      content: examples[0], xpReward: 3,
    }))
  }

  return steps
}

// ── Kinesthetic ───────────────────────────────────────────────────────────────
// Rhythm: prediction → concept → mini_activity → (repeat)
// Depth:  all concepts + 2 examples — each with hands-on activity
// Note:   Code Lab insertion for elaborate phase is handled by the orchestrator

function buildKinesthetic({ conceptPool, examples, moduleTitle }: StrategyOptions): LearningJourneyStep[] {
  const steps: LearningJourneyStep[] = []
  const half  = Math.ceil(conceptPool.length / 2)

  conceptPool.forEach(({ id, text }, i) => {
    const ph = p(i, half)
    // Prediction BEFORE concept — kinesthetic learners need to act before reading
    steps.push({ ...makeKinestheticPrediction(moduleTitle, i), phase: ph })
    steps.push(createStep(id, 'concept', ph, { content: text, xpReward: 2 }))
    steps.push({ ...makeMiniActivity(i), phase: ph })
  })

  // Two practical examples, each followed by an activity (reinforce by doing)
  examples.slice(0, 2).forEach((ex, i) => {
    steps.push(createStep(`example-${i}`, 'example', 'explain', {
      content: ex, xpReward: 3,
    }))
    steps.push({ ...makeMiniActivity(i + 50), phase: 'explain' as Phase5E })
  })

  return steps
}

// ── Default ───────────────────────────────────────────────────────────────────
// Mixed strategy — used when modality is unknown; mirrors the pre-D6.5 behavior

function buildDefault({ conceptPool, examples, moduleTitle }: StrategyOptions): LearningJourneyStep[] {
  const steps: LearningJourneyStep[] = []
  const half          = Math.ceil(conceptPool.length / 2)
  let   curiosityCount = 0
  const phaseLen      = Math.max(conceptPool.length, examples.length)

  for (let i = 0; i < phaseLen; i++) {
    if (i < conceptPool.length) {
      const ph         = p(i, half)
      const { id, text } = conceptPool[i]
      steps.push(createStep(id, 'concept', ph, { content: text, xpReward: 2 }))

      if ((i + 1) % 2 === 0) {
        steps.push({ ...makeCuriosity(moduleTitle, curiosityCount++), phase: ph })
      }
      switch (i % 3) {
        case 0: steps.push({ ...makeMicroQuestion(i),          phase: ph }); break
        case 1: steps.push({ ...makeAnalogy(moduleTitle, i),   phase: ph }); break
      }
    }

    if (i < examples.length) {
      steps.push(createStep(`example-${i}`, 'example', 'explain', {
        content: examples[i], xpReward: 3,
      }))
      steps.push({ ...makeMiniActivity(i), phase: 'explain' as Phase5E })
    }
  }

  return steps
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Returns the Explore + Explain phase steps for the given modality strategy.
 * The Elaborate and Evaluate phases are handled by the orchestrator.
 */
export function buildExploreExplainSteps(
  modality:    LearningModality | undefined,
  conceptPool: ReadonlyArray<{ id: string; text: string }>,
  examples:    ReadonlyArray<string>,
  moduleTitle: string,
): LearningJourneyStep[] {
  const opts: StrategyOptions = { conceptPool, examples, moduleTitle }
  switch (modality) {
    case 'visual':      return buildVisual(opts)
    case 'reading':     return buildReading(opts)
    case 'audio':       return buildAudio(opts)
    case 'kinesthetic': return buildKinesthetic(opts)
    default:            return buildDefault(opts)
  }
}
