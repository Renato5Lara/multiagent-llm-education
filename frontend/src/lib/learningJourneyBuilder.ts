/**
 * LearningJourney Builder — Orchestrator
 *
 * Responsibilities: personalization config, content pool extraction,
 * phase sequencing, and final journey assembly.
 *
 * All step creation logic lives in lib/builders/:
 *   stepFactory         — createStep() helper
 *   codeLabSelector     — module_id → Code Lab slug
 *   mediaPromptFactory  — image/video prompt steps
 *   interactiveStepFactory — interactive steps + modality picker
 */
import type {
  LearningJourney,
  LearningJourneyStep,
  MicroQuestionMeta,
  PredictionMeta,
  MiniActivityMeta,
  AnalogyMeta,
  MediaPromptMeta,
  CuriosityMeta,
  InteractivePracticeMeta,
  Phase5E,
} from '@/types/learningJourney'
import type { LearningModality } from '@/types/modality'
import type {
  EngagementSession,
  EngagementResourceType,
} from '@/types/engagement'
import type { ModuleOrchestrationResponse, ConceptBlock } from '@/types/pedagogy'

import { createStep }                  from './builders/stepFactory'
import { getCodeLabSlug }              from './builders/codeLabSelector'
import { buildExploreExplainSteps }    from './builders/modalityStrategyBuilder'
import {
  makePrediction,
  makeKinestheticPrediction,
} from './builders/interactiveStepFactory'

// Re-export for consumers that imported from this module in D6
export type { LearningModality }

// ── Depth configuration ───────────────────────────────────────────────────────

type KnowledgeLevel = 'never_seen' | 'heard_about_it' | 'know_a_bit' | 'know_well'

function readKnowledgeLevel(sessionId: string): KnowledgeLevel | null {
  try {
    const v = sessionStorage.getItem(`engage:knowledge_level:${sessionId}`)
    if (v === 'never_seen' || v === 'heard_about_it' || v === 'know_a_bit' || v === 'know_well') return v
    return null
  } catch {
    return null
  }
}

interface DepthConfig {
  maxIntroParagraphs:       number
  maxExplanationParagraphs: number
  maxExamples:              number
  maxMisconceptions:        number
}

function getDepthConfig(level: KnowledgeLevel | null): DepthConfig {
  switch (level) {
    case 'never_seen':
    case 'heard_about_it':
      return { maxIntroParagraphs: Infinity, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity }
    case 'know_a_bit':
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 4, maxExamples: Infinity, maxMisconceptions: 2 }
    case 'know_well':
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 2, maxExamples: Infinity, maxMisconceptions: 1 }
    default:
      return { maxIntroParagraphs: 2, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity }
  }
}

// ── ConceptBlock modality config ──────────────────────────────────────────────

interface ConceptBlockConfig {
  maxBlocks:        number   // how many LLM concept_blocks to show
  forcePrediction:  boolean  // add kinesthetic prediction before each block
  maxMisconceptions: number  // how many misconceptions in Evaluate
}

function getConceptBlockConfig(modality: LearningModality | undefined): ConceptBlockConfig {
  switch (modality) {
    case 'visual':
      return { maxBlocks: 4,       forcePrediction: false, maxMisconceptions: 1 }
    case 'reading':
      return { maxBlocks: Infinity, forcePrediction: false, maxMisconceptions: Infinity }
    case 'audio':
      return { maxBlocks: 4,       forcePrediction: false, maxMisconceptions: 1 }
    case 'kinesthetic':
      return { maxBlocks: Infinity, forcePrediction: true,  maxMisconceptions: 2 }
    default:
      return { maxBlocks: Infinity, forcePrediction: false, maxMisconceptions: Infinity }
  }
}

// ── Utilities ─────────────────────────────────────────────────────────────────

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

function cap<T>(arr: T[], max: number): T[] {
  return max === Infinity ? arr : arr.slice(0, max)
}

// ── Budget constant ───────────────────────────────────────────────────────────

const MAX_INTERACTIVE_STEPS = 8

// ── Code Lab step factory (used by both paths) ────────────────────────────────

function makeCodeLabStep(moduleId: string, moduleTitle: string, phase: Phase5E): LearningJourneyStep | null {
  const slug = getCodeLabSlug(`${moduleId} ${moduleTitle}`)
  if (!slug) return null
  const meta: InteractivePracticeMeta = {
    interactiveType: 'code_lab',
    topicSlug:       slug,
    description:     `Practica ${moduleTitle} directamente en el editor interactivo.`,
  }
  return createStep(`code-lab-${moduleId}`, 'interactive_practice', phase, {
    title:    `Práctica en Code Lab: ${moduleTitle}`,
    xpReward: 10,
    metadata: meta as unknown as Record<string, unknown>,
  })
}

// ── Sprint L1: ConceptBlock path ──────────────────────────────────────────────

