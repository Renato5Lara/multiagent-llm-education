import type { LearningJourney, LearningJourneyStep } from '@/types/learningJourney'
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

// ── Main builder ──────────────────────────────────────────────────────────────

/**
 * Builds a module-only LearningJourney. The Engage phase already ran and is
 * NOT repeated here. No engage resource types appear as steps.
 *
 * The session is used only for personalization via the knowledge_level
 * written to sessionStorage by PriorKnowledgeCard:
 *   never_seen / heard_about_it → full depth
 *   know_a_bit                  → trimmed intro + explanation
 *   know_well                   → concise (first intro paragraph only)
 *
 * Step order:
 *   zip(concepts, examples)   — interleaved for rhythm
 *   application               — real-world context
 *   reflection(s)             — misconceptions as checkpoints
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

  // ── Phase 1: Zip concepts with examples ───────────────────────────────────
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

  // ── Phase 2: Application ──────────────────────────────────────────────────
  // real_news from engage provides a real-world hook; real_applications from
  // module content provide depth. Merged into one bookmarkable card.
  const realNewsResource = engagementSession.resources
    .find(r => r.resource_type === ('real_news' as EngagementResourceType))
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
