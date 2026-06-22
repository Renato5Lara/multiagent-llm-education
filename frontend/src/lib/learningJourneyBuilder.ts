import type { LearningJourney, LearningJourneyStep } from '@/types/learningJourney'
import type {
  EngagementSession,
  EngagementResource,
  EngagementResourceType,
  MiniQuizMetadata,
  ShortChallengeMetadata,
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

// ── Depth configuration — how much content to include per level ───────────────

interface DepthConfig {
  maxIntroParagraphs:       number  // Infinity = all
  maxExplanationParagraphs: number  // Infinity = all
  maxExamples:              number  // Infinity = all
  maxMisconceptions:        number  // Infinity = all
  earlyChallenge:           boolean // true = challenge appears before full explanation
}

function getDepthConfig(level: KnowledgeLevel | null): DepthConfig {
  switch (level) {
    case 'never_seen':
    case 'heard_about_it':
      // Beginners: full depth, challenge after explanation
      return { maxIntroParagraphs: Infinity, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity, earlyChallenge: false }
    case 'know_a_bit':
      // Intermediate: trim intro, keep full explanation + examples
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 4, maxExamples: Infinity, maxMisconceptions: 2, earlyChallenge: false }
    case 'know_well':
      // Advanced: concise intro + explanation, challenge surfaced early
      return { maxIntroParagraphs: 1, maxExplanationParagraphs: 2, maxExamples: Infinity, maxMisconceptions: 1, earlyChallenge: true }
    default:
      return { maxIntroParagraphs: 2, maxExplanationParagraphs: Infinity, maxExamples: Infinity, maxMisconceptions: Infinity, earlyChallenge: false }
  }
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

function cap<T>(arr: T[], max: number): T[] {
  return max === Infinity ? arr : arr.slice(0, max)
}

function engageToStep(resource: EngagementResource): LearningJourneyStep {
  const base = {
    id:      resource.id,
    title:   resource.title   || undefined,
    content: resource.content || undefined,
  }

  switch (resource.resource_type) {
    case 'short_challenge': {
      const meta = resource.resource_metadata as ShortChallengeMetadata
      return {
        ...base,
        type:           'challenge',
        requiresAnswer: true,
        xpReward:       8,
        metadata: { prompt: meta?.prompt ?? resource.content, hint: meta?.hint },
      }
    }
    case 'mini_quiz': {
      const meta = resource.resource_metadata as MiniQuizMetadata
      return {
        ...base,
        type:           'evaluation',
        requiresAnswer: true,
        xpReward:       10,
        metadata: {
          options:       meta?.options       ?? [],
          correct_index: meta?.correct_index ?? 0,
          explanation:   meta?.explanation   ?? '',
        },
      }
    }
    // did_you_know / prior_knowledge / detonating_question / real_news:
    // never called — these types are not re-rendered in the journey.
    default:
      return { ...base, type: 'did_you_know' }
  }
}

// ── Main builder ──────────────────────────────────────────────────────────────

/**
 * Builds a module-only LearningJourney from engagement session context and
 * module content. Engage resources that already ran (did_you_know,
 * prior_knowledge, detonating_question) are NOT included — only the
 * post-engage module experience.
 *
 * Only two engage resources survive into the journey:
 *   - short_challenge → challenge   (applied practice, spaced from engage)
 *   - mini_quiz       → evaluation  (culminating assessment after module)
 *
 * Personalization uses the knowledge_level stored in sessionStorage by
 * PriorKnowledgeCard during the Engage phase:
 *   never_seen / heard_about_it → full depth, challenge after explanation
 *   know_a_bit                  → trimmed intro, challenge after explanation
 *   know_well                   → concise, challenge surfaced early
 *
 * Step order:
 *   [early challenge — advanced only]
 *   zip(concepts, examples)
 *   challenge — beginners/intermediate
 *   mid-reflection (first misconception)
 *   application
 *   end reflections (remaining misconceptions)
 *   evaluation
 */
export function buildJourneyFromLegacy(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
): LearningJourney {
  const steps: LearningJourneyStep[] = []

  // ── Engage resource index ──────────────────────────────────────────────────
  const sorted = [...engagementSession.resources].sort((a, b) => a.display_order - b.display_order)
  const byType = new Map<EngagementResourceType, EngagementResource>()
  for (const r of sorted) {
    if (!byType.has(r.resource_type)) byType.set(r.resource_type, r)
  }

  const push = (step: LearningJourneyStep | null | undefined) => { if (step) steps.push(step) }

  const fromEngage = (type: EngagementResourceType): LearningJourneyStep | null => {
    const r = byType.get(type)
    return r ? engageToStep(r) : null
  }

  // ── Personalization ────────────────────────────────────────────────────────
  const knowledgeLevel = readKnowledgeLevel(engagementSession.session_id)
  const cfg            = getDepthConfig(knowledgeLevel)

  // ── Content pools ──────────────────────────────────────────────────────────
  const introParagraphs       = cap(splitParagraphs(moduleContent.introduction),          cfg.maxIntroParagraphs)
  const explanationParagraphs = cap(splitParagraphs(moduleContent.pedagogical_explanation), cfg.maxExplanationParagraphs)
  const examples              = cap(moduleContent.examples, cfg.maxExamples)

  // Concept pool: all intro + all explanation paragraphs, in order
  const conceptPool: Array<{ id: string; text: string }> = [
    ...introParagraphs.map((text, i)       => ({ id: `intro-concept-${i}`, text })),
    ...explanationParagraphs.map((text, i) => ({ id: `concept-${i}`,       text })),
  ]

  // ── Phase 1: Early challenge (advanced students — try before theory) ───────
  if (cfg.earlyChallenge && conceptPool.length > 0) {
    const first = conceptPool.shift()!
    steps.push({ id: first.id, type: 'concept', content: first.text, xpReward: 2 })
    push(fromEngage('short_challenge'))
  }

  // ── Phase 2: Zip remaining concepts with examples ─────────────────────────
  const phaseLen = Math.max(conceptPool.length, examples.length)
  for (let i = 0; i < phaseLen; i++) {
    if (i < conceptPool.length) {
      const { id, text } = conceptPool[i]
      steps.push({ id, type: 'concept', content: text, xpReward: 2 })
    }
    if (i < examples.length) {
      steps.push({ id: `example-${i}`, type: 'example', content: examples[i], xpReward: 3 })
    }
  }

  // ── Phase 3: Challenge — beginner/intermediate path ────────────────────────
  if (!cfg.earlyChallenge) {
    push(fromEngage('short_challenge'))
  }

  // ── Phase 4: Mid-reflection (first misconception — reality check) ──────────
  const misconceptions    = cap(moduleContent.misconceptions, cfg.maxMisconceptions)
  const midMisconception  = misconceptions.length > 1 ? misconceptions[0]       : null
  const endMisconceptions = midMisconception           ? misconceptions.slice(1) : misconceptions

  if (midMisconception) {
    steps.push({
      id:       'reflection-mid',
      type:     'reflection',
      title:    midMisconception.misconception,
      content:  midMisconception.correction,
      xpReward: 5,
      metadata: { severity: midMisconception.severity },
    })
  }

  // ── Phase 5: Application — real_news (engage context) + module applications ─
  const realNewsResource = byType.get('real_news')
  const applicationItems: string[] = [
    ...(realNewsResource ? [realNewsResource.content] : []),
    ...moduleContent.real_applications,
  ]
  if (applicationItems.length > 0) {
    steps.push({
      id:       'application-combined',
      type:     'application',
      xpReward: 2,
      metadata: { items: applicationItems },
    })
  }

  // ── Phase 6: End reflections (remaining misconceptions) ───────────────────
  endMisconceptions.forEach((item, i) => {
    steps.push({
      id:       `reflection-${i}`,
      type:     'reflection',
      title:    item.misconception,
      content:  item.correction,
      xpReward: 5,
      metadata: { severity: item.severity },
    })
  })

  // ── Phase 7: Evaluation — spaced from engage, now after full module ────────
  push(fromEngage('mini_quiz'))

  return {
    id:          `journey-${moduleContent.module_id}`,
    moduleTitle: moduleContent.module_title,
    courseId:    moduleContent.course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}
