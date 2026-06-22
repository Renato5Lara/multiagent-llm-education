import type {
  LearningJourney,
  LearningJourneyStep,
  MicroQuestionMeta,
  PredictionMeta,
  MiniActivityMeta,
  CuriosityMeta,
  AnalogyMeta,
  MediaPromptMeta,
} from '@/types/learningJourney'
import type {
  EngagementSession,
  EngagementResourceType,
} from '@/types/engagement'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'

// ── Knowledge level (written by PriorKnowledgeCard during Engage) ─────────────

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

// ── Depth configuration ───────────────────────────────────────────────────────

interface DepthConfig {
  maxIntroParagraphs:       number  // Infinity = all
  maxExplanationParagraphs: number  // Infinity = all
  maxExamples:              number  // Infinity = all
  maxMisconceptions:        number  // Infinity = all
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

// ── Helpers ───────────────────────────────────────────────────────────────────

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

function cap<T>(arr: T[], max: number): T[] {
  return max === Infinity ? arr : arr.slice(0, max)
}

// ── Sprint L4: Interactive step factories ─────────────────────────────────────

function makeMicroQuestion(conceptIdx: number): LearningJourneyStep {
  const meta: MicroQuestionMeta = {
    question: '¿Te imaginabas esto?',
    options:  ['Sí, lo imaginaba', 'No, fue una sorpresa', 'Un poco'],
    feedback: 'Reflexionar sobre lo que sabías antes de leer ayuda a consolidar el aprendizaje.',
  }
  return {
    id:             `micro-q-${conceptIdx}`,
    type:           'micro_question',
    title:          '¿Te imaginabas esto?',
    xpReward:       2,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makeAnalogy(moduleTitle: string, conceptIdx: number): LearningJourneyStep {
  const titleLower = moduleTitle.toLowerCase()
  const meta: AnalogyMeta = {
    target:      moduleTitle,
    source:      'una guía paso a paso',
    explanation: `Así como una guía te muestra el camino para lograr algo de forma ordenada, ${titleLower} te proporciona los fundamentos y la estructura necesarios para entender y aplicar sus ideas de manera efectiva.`,
    image_hint:  `Imagina una guía bien organizada con secciones claras, cada una llevándote un paso más lejos en la comprensión de ${titleLower}.`,
  }
  return {
    id:       `analogy-${conceptIdx}`,
    type:     'analogy',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

function makeMediaPrompt(moduleTitle: string, conceptIdx: number): LearningJourneyStep {
  // Rotate type every 3 media prompts for variety
  const types: Array<'image' | 'video' | 'audio'> = ['image', 'video', 'image']
  const mediaType = types[Math.floor(conceptIdx / 3) % types.length]

  const configs: Record<'image' | 'video' | 'audio', Pick<MediaPromptMeta, 'title' | 'prompt' | 'learning_goal'>> = {
    image: {
      title:         `Visualiza: ${moduleTitle}`,
      prompt:        `Crea una infografía educativa que explique "${moduleTitle}" usando ejemplos cotidianos. Incluye íconos y flechas que muestren las relaciones entre sus conceptos principales. Estilo limpio, colores suaves, fondo blanco.`,
      learning_goal: `Construir una representación visual refuerza la memoria a largo plazo y facilita la comprensión de ideas abstractas en ${moduleTitle.toLowerCase()}.`,
    },
    video: {
      title:         `Explora en video: ${moduleTitle}`,
      prompt:        `Crea un guion para un video animado de 90 segundos que explique "${moduleTitle}" de forma clara y visual. Usa metáforas cotidianas, narración simple y ejemplos del mundo real.`,
      learning_goal: `Los videos activan múltiples canales sensoriales simultáneamente, incrementando la retención y la comprensión de ${moduleTitle.toLowerCase()}.`,
    },
    audio: {
      title:         `Escucha sobre: ${moduleTitle}`,
      prompt:        `Crea un guion de narración de audio de 60 segundos sobre "${moduleTitle}". Tono conversacional, ritmo pausado, con una analogía cotidiana al inicio y un resumen al final.`,
      learning_goal: `La narración auditiva activa el procesamiento verbal y ayuda a consolidar conceptos complejos de ${moduleTitle.toLowerCase()}.`,
    },
  }

  const cfg = configs[mediaType]
  const meta: MediaPromptMeta = { type: mediaType, ...cfg }
  return {
    id:       `media-${conceptIdx}`,
    type:     'media_prompt',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

function makeMiniActivity(exampleIdx: number): LearningJourneyStep {
  const meta: MiniActivityMeta = {
    instructions: 'Refuerza la idea principal del ejemplo que acabas de leer.',
    steps: [
      'Lee nuevamente el ejemplo.',
      'Identifica el concepto clave que ilustra.',
      'Escribe mentalmente una palabra que lo resuma.',
    ],
  }
  return {
    id:             `mini-act-${exampleIdx}`,
    type:           'mini_activity',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makePrediction(moduleTitle: string, firstApplication: string | undefined): LearningJourneyStep {
  const titleLower = moduleTitle.toLowerCase()
  const meta: PredictionMeta = {
    question: `¿Qué crees que ocurrirá cuando ${titleLower} se aplique en la práctica?`,
    reveal:   firstApplication
      ?? `En la práctica, ${titleLower} permite resolver problemas reales de forma estructurada y eficiente, con impacto directo en los resultados.`,
    hint:     'Piensa en situaciones cotidianas donde esta idea podría marcar la diferencia.',
  }
  return {
    id:             'prediction-pre-application',
    type:           'prediction',
    xpReward:       3,
    requiresAnswer: true,
    metadata:       meta as unknown as Record<string, unknown>,
  }
}

function makeCuriosity(moduleTitle: string, curiosityIdx: number): LearningJourneyStep {
  const meta: CuriosityMeta = {
    fact:   `Muchas organizaciones y empresas tecnológicas aplican los principios de ${moduleTitle.toLowerCase()} en sus sistemas todos los días.`,
    stat:   '8 de cada 10',
    source: 'Tendencias en educación tecnológica, 2024',
  }
  return {
    id:       `curiosity-${curiosityIdx}`,
    type:     'curiosity',
    xpReward: 2,
    metadata: meta as unknown as Record<string, unknown>,
  }
}

// ── Main builder ──────────────────────────────────────────────────────────────

/**
 * Builds a module-only LearningJourney. The Engage phase already ran and is
 * NOT repeated here. No engage resource types appear as steps.
 *
 * Sprint L4 enriches the sequence with interleaved interactive steps:
 *   concept[0] → micro_question
 *   concept[1] → analogy
 *   concept[2] → media_prompt
 *   every 2 concepts → curiosity (after the positional step)
 *   every example → mini_activity
 *   before application → prediction
 *
 * Step order:
 *   zip(concepts + interactive inserts, examples + mini_activity)
 *   prediction (if application exists)
 *   application
 *   reflection(s)
 */
export function buildJourneyFromLegacy(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
): LearningJourney {
  const steps: LearningJourneyStep[] = []

  // ── Personalization ────────────────────────────────────────────────────────
  const knowledgeLevel = readKnowledgeLevel(engagementSession.session_id)
  const cfg            = getDepthConfig(knowledgeLevel)

  // ── Content pools ──────────────────────────────────────────────────────────
  const introParagraphs       = cap(splitParagraphs(moduleContent.introduction),            cfg.maxIntroParagraphs)
  const explanationParagraphs = cap(splitParagraphs(moduleContent.pedagogical_explanation), cfg.maxExplanationParagraphs)
  const examples              = cap(moduleContent.examples, cfg.maxExamples)

  const conceptPool: Array<{ id: string; text: string }> = [
    ...introParagraphs.map((text, i)       => ({ id: `intro-concept-${i}`, text })),
    ...explanationParagraphs.map((text, i) => ({ id: `concept-${i}`,       text })),
  ]

  const moduleTitle  = moduleContent.module_title
  let curiosityCount = 0

  // ── Phase 1: Zip concepts (with inserts) + examples (with mini_activity) ──
  const phaseLen = Math.max(conceptPool.length, examples.length)
  for (let i = 0; i < phaseLen; i++) {

    // ── Concept + positional interactive step ────────────────────────────────
    if (i < conceptPool.length) {
      const { id, text } = conceptPool[i]
      steps.push({ id, type: 'concept', content: text, xpReward: 2 })

      // Rule 6 — every 2 concepts: insert curiosity BEFORE positional step
      // so the rhythm is: concept → curiosity → micro_question/analogy/media_prompt
      if ((i + 1) % 2 === 0) {
        steps.push(makeCuriosity(moduleTitle, curiosityCount++))
      }

      // Rules 1/2/3 — positional step by concept index mod 3
      switch (i % 3) {
        case 0: steps.push(makeMicroQuestion(i)); break
        case 1: steps.push(makeAnalogy(moduleTitle, i)); break
        case 2: steps.push(makeMediaPrompt(moduleTitle, i)); break
      }
    }

    // ── Example + mini_activity ───────────────────────────────────────────────
    if (i < examples.length) {
      steps.push({ id: `example-${i}`, type: 'example', content: examples[i], xpReward: 3 })
      // Rule 4 — after every example
      steps.push(makeMiniActivity(i))
    }
  }

  // ── Phase 2: Application (with prediction gate) ────────────────────────────
  const realNewsResource = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
  const applicationItems: string[] = [
    ...(realNewsResource ? [realNewsResource.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    // Rule 5 — prediction before application
    steps.push(makePrediction(moduleTitle, applicationItems[0]))
    steps.push({
      id:       'application-combined',
      type:     'application',
      xpReward: 2,
      metadata: { items: applicationItems },
    })
  }

  // ── Phase 3: Reflections (misconceptions as checkpoints) ──────────────────
  cap(moduleContent.misconceptions, cfg.maxMisconceptions).forEach((item, i) => {
    steps.push({
      id:       `reflection-${i}`,
      type:     'reflection',
      title:    item.misconception,
      content:  item.correction,
      xpReward: 5,
      metadata: { severity: item.severity },
    })
  })

  return {
    id:          `journey-${moduleContent.module_id}`,
    moduleTitle: moduleContent.module_title,
    courseId:    moduleContent.course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}
