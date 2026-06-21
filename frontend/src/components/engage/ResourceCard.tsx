/**
 * ResourceCard — card router for Engage phase resources.
 *
 * Routes each resource_type to its specific card component.
 * Types without a dedicated card fall back to GenericCard.
 *
 * Sprint progress:
 *   C1  ✓ did_you_know        → DidYouKnowCard
 *   H1  ✓ prior_knowledge     → PriorKnowledgeCard
 *   C2  ✓ detonating_question → DetonatingQuestionCard
 *   C3  ✓ real_news           → RealNewsCard
 *   C4  ✓ mini_quiz           → MiniQuizCard
 *   C5  ✓ short_challenge     → ShortChallengeCard
 */

import type { EngagementResource } from '@/types/engagement'
import { DidYouKnowCard } from './cards/DidYouKnowCard'
import { PriorKnowledgeCard } from './cards/PriorKnowledgeCard'
import { DetonatingQuestionCard } from './cards/DetonatingQuestionCard'
import { RealNewsCard } from './cards/RealNewsCard'
import { MiniQuizCard } from './cards/MiniQuizCard'
import { ShortChallengeCard } from './cards/ShortChallengeCard'

// ── Generic fallback (removed one by one as real cards land) ────────────────

function GenericCard({ resource }: { resource: EngagementResource }) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold leading-snug">{resource.title}</h2>
      <p className="text-muted-foreground leading-relaxed">{resource.content}</p>
    </div>
  )
}

// ── Router ────────────────────────────────────────────────────────────────────

interface Props {
  resource:  EngagementResource
  sessionId: string
  /** Fired when an interactive card records a user answer (used to gate navigation). */
  onAnswer?: () => void
}

export function ResourceCard({ resource, sessionId, onAnswer }: Props) {
  switch (resource.resource_type) {
    case 'did_you_know':
      return <DidYouKnowCard resource={resource} />
    case 'prior_knowledge':
      return <PriorKnowledgeCard resource={resource} sessionId={sessionId} onAnswer={onAnswer} />
    case 'detonating_question':
      return <DetonatingQuestionCard resource={resource} sessionId={sessionId} />
    case 'real_news':
      return <RealNewsCard resource={resource} sessionId={sessionId} />
    case 'mini_quiz':
      return <MiniQuizCard resource={resource} sessionId={sessionId} />
    case 'short_challenge':
      return <ShortChallengeCard resource={resource} sessionId={sessionId} />
    default:
      return <GenericCard resource={resource} />
  }
}
