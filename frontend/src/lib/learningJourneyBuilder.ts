import type { LearningJourney, LearningJourneyStep } from '@/types/learningJourney'
import type {
  EngagementSession,
  EngagementResource,
  EngagementResourceType,
  MiniQuizMetadata,
  ShortChallengeMetadata,
} from '@/types/engagement'
import type { ModuleOrchestrationResponse } from '@/types/pedagogy'

// ── Internal helpers ──────────────────────────────────────────────────────────

function splitParagraphs(text: string): string[] {
  return text.split(/\n\n+/).map(p => p.trim()).filter(Boolean)
}

function engageToStep(resource: EngagementResource): LearningJourneyStep {
  const base = {
    id:      resource.id,
    title:   resource.title || undefined,
    content: resource.content || undefined,
  }

  switch (resource.resource_type) {
    case 'did_you_know':
      return { ...base, type: 'did_you_know', xpReward: 2 }

    case 'prior_knowledge':
      return { ...base, type: 'prior_knowledge', requiresAnswer: true, xpReward: 3 }

    case 'detonating_question':
      return { ...base, type: 'question', requiresAnswer: true, xpReward: 5 }

    case 'real_news':
      return { ...base, type: 'application', xpReward: 2, metadata: { items: [resource.content] } }

    case 'short_challenge': {
      const meta = resource.resource_metadata as ShortChallengeMetadata
      return {
        ...base,
        type:           'challenge',
        requiresAnswer: true,
        xpReward:       8,
        metadata: {
          prompt: meta?.prompt ?? resource.content,
          hint:   meta?.hint,
        },
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

    default:
      return { ...base, type: 'did_you_know' }
  }
}

// ── Main builder ──────────────────────────────────────────────────────────────

/**
 * Combines an EngagementSession and ModuleOrchestrationResponse into a single
 * interleaved LearningJourney. No backend changes required — pure frontend adapter.
 *
 * Interleaving strategy (J2.5):
 *   1. Hook            — did_you_know, prior_knowledge
 *   2. Anchor concept  — intro[0] (seed for the detonating question)
 *   3. Question        — placed right after first concept, not after all content
 *   4. Content weave   — zip(remaining intro + explanation, examples): concept, example, concept, example…
 *   5. Challenge       — mid-journey application after explanation
 *   6. Mid-reflection  — first misconception (reality check before application)
 *   7. Application     — real_news (engage) + real_applications (module)
 *   8. End reflections — remaining misconceptions
 *   9. Evaluation      — mini_quiz
 *
 * This prevents the "6 engage cards → 20 concept cards" block feeling by keeping
 * engage anchors distributed throughout the sequence.
 */
export function buildJourneyFromLegacy(
  engagementSession: EngagementSession,
  moduleContent:     ModuleOrchestrationResponse,
): LearningJourney {
  const steps: LearningJourneyStep[] = []

  // Index engage resources by type (first occurrence wins, sorted by display_order)
  const sorted = [...engagementSession.resources].sort((a, b) => a.display_order - b.display_order)
  const byType = new Map<EngagementResourceType, EngagementResource>()
  for (const r of sorted) {
    if (!byType.has(r.resource_type)) byType.set(r.resource_type, r)
  }

  const push = (step: LearningJourneyStep | null | undefined) => {
    if (step) steps.push(step)
  }

  const fromEngage = (type: EngagementResourceType): LearningJourneyStep | null => {
    const r = byType.get(type)
    return r ? engageToStep(r) : null
  }

  // ── 1. Hook ───────────────────────────────────────────────────────────────
  push(fromEngage('did_you_know'))
  push(fromEngage('prior_knowledge'))

  // ── 2. Anchor concept (first intro paragraph seeds the question) ──────────
  const introParagraphs       = splitParagraphs(moduleContent.introduction)
  const explanationParagraphs = splitParagraphs(moduleContent.pedagogical_explanation)

  if (introParagraphs.length > 0) {
    steps.push({ id: 'intro-concept-0', type: 'concept', content: introParagraphs[0], xpReward: 2 })
  }

  // ── 3. Detonating question (anchored right after first concept) ───────────
  push(fromEngage('detonating_question'))

  // ── 4. Content weave — zip remaining concepts with examples ───────────────
  // Pool: remaining intro paragraphs + all explanation paragraphs
  const remainingConcepts = [
    ...introParagraphs.slice(1).map((text, i) => ({ id: `intro-concept-${i + 1}`, text })),
    ...explanationParagraphs.map((text, i)  => ({ id: `concept-${i}`,             text })),
  ]
  const examples   = moduleContent.examples
  const phaseLen   = Math.max(remainingConcepts.length, examples.length)

  for (let i = 0; i < phaseLen; i++) {
    if (i < remainingConcepts.length) {
      const { id, text } = remainingConcepts[i]
      steps.push({ id, type: 'concept', content: text, xpReward: 2 })
    }
    if (i < examples.length) {
      steps.push({ id: `example-${i}`, type: 'example', content: examples[i], xpReward: 3 })
    }
  }

  // ── 5. Challenge (mid-journey: apply before seeing applications) ──────────
  push(fromEngage('short_challenge'))

  // ── 6. Mid-reflection (first misconception as a reality check) ────────────
  // Only inserted as a mid-step when there are 2+ misconceptions; otherwise
  // the single misconception goes to end reflections together with evaluation.
  const misconceptions = moduleContent.misconceptions
  const midMisconception   = misconceptions.length > 1 ? misconceptions[0]    : null
  const endMisconceptions  = midMisconception            ? misconceptions.slice(1) : misconceptions

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

  // ── 7. Application — merge real_news (engage) + real_applications (module) ─
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

  // ── 8. End reflections (remaining misconceptions) ─────────────────────────
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

  // ── 9. Evaluation ─────────────────────────────────────────────────────────
  push(fromEngage('mini_quiz'))

  return {
    id:          `journey-${moduleContent.module_id}`,
    moduleTitle: moduleContent.module_title,
    courseId:    moduleContent.course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}
