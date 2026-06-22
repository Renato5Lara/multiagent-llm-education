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
 * linear LearningJourney. No backend changes required — pure frontend adapter.
 *
 * Step order:
 *   DidYouKnow → PriorKnowledge → Concept (intro) → Question →
 *   Concept (explanation) → Example → Challenge →
 *   Application → Reflection (misconceptions) → Evaluation
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

  // 1. DidYouKnow (engage)
  push(fromEngage('did_you_know'))

  // 2. PriorKnowledge (engage)
  push(fromEngage('prior_knowledge'))

  // 3. Introduction → Concept
  splitParagraphs(moduleContent.introduction).forEach((text, i) => {
    steps.push({ id: `intro-concept-${i}`, type: 'concept', content: text, xpReward: 2 })
  })

  // 4. DetonatingQuestion → Question (engage)
  push(fromEngage('detonating_question'))

  // 5. PedagogicalExplanation → Concept
  splitParagraphs(moduleContent.pedagogical_explanation).forEach((text, i) => {
    steps.push({ id: `concept-${i}`, type: 'concept', content: text, xpReward: 2 })
  })

  // 6. Examples → Example
  moduleContent.examples.forEach((ex, i) => {
    steps.push({ id: `example-${i}`, type: 'example', content: ex, xpReward: 3 })
  })

  // 7. Challenge (engage)
  push(fromEngage('short_challenge'))

  // 8. Application — merge real_news (engage) + real_applications (module) into one step
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

  // 9. Reflection — one step per misconception
  moduleContent.misconceptions.forEach((item, i) => {
    steps.push({
      id:       `reflection-${i}`,
      type:     'reflection',
      title:    item.misconception,
      content:  item.correction,
      xpReward: 5,
      metadata: { severity: item.severity },
    })
  })

  // 10. Evaluation (engage mini_quiz)
  push(fromEngage('mini_quiz'))

  return {
    id:         `journey-${moduleContent.module_id}`,
    moduleTitle: moduleContent.module_title,
    courseId:    moduleContent.course_id,
    steps,
    sessionId:   engagementSession.session_id,
  }
}
