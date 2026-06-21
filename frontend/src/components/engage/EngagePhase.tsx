import { useState, useEffect, useRef, useCallback } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  SkipForward,
  CheckCircle,
  Lightbulb,
  HelpCircle,
  Newspaper,
  Brain,
  Zap,
  Loader2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { useInteractEngagement, useCompleteEngagement } from '@/hooks/useEngagement'
import type { EngagementSession, EngagementResource } from '@/types/engagement'

// ── Helpers ──────────────────────────────────────────────────────────────────

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

function ResourceBadge({ type }: { type: string }) {
  const Icon = RESOURCE_ICONS[type] ?? Lightbulb
  return (
    <Badge variant="secondary" className="gap-1.5 text-xs px-2 py-1">
      <Icon className="h-3 w-3" />
      {RESOURCE_LABELS[type] ?? type}
    </Badge>
  )
}

// ── Placeholder renderer (Sprint A — replaced by real cards in Sprint C) ────

function ResourceRenderer({ resource }: { resource: EngagementResource }) {
  const meta = resource.resource_metadata as Record<string, unknown>

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <ResourceBadge type={resource.resource_type} />
        {resource.is_interactive && (
          <Badge variant="outline" className="text-xs">Interactivo</Badge>
        )}
      </div>

      <h2 className="text-xl font-semibold leading-snug">{resource.title}</h2>

      <p className="text-muted-foreground leading-relaxed">{resource.content}</p>

      {/* Mini quiz placeholder */}
      {resource.resource_type === 'mini_quiz' && meta.options && (
        <div className="space-y-2 mt-4">
          <p className="text-sm font-medium text-muted-foreground">Opciones:</p>
          {(meta.options as string[]).map((opt, i) => (
            <div
              key={i}
              className="text-sm px-4 py-2 rounded-md border border-border bg-muted/40"
            >
              {String.fromCharCode(65 + i)}. {opt}
            </div>
          ))}
          <p className="text-xs text-muted-foreground italic mt-2">
            (Interacción completa disponible en Sprint C)
          </p>
        </div>
      )}

      {/* Short challenge placeholder */}
      {resource.resource_type === 'short_challenge' && meta.prompt && (
        <div className="mt-4 p-4 rounded-md border border-primary/20 bg-primary/5">
          <p className="text-sm font-medium mb-1">Desafío:</p>
          <p className="text-sm">{String(meta.prompt)}</p>
          {meta.hint && (
            <p className="text-xs text-muted-foreground mt-2">
              Pista: {String(meta.hint)}
            </p>
          )}
          <p className="text-xs text-muted-foreground italic mt-2">
            (Área de respuesta disponible en Sprint C)
          </p>
        </div>
      )}
    </div>
  )
}

// ── Types ─────────────────────────────────────────────────────────────────────

type EngageState = 'active' | 'completing' | 'error'

interface Props {
  session: EngagementSession
  onComplete: () => void
  onSkip: () => void
  onProgress?: (index: number) => void
}

// ── Component ─────────────────────────────────────────────────────────────────

export function EngagePhase({ session, onComplete, onSkip, onProgress }: Props) {
  const [currentIndex, setCurrentIndex] = useState(0)
  const [engageState, setEngageState] = useState<EngageState>('active')
  const viewedResources = useRef(new Set<string>())

  const { mutate: interactMutate } = useInteractEngagement()
  const { mutate: completeMutate, isPending: isCompleting } = useCompleteEngagement()

  const resources = session.resources
  const total     = resources.length
  const resource  = resources[currentIndex]
  const isLast    = currentIndex === total - 1

  // ── Track view interaction once per resource ─────────────────────────────

  useEffect(() => {
    if (!resource || viewedResources.current.has(resource.id)) return
    viewedResources.current.add(resource.id)
    interactMutate({
      session_id:       session.session_id,
      resource_id:      resource.id,
      interaction_type: 'view',
      time_spent_seconds: 0,
    })
    onProgress?.(currentIndex)
  }, [currentIndex, resource, session.session_id, interactMutate, onProgress])

  // ── Navigation ────────────────────────────────────────────────────────────

  const goNext = useCallback(() => {
    if (currentIndex < total - 1) setCurrentIndex(i => i + 1)
  }, [currentIndex, total])

  const goPrev = useCallback(() => {
    if (currentIndex > 0) setCurrentIndex(i => i - 1)
  }, [currentIndex])

  // ── Complete / Skip ───────────────────────────────────────────────────────

  const handleComplete = useCallback(() => {
    setEngageState('completing')
    completeMutate(
      { session_id: session.session_id, skipped: false },
      {
        onSuccess: () => onComplete(),
        onError:   () => {
          setEngageState('error')
          // Don't block the student — surface error via toast (handled in hook)
          onComplete()
        },
      }
    )
  }, [session.session_id, completeMutate, onComplete])

  const handleSkip = useCallback(() => {
    setEngageState('completing')
    completeMutate(
      { session_id: session.session_id, skipped: true },
      {
        onSuccess: () => onSkip(),
        onError:   () => onSkip(),
      }
    )
  }, [session.session_id, completeMutate, onSkip])

  // ── Render ────────────────────────────────────────────────────────────────

  const progressPct = ((currentIndex + 1) / total) * 100

  return (
    <div className="max-w-2xl mx-auto py-6 px-4 space-y-6">

      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-mono text-muted-foreground uppercase tracking-wider">
              Fase Engage
            </p>
            <h1 className="text-lg font-semibold mt-0.5">Misión de Descubrimiento</h1>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="text-muted-foreground gap-1.5"
            onClick={handleSkip}
            disabled={isCompleting}
          >
            <SkipForward className="h-3.5 w-3.5" />
            Saltar esta fase
          </Button>
        </div>

        {/* Progress */}
        <div className="space-y-1">
          <Progress value={progressPct} className="h-1.5" />
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Recurso {currentIndex + 1} de {total}</span>
            <span>{Math.round(progressPct)}% completado</span>
          </div>
        </div>
      </div>

      {/* Resource card (placeholder until Sprint C) */}
      <div className="rounded-xl border border-border bg-card p-6 min-h-[280px]">
        {resource ? <ResourceRenderer resource={resource} /> : null}
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={goPrev}
          disabled={currentIndex === 0 || isCompleting}
          className="gap-1.5"
        >
          <ChevronLeft className="h-4 w-4" />
          Anterior
        </Button>

        {isLast ? (
          <Button
            size="sm"
            onClick={handleComplete}
            disabled={isCompleting}
            className="gap-1.5"
          >
            {isCompleting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4" />
            )}
            {isCompleting ? 'Completando...' : '¡Completar y continuar!'}
          </Button>
        ) : (
          <Button
            size="sm"
            onClick={goNext}
            disabled={isCompleting}
            className="gap-1.5"
          >
            Siguiente
            <ChevronRight className="h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  )
}
