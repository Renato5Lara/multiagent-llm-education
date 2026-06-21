import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  SkipForward,
  Unlock,
  Loader2,
  Check,
  Target,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useInteractEngagement, useCompleteEngagement } from '@/hooks/useEngagement'
import type { EngagementSession, EngagementResource, EngagementBadge, CompleteResponse } from '@/types/engagement'
import { ResourceCard } from './ResourceCard'
import { XpLevelBar } from '@/components/gamification/XpLevelBar'
import { BadgeShelf } from '@/components/gamification/BadgeShelf'
import { EngageCompletionCelebration } from '@/components/gamification/EngageCompletionCelebration'

// ── Resource framing metadata ────────────────────────────────────────────────

// Narrative label shown in the badge — reinforces the "pista" frame
const RESOURCE_LABELS: Record<string, string> = {
  did_you_know:        '💡 Evidencia',
  detonating_question: '🔎 Pista',
  real_news:           '📰 Noticia',
  mini_quiz:           '🧩 Desafío',
  short_challenge:     '🎯 Reto final',
}

// Contextual tagline shown above each card to prime curiosity
const RESOURCE_TAGLINES: Record<string, string> = {
  did_you_know:        'Esta evidencia podría cambiar la forma en que entiendes este tema.',
  detonating_question: 'Una pregunta que pocos se atreven a hacerse. Tómate un momento para reflexionar.',
  real_news:           'Algo que está pasando en el mundo real y que conecta directamente con lo que vas a aprender.',
  mini_quiz:           'Pon a prueba lo que ya sabes. Sin presión — cada intento suma experiencia.',
  short_challenge:     'Llegaste al reto principal de esta misión. Demuestra lo que descubriste.',
}

// Derive the mission objective from resources:
// prefer a detonating_question (it IS a question worth investigating);
// otherwise fall back to the first resource title.
function getMissionObjective(resources: EngagementResource[]): string {
  const question = resources.find(r => r.resource_type === 'detonating_question')
  if (question) return question.title.replace(/[?]+$/, '') + '?'
  const first = resources[0]
  if (!first) return ''
  return first.title.replace(/[.!?]+$/, '') + '.'
}

// ── Investigation dot ────────────────────────────────────────────────────────

function InvestigationDot({
  index,
  isCurrent,
  isViewed,
}: {
  index: number
  isCurrent: boolean
  isViewed: boolean
}) {
  return (
    <div
      className={cn(
        'w-8 h-8 rounded-full border-2 flex items-center justify-center transition-all duration-500',
        isCurrent
          ? 'border-primary bg-primary text-primary-foreground scale-110 shadow-md shadow-primary/30'
          : isViewed
          ? 'border-green-500 bg-green-50 text-green-600'
          : 'border-gray-200 bg-gray-50 text-gray-300',
      )}
    >
      {isViewed && !isCurrent ? (
        <Check className="h-3.5 w-3.5" />
      ) : isCurrent ? (
        <span className="text-xs font-bold">{index + 1}</span>
      ) : (
        <span className="text-[11px]">{index + 1}</span>
      )}
    </div>
  )
}

// ── XP flash ────────────────────────────────────────────────────────────────

function XpFlash({ delta }: { delta: number }) {
  return (
    <span className="inline-flex items-center gap-0.5 text-amber-500 font-semibold text-sm animate-bounce">
      ✨ +{delta} XP
    </span>
  )
}

// ── Resource badge ───────────────────────────────────────────────────────────

function ResourceBadge({ type }: { type: string }) {
  return (
    <Badge variant="secondary" className="text-xs px-2.5 py-1 font-medium">
      {RESOURCE_LABELS[type] ?? type}
    </Badge>
  )
}

// ── Resource frame (badge + pista count + tagline) ───────────────────────────
// Wraps any card with consistent framing. The card itself handles only content.

function ResourceFrame({
  resource,
  index,
  total,
  children,
}: {
  resource: EngagementResource
  index: number
  total: number
  children: React.ReactNode
}) {
  const tagline = RESOURCE_TAGLINES[resource.resource_type]
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <ResourceBadge type={resource.resource_type} />
        <span className="text-xs text-muted-foreground">
          Pista {index + 1} de {total}
        </span>
      </div>
      {tagline && (
        <p className="text-xs text-muted-foreground italic border-l-2 border-primary/30 pl-3">
          {tagline}
        </p>
      )}
      {children}
    </div>
  )
}

