import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  SkipForward,
  Unlock,
  Lightbulb,
  HelpCircle,
  Newspaper,
  Brain,
  Zap,
  Loader2,
  Check,
  Star,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useInteractEngagement, useCompleteEngagement } from '@/hooks/useEngagement'
import type { EngagementSession, EngagementResource } from '@/types/engagement'

// ── Resource metadata ────────────────────────────────────────────────────────

const RESOURCE_ICONS: Record<string, React.ElementType> = {
  did_you_know:        Lightbulb,
  detonating_question: HelpCircle,
  real_news:           Newspaper,
  mini_quiz:           Brain,
  short_challenge:     Zap,
}

const RESOURCE_LABELS: Record<string, string> = {
  did_you_know:        '¿Sabías que...?',
  detonating_question: 'Pregunta detonante',
  real_news:           'Noticia real',
  mini_quiz:           'Mini quiz',
  short_challenge:     'Desafío corto',
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
    <span className="inline-flex items-center gap-0.5 text-amber-500 font-semibold text-sm animate-in fade-in slide-in-from-bottom-2 duration-300">
      +{delta} XP
    </span>
  )
}

// ── Resource badge ───────────────────────────────────────────────────────────

function ResourceBadge({ type }: { type: string }) {
  const Icon = RESOURCE_ICONS[type] ?? Lightbulb
  return (
    <Badge variant="secondary" className="gap-1.5 text-xs px-2.5 py-1">
      <Icon className="h-3 w-3" />
      {RESOURCE_LABELS[type] ?? type}
    </Badge>
  )
}

// ── Placeholder renderer (replaced by real cards in Sprint C) ────────────────

function ResourceRenderer({ resource }: { resource: EngagementResource }) {
  const meta = resource.resource_metadata as Record<string, unknown>

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <ResourceBadge type={resource.resource_type} />
        {resource.is_interactive && (
          <Badge variant="outline" className="text-xs text-primary border-primary/40">
            Interactivo
          </Badge>
        )}
      </div>

      <h2 className="text-xl font-semibold leading-snug">{resource.title}</h2>

      <p className="text-muted-foreground leading-relaxed">{resource.content}</p>

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
          <p className="text-xs text-muted-foreground italic mt-2">
            (Interacción completa disponible en Sprint C)
          </p>
        </div>
      )}

      {resource.resource_type === 'short_challenge' && meta.prompt && (
        <div className="mt-4 p-4 rounded-xl border border-primary/20 bg-primary/5">
          <p className="text-sm font-semibold mb-1.5">Tu desafío:</p>
          <p className="text-sm">{String(meta.prompt)}</p>
          {meta.hint && (
            <p className="text-xs text-muted-foreground mt-2">
              Pista: {String(meta.hint)}
            </p>
          )}
          <p className="text-xs text-muted-foreground italic mt-3">
            (Área de respuesta disponible en Sprint C)
          </p>
        </div>
      )}

      {resource.resource_type === 'real_news' && meta.source_hint && (
        <p className="text-xs text-muted-foreground border-l-2 border-border pl-3 italic">
          Fuente: {String(meta.source_hint)}
          {meta.year ? ` · ${meta.year}` : ''}
        </p>
      )}
    </div>
  )
}

// ── Types ────────────────────────────────────────────────────────────────────

type EngageState = 'active' | 'completing' | 'error'

interface Props {
  session: EngagementSession
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
  /** Optional context title shown as mission subtitle. */
  missionTitle?: string
}

// ── Component ─────────────────────────────────────────────────────────────────

export function EngagePhase({ session, onComplete, onSkip, onProgress, missionTitle }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [engageState, setEngageState] = useState<EngageState>('active')
  const [currentXp, setCurrentXp]     = useState(session.xp_earned)
  const [xpDelta, setXpDelta]         = useState<number | null>(null)
  const [discoveryMsg, setDiscoveryMsg] = useState<string | null>(null)
  const [cardVisible, setCardVisible]  = useState(true)
  // Tracks viewed IDs for dot rendering (state so re-render fires)
  const [viewedIds, setViewedIds]      = useState<Set<string>>(new Set())
  const viewedResources = useRef(new Set<string>())
  const xpTimer         = useRef<ReturnType<typeof setTimeout>>()
  const discoveryTimer  = useRef<ReturnType<typeof setTimeout>>()

  const { mutate: interactMutate } = useInteractEngagement()
  const { mutate: completeMutate, isPending: isCompleting } = useCompleteEngagement()

  const resources = session.resources
  const total     = resources.length
  const resource  = resources[currentIndex]
  const isLast    = currentIndex === total - 1

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
    setEngageState('completing')
    completeMutate(
      { session_id: session.session_id, skipped: false },
      {
        onSuccess: (result) => {
          setCurrentXp(result.xp_earned)
          onComplete()
        },
        onError: () => {
          setEngageState('error')
          onComplete()
        },
      },
    )
  }, [session.session_id, completeMutate, onComplete])

  const handleSkip = useCallback(() => {
    setEngageState('completing')
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
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6 animate-in fade-in duration-500">

      {/* ── Mission header ──────────────────────────────────────────────── */}
      <div className="space-y-1">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-0.5">
            <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">
              Misión de descubrimiento
            </p>
            {missionTitle && (
              <p className="text-sm text-muted-foreground leading-snug max-w-md">
                {missionTitle}
              </p>
            )}
          </div>

          {/* XP counter */}
          <div className="flex flex-col items-end shrink-0">
            <div className="flex items-center gap-1 text-amber-500">
              <Star className="h-3.5 w-3.5 fill-amber-400" />
              <span className="text-sm font-semibold tabular-nums">{currentXp} XP</span>
            </div>
            <div className="h-4">
              {xpDelta !== null && <XpFlash delta={xpDelta} />}
            </div>
          </div>
        </div>
      </div>

      {/* ── Investigation progress ───────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-muted-foreground">
            Investigación {currentIndex + 1}/{total}
          </span>
          {discoveryMsg && (
            <span className="text-xs text-green-600 font-medium animate-in fade-in slide-in-from-right-2 duration-300">
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
      <div
        className={cn(
          'rounded-xl border border-border bg-card p-6 min-h-[280px] transition-opacity duration-150',
          cardVisible ? 'opacity-100' : 'opacity-0',
        )}
      >
        {resource ? <ResourceRenderer resource={resource} /> : null}
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
  )
}