function buildJourneyFromConceptBlocks(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
  dominantModality?: LearningModality,
): LearningJourney {
  const steps: LearningJourneyStep[] = []
  const { module_title, module_id, course_id } = moduleContent
  const cbConfig    = getConceptBlockConfig(dominantModality)
  const activeBlocks = cbConfig.maxBlocks === Infinity
    ? moduleContent.concept_blocks
    : moduleContent.concept_blocks.slice(0, cbConfig.maxBlocks)

  let interactiveUsed = 0
  let currentPhase: Phase5E = 'explore'

  const tryPush = (step: LearningJourneyStep): void => {
    if (interactiveUsed >= MAX_INTERACTIVE_STEPS) return
    steps.push({ ...step, phase: currentPhase })
    interactiveUsed++
  }

  const halfLen = Math.ceil(activeBlocks.length / 2)

  activeBlocks.forEach((block: ConceptBlock, i: number) => {
    currentPhase = i < halfLen ? 'explore' : 'explain'

    // Kinesthetic: prediction BEFORE the concept block (learn by doing)
    if (cbConfig.forcePrediction) {
      tryPush(makeKinestheticPrediction(module_title, i))
    }

    if (block.prediction_question && !cbConfig.forcePrediction) {
      // Feedback del PO (Pruebas 1): la revelación debe RESPONDER, no decir
      // «sigue leyendo». La respuesta real es la explicación del propio bloque.
      const predMeta: PredictionMeta = {
        question: block.prediction_question,
        reveal:   splitParagraphs(block.explanation)[0] ?? block.title,
        hint:     `La clave está en: ${block.title.toLowerCase()}.`,
      }
      tryPush(createStep(`cb-predict-${i}`, 'prediction', currentPhase, {
        xpReward: 1, requiresAnswer: true,
        metadata: predMeta as unknown as Record<string, unknown>,
      }))
    }

    steps.push(createStep(block.id, 'concept', currentPhase, {
      title: block.title, content: block.explanation, xpReward: 2,
    }))

    if ((i + 1) % 2 === 0 && block.curiosity) {
      const meta: CuriosityMeta = { fact: block.curiosity.fact, stat: block.curiosity.stat, source: block.curiosity.source }
      tryPush(createStep(`cb-curiosity-${i}`, 'curiosity', currentPhase, {
        xpReward: 2, metadata: meta as unknown as Record<string, unknown>,
      }))
    }

    switch (i % 3) {
      case 0: {
        const meta: MicroQuestionMeta = {
          question: '¿Te imaginabas esto?',
          options:  ['Sí, lo imaginaba', 'No, fue una sorpresa', 'Un poco'],
          feedback: 'Reflexionar sobre lo que sabías antes de leer ayuda a consolidar el aprendizaje.',
        }
        tryPush(createStep(`cb-mq-${i}`, 'micro_question', currentPhase, {
          title: '¿Te imaginabas esto?', xpReward: 2, requiresAnswer: true,
          metadata: meta as unknown as Record<string, unknown>,
        }))
        break
      }
      case 1: {
        if (!block.analogy) break
        const meta: AnalogyMeta = {
          target: module_title, source: block.analogy.source,
          explanation: block.analogy.explanation, image_hint: block.analogy.image_hint,
        }
        tryPush(createStep(`cb-analogy-${i}`, 'analogy', currentPhase, {
          xpReward: 2, metadata: meta as unknown as Record<string, unknown>,
        }))
        break
      }
      case 2: {
        if (!block.media_prompt) break
        const meta: MediaPromptMeta = {
          type: block.media_prompt.type, title: block.media_prompt.title,
          prompt: block.media_prompt.prompt, learning_goal: block.media_prompt.learning_goal,
          duration_seconds: block.media_prompt.duration_seconds,
        }
        tryPush(createStep(`cb-media-${i}`, 'media_prompt', currentPhase, {
          xpReward: 2, metadata: meta as unknown as Record<string, unknown>,
        }))
        break
      }
    }

    if (block.example) {
      steps.push(createStep(`cb-example-${i}`, 'example', 'explain', {
        content: block.example, xpReward: 3,
      }))
    }

    if (block.mini_activity) {
      const miniMeta: MiniActivityMeta = {
        instructions: block.mini_activity.instructions,
        steps:        block.mini_activity.steps,
      }
      tryPush(createStep(`cb-mini-${i}`, 'mini_activity', currentPhase, {
        xpReward: 3, requiresAnswer: true,
        metadata: miniMeta as unknown as Record<string, unknown>,
      }))

      if (block.reflection_question) {
        const refMeta: MicroQuestionMeta = {
          question: block.reflection_question,
          options:  ['Puedo explicarlo', 'Lo entiendo parcialmente', 'Necesito repasarlo'],
          feedback: '¡La reflexión metacognitiva fortalece el aprendizaje a largo plazo!',
        }
        tryPush(createStep(`cb-reflect-${i}`, 'micro_question', currentPhase, {
          title: block.reflection_question, xpReward: 2, requiresAnswer: true,
          metadata: refMeta as unknown as Record<string, unknown>,
        }))
      }
    }
  })

  // ── Elaborate phase ───────────────────────────────────────────────────────
  currentPhase = 'elaborate'
  const realNews = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
  const applicationItems: string[] = [
    ...(realNews ? [realNews.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    const predMeta: PredictionMeta = {
      question: `¿Qué crees que ocurrirá cuando ${module_title.toLowerCase()} se aplique en la práctica?`,
      reveal:   applicationItems[0],
      hint:     'Piensa en situaciones cotidianas donde esta idea podría marcar la diferencia.',
    }
    steps.push(createStep('cb-prediction', 'prediction', 'elaborate', {
      xpReward: 3, requiresAnswer: true,
      metadata: predMeta as unknown as Record<string, unknown>,
    }))
    steps.push(createStep('cb-application', 'application', 'elaborate', {
      xpReward: 2, metadata: { items: applicationItems },
    }))
  }

  if (dominantModality === 'kinesthetic') {
    const codeLabStep = makeCodeLabStep(module_id, module_title, 'elaborate')
    if (codeLabStep) steps.push(codeLabStep)
  }

  // ── Evaluate phase ────────────────────────────────────────────────────────
  const shownMisconceptions = cbConfig.maxMisconceptions === Infinity
    ? moduleContent.misconceptions
    : moduleContent.misconceptions.slice(0, cbConfig.maxMisconceptions)

  shownMisconceptions.forEach((item, i) => {
    steps.push(createStep(`cb-reflection-${i}`, 'reflection', 'evaluate', {
      title: item.misconception, content: item.correction,
      xpReward: 5, metadata: { severity: item.severity },
    }))
  })

  return {
    id:               `journey-${module_id}`,
    moduleTitle:      module_title,
    courseId:         course_id,
    steps,
    sessionId:        engagementSession.session_id,
    dominantModality: dominantModality ?? undefined,
  }
}

// ── Public entry point ────────────────────────────────────────────────────────

/**
 * Builds a module-only LearningJourney. The Engage phase already ran and is
 * NOT repeated here. No engage resource types appear as steps.
 *
 * D6.3: pass options.dominantModality to enable modality-based step selection.
 */
export function buildJourneyFromLegacy(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
  options?:          { dominantModality?: LearningModality },
): LearningJourney {
  const dominantModality = options?.dominantModality

  if (moduleContent.concept_blocks && moduleContent.concept_blocks.length > 0) {
    return buildJourneyFromConceptBlocks(engagementSession, moduleContent, dominantModality)
  }

  // ── Legacy heuristic path ─────────────────────────────────────────────────
  const steps: LearningJourneyStep[] = []
  const knowledgeLevel = readKnowledgeLevel(engagementSession.session_id)
  const cfg            = getDepthConfig(knowledgeLevel)

  const introParagraphs       = cap(splitParagraphs(moduleContent.introduction),            cfg.maxIntroParagraphs)
  const explanationParagraphs = cap(splitParagraphs(moduleContent.pedagogical_explanation), cfg.maxExplanationParagraphs)
  const examples              = cap(moduleContent.examples, cfg.maxExamples)

  const conceptPool: Array<{ id: string; text: string }> = [
    ...introParagraphs.map((text, i)       => ({ id: `intro-concept-${i}`, text })),
    ...explanationParagraphs.map((text, i) => ({ id: `concept-${i}`,       text })),
  ]

  const moduleTitle = moduleContent.module_title

  // ── Explore + Explain via Modality-Depth Matrix (D6.5.1) ──────────────────
  const exploreExplainSteps = buildExploreExplainSteps(
    dominantModality, conceptPool, examples, moduleTitle,
  )
  steps.push(...exploreExplainSteps)

  // ── Elaborate phase ───────────────────────────────────────────────────────
  const realNews = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
  const applicationItems: string[] = [
    ...(realNews ? [realNews.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    steps.push({ ...makePrediction(moduleTitle, applicationItems[0]), phase: 'elaborate' })
    steps.push(createStep('application-combined', 'application', 'elaborate', {
      xpReward: 2, metadata: { items: applicationItems },
    }))
  }

  if (dominantModality === 'kinesthetic') {
    const codeLabStep = makeCodeLabStep(moduleContent.module_id, moduleTitle, 'elaborate')
    if (codeLabStep) steps.push(codeLabStep)
  }

  // ── Evaluate phase ────────────────────────────────────────────────────────
  cap(moduleContent.misconceptions, cfg.maxMisconceptions).forEach((item, i) => {
    steps.push(createStep(`reflection-${i}`, 'reflection', 'evaluate', {
      title: item.misconception, content: item.correction,
      xpReward: 5, metadata: { severity: item.severity },
    }))
  })

  return {
    id:               `journey-${moduleContent.module_id}`,
    moduleTitle:      moduleContent.module_title,
    courseId:         moduleContent.course_id,
    steps,
    sessionId:        engagementSession.session_id,
    dominantModality: dominantModality ?? undefined,
  }
}