// ── Types ────────────────────────────────────────────────────────────────────

interface Props {
  session: EngagementSession
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
}

// ── Component ─────────────────────────────────────────────────────────────────

export function EngagePhase({ session, onComplete, onSkip, onProgress }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [currentXp, setCurrentXp]       = useState(session.xp_earned)
  const [xpDelta, setXpDelta]           = useState<number | null>(null)
  const [discoveryMsg, setDiscoveryMsg] = useState<string | null>(null)
  const [cardVisible, setCardVisible]   = useState(true)
  const [sessionBadges, setSessionBadges]     = useState<EngagementBadge[]>(session.earned_badges)
  const [newBadgeSlug, setNewBadgeSlug]       = useState<string | null>(null)
  const [completionResult, setCompletionResult] = useState<CompleteResponse | null>(null)
  // Tracks viewed IDs for dot rendering (state so re-render fires)
  const [viewedIds, setViewedIds]      = useState<Set<string>>(new Set())
  const viewedResources = useRef(new Set<string>())
  const xpTimer         = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const discoveryTimer  = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)

  const { mutate: interactMutate } = useInteractEngagement()
  const { mutate: completeMutate, isPending: isCompleting } = useCompleteEngagement()

  const resources = session.resources
  const total     = resources.length
  const resource  = resources[currentIndex]
  const isLast    = currentIndex === total - 1

  // Store detonating_question resource ID so SurpriseModal can post reflection
  useEffect(() => {
    const dq = resources.find(r => r.resource_type === 'detonating_question')
    if (dq) sessionStorage.setItem(`engage:dq-resource:${session.session_id}`, dq.id)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Card fade transition ──────────────────────────────────────────────────

  const changeResource = useCallback((nextIndex: number) => {
    setCardVisible(false)
    setTimeout(() => {
      setCurrentIndex(nextIndex)
      setCardVisible(true)
    }, 150)
  }, [])

  // ── Track view + XP + discovery message ──────────────────────────────────

  useEffect(() => {
    if (!resource || viewedResources.current.has(resource.id)) return
    viewedResources.current.add(resource.id)
    setViewedIds(new Set(viewedResources.current))

    interactMutate(
      {
        session_id:         session.session_id,
        resource_id:        resource.id,
        interaction_type:   'view',
        time_spent_seconds: 0,
      },
      {
        onSuccess: (result) => {
          if (result.xp_delta > 0) {
            setCurrentXp(result.xp_total)
            setXpDelta(result.xp_delta)
            clearTimeout(xpTimer.current)
            xpTimer.current = setTimeout(() => setXpDelta(null), 2200)
          }
          if (result.badge) {
            setSessionBadges(prev =>
              prev.find(b => b.slug === result.badge!.slug) ? prev : [...prev, result.badge!],
            )
            setNewBadgeSlug(result.badge.slug)
            setTimeout(() => setNewBadgeSlug(null), 3000)
          }
        },
      },
    )

    // Discovery message (skip on first resource — it fires immediately on mount)
    if (currentIndex > 0) {
      setDiscoveryMsg('✓ Nueva evidencia encontrada')
      clearTimeout(discoveryTimer.current)
      discoveryTimer.current = setTimeout(() => setDiscoveryMsg(null), 2500)
    }

    onProgress?.(currentIndex)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex])

  // ── Navigation ────────────────────────────────────────────────────────────

  const goNext = useCallback(() => {
    if (currentIndex < total - 1) changeResource(currentIndex + 1)
  }, [currentIndex, total, changeResource])

  const goPrev = useCallback(() => {
    if (currentIndex > 0) changeResource(currentIndex - 1)
  }, [currentIndex, changeResource])

  // ── Complete / Skip ───────────────────────────────────────────────────────

  const handleComplete = useCallback(() => {
    completeMutate(
      { session_id: session.session_id, skipped: false },
      {
        onSuccess: (result) => {
          // Show celebration overlay; onComplete fires after student dismisses it
          setCompletionResult(result)
        },
        onError: () => onComplete(),
      },
    )
  }, [session.session_id, completeMutate, onComplete])

  const handleSkip = useCallback(() => {
    completeMutate(
      { session_id: session.session_id, skipped: true },
      {
        onSuccess: () => onSkip(),
        onError:   () => onSkip(),
      },
    )
  }, [session.session_id, completeMutate, onSkip])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <>
    {completionResult && (
      <EngageCompletionCelebration
        result={completionResult}
        initialXp={session.xp_earned}
        onContinue={onComplete}
      />
    )}
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6 animate-in fade-in duration-500">

      {/* ── Mission header ──────────────────────────────────────────────── */}
      <div className="space-y-3">
        {/* Row 1: label + XP level bar */}
        <div className="flex items-start justify-between gap-4">
          <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest pt-0.5 shrink-0">
            🚀 Misión de descubrimiento
          </p>
          <div className="flex-1 max-w-[200px] space-y-0.5">
            <XpLevelBar xp={currentXp} />
            <div className="h-4 text-right">
              {xpDelta !== null && <XpFlash delta={xpDelta} />}
            </div>
          </div>
        </div>

        {/* Row 2: badges earned so far */}
        {sessionBadges.length > 0 && (
          <BadgeShelf badges={sessionBadges} newBadgeSlug={newBadgeSlug} />
        )}

        {/* Row 3: mission objective box */}
        {resources.length > 0 && (
          <div className="flex items-start gap-2 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
            <Target className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <div>
              <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-0.5">
                Objetivo de la misión
              </p>
              <p className="text-sm text-foreground leading-snug">
                {getMissionObjective(resources)}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* ── Investigation progress ───────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            Investigación {currentIndex + 1}/{total}
          </span>
          {discoveryMsg && (
            <span className="text-xs text-green-600 font-semibold animate-in fade-in slide-in-from-right-2 duration-300">
              {discoveryMsg}
            </span>
          )}
        </div>

        {/* Investigation dots */}
        <div className="flex items-center gap-2">
          {resources.map((r, i) => (
            <InvestigationDot
              key={r.id}
              index={i}
              isCurrent={i === currentIndex}
              isViewed={viewedIds.has(r.id)}
            />
          ))}
          <div className="flex-1 h-px bg-border mx-1" />
          <div className="flex items-center gap-1 text-xs text-muted-foreground whitespace-nowrap">
            <Check className="h-3 w-3 text-green-500" />
            {viewedIds.size}/{total} pistas
          </div>
        </div>
      </div>

      {/* ── Resource card ────────────────────────────────────────────────── */}
      <div className={cn('transition-opacity duration-150', cardVisible ? 'opacity-100' : 'opacity-0')}>
        {resource && (
          <ResourceFrame resource={resource} index={currentIndex} total={total}>
            <ResourceCard resource={resource} sessionId={session.session_id} />
          </ResourceFrame>
        )}
      </div>

      {/* ── Navigation ───────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={goPrev}
            disabled={currentIndex === 0 || isCompleting}
            className="gap-1"
          >
            <ChevronLeft className="h-4 w-4" />
            Anterior
          </Button>
        </div>

        <div className="flex items-center gap-2">
          {isLast ? (
            <Button
              size="sm"
              onClick={handleComplete}
              disabled={isCompleting}
              className="gap-2 bg-primary hover:bg-primary/90 shadow-md shadow-primary/25 transition-all"
            >
              {isCompleting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Unlock className="h-4 w-4" />
              )}
              {isCompleting ? 'Desbloqueando...' : 'Desbloquear módulo'}
            </Button>
          ) : (
            <Button
              size="sm"
              onClick={goNext}
              disabled={isCompleting}
              className="gap-1.5"
            >
              Descubrir otra pista
              <ChevronRight className="h-4 w-4" />
            </Button>
          )}

          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground gap-1 text-xs"
            onClick={handleSkip}
            disabled={isCompleting}
          >
            <SkipForward className="h-3.5 w-3.5" />
            Saltar
          </Button>
        </div>
      </div>
    </div>
    </>
  )
}
