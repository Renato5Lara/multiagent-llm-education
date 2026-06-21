/**
 * ResourceCard — card router for Engage phase resources.
 *
 * Routes each resource_type to its specific card component.
 * Types without a dedicated card fall back to GenericCard.
 *
 * Sprint progress:
 *   C1 ✓ did_you_know      → DidYouKnowCard
 *   C2   detonating_question → DetonatingQuestionCard (pending)
 *   C3   real_news           → RealNewsCard (pending)
 *   C4   mini_quiz           → MiniQuizCard (pending)
 *   C5   short_challenge     → ShortChallengeCard (pending)
 */

import type { EngagementResource } from '@/types/engagement'
import { DidYouKnowCard } from './cards/DidYouKnowCard'

// ── Generic fallback (removed one by one as real cards land) ────────────────

function GenericCard({ resource }: { resource: EngagementResource }) {
  const meta = resource.resource_metadata as Record<string, unknown>

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold leading-snug">{resource.title}</h2>

      <p className="text-muted-foreground leading-relaxed">{resource.content}</p>

      {/* mini_quiz options */}
      {resource.resource_type === 'mini_quiz' && meta.options && (
        <div className="space-y-2 mt-4">
          <p className="text-sm font-medium text-muted-foreground">
            {String(meta.question ?? 'Selecciona la respuesta correcta:')}
          </p>
          {(meta.options as string[]).map((opt, i) => (
            <div
              key={i}
              className="text-sm px-4 py-2.5 rounded-lg border border-border bg-muted/40 hover:bg-muted transition-colors cursor-pointer"
            >
              <span className="font-medium mr-2">{String.fromCharCode(65 + i)}.</span>
              {opt}
            </div>
          ))}
          <p className="text-xs text-muted-foreground italic mt-1">
            (Interacción completa disponible en Sprint C4)
          </p>
        </div>
      )}

      {/* short_challenge */}
      {resource.resource_type === 'short_challenge' && meta.prompt && (
        <div className="mt-4 p-4 rounded-xl border border-primary/20 bg-primary/5">
          <p className="text-sm font-semibold mb-1.5">Tu desafío:</p>
          <p className="text-sm">{String(meta.prompt)}</p>
          {meta.hint && (
            <p className="text-xs text-muted-foreground mt-2">Pista: {String(meta.hint)}</p>
          )}
          <p className="text-xs text-muted-foreground italic mt-3">
            (Área de respuesta disponible en Sprint C5)
          </p>
        </div>
      )}

      {/* real_news source */}
      {resource.resource_type === 'real_news' && meta.source_hint && (
        <p className="text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
          Fuente: {String(meta.source_hint)}{meta.year ? ` · ${meta.year}` : ''}
        </p>
      )}
    </div>
  )
}

// ── Router ────────────────────────────────────────────────────────────────────

interface Props {
  resource: EngagementResource
}

export function ResourceCard({ resource }: Props) {
  switch (resource.resource_type) {
    case 'did_you_know':
      return <DidYouKnowCard resource={resource} />
    default:
      return <GenericCard resource={resource} />
  }
}
