import { useState, useRef, useCallback } from 'react'
import { Send, Lightbulb, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useInteractEngagement } from '@/hooks/useEngagement'
import type { EngagementResource } from '@/types/engagement'

type CardState = 'question' | 'submitting' | 'submitted'

interface Props {
  resource: EngagementResource
  sessionId: string
}

/**
 * DetonatingQuestionCard — Sprint C2
 *
 * Presents a provocative question, collects the student's hypothesis, and
 * creates a cognitive tension that motivates engagement with the module.
 *
 * Hypothesis is stored in engagement_interactions.response_data:
 *   { hypothesis: "..." }
 *
 * The question text comes from resource.title; context from resource.content.
 */
export function DetonatingQuestionCard({ resource, sessionId }: Props) {
  const [cardState, setCardState]       = useState<CardState>('question')
  const [hypothesis, setHypothesis]     = useState('')
  const [savedHypothesis, setSaved]     = useState('')
  const startTimeRef                    = useRef(Date.now())
  const { mutate: interactMutate }      = useInteractEngagement()

  const handleSubmit = useCallback(() => {
    const trimmed = hypothesis.trim()
    if (!trimmed) return

    const secondsSpent = Math.round((Date.now() - startTimeRef.current) / 1000)
    setCardState('submitting')

    interactMutate(
      {
        session_id:         sessionId,
        resource_id:        resource.id,
        interaction_type:   'answer',
        time_spent_seconds: secondsSpent,
        response_data:      { hypothesis: trimmed },
      },
      {
        onSuccess: () => {
          setSaved(trimmed)
          setCardState('submitted')
        },
        onError: () => {
          // Still show confirmation — don't block the student on network errors
          setSaved(trimmed)
          setCardState('submitted')
        },
      },
    )
  }, [hypothesis, sessionId, resource.id, interactMutate])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
    },
    [handleSubmit],
  )

  // ── Submitted state ──────────────────────────────────────────────────────

  if (cardState === 'submitted') {
    return (
      <div className="relative overflow-hidden rounded-xl border border-emerald-200 dark:border-emerald-800 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-950/30 dark:to-teal-950/30 p-6 space-y-5 animate-in fade-in duration-500">
        <div className="pointer-events-none absolute -top-8 -right-10 w-36 h-36 rounded-full bg-emerald-200/30 dark:bg-emerald-500/10" />

        <div className="relative flex items-center gap-3">
          <span className="text-3xl select-none">💡</span>
          <div>
            <p className="text-xs font-mono font-bold tracking-widest text-emerald-600 dark:text-emerald-400 uppercase">
              Hipótesis registrada
            </p>
            <p className="text-xs text-emerald-700/60 dark:text-emerald-400/50 mt-0.5">
              Tu idea quedó guardada
            </p>
          </div>
        </div>

        <div className="relative rounded-lg border border-emerald-200 dark:border-emerald-700 bg-white/70 dark:bg-emerald-950/20 px-4 py-3">
          <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 mb-1">
            Tu hipótesis:
          </p>
          <p className="text-sm text-gray-800 dark:text-gray-200 italic leading-relaxed">
            "{savedHypothesis}"
          </p>
        </div>

        <p className="relative text-sm text-emerald-800 dark:text-emerald-300 leading-relaxed">
          A lo largo de este módulo descubrirás si tu respuesta estaba cerca de la realidad.
          La tensión cognitiva que sientes ahora es parte del aprendizaje.
        </p>
      </div>
    )
  }

  // ── Question state ───────────────────────────────────────────────────────

  return (
    <div className="relative overflow-hidden rounded-xl border border-indigo-200 dark:border-indigo-800 bg-gradient-to-br from-indigo-50 via-violet-50 to-purple-50 dark:from-indigo-950/30 dark:via-violet-950/30 dark:to-purple-950/20 p-6 space-y-5">
      <div className="pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full bg-indigo-200/30 dark:bg-indigo-500/10" />
      <div className="pointer-events-none absolute -bottom-14 -left-8 w-48 h-48 rounded-full bg-purple-200/20 dark:bg-purple-500/10" />

      {/* Header */}
      <div className="relative flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🤔</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-indigo-600 dark:text-indigo-400 uppercase">
            Pregunta de investigación
          </p>
          <p className="text-xs text-indigo-700/60 dark:text-indigo-400/50 mt-0.5">
            Reflexiona antes de continuar
          </p>
        </div>
      </div>

      {/* The question */}
      <div className="relative">
        <p className="text-lg sm:text-xl font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {resource.title}
        </p>
        {resource.content && resource.content !== resource.title && (
          <p className="text-sm text-indigo-700/70 dark:text-indigo-300/60 mt-2 leading-relaxed">
            {resource.content}
          </p>
        )}
      </div>

      {/* Divider */}
      <div className="relative h-px bg-indigo-200/60 dark:bg-indigo-700/40" />

      {/* Hypothesis input */}
      <div className="relative space-y-2">
        <label className="text-xs font-semibold text-indigo-700 dark:text-indigo-400 flex items-center gap-1.5">
          <span>✍️</span>
          <span>Tu hipótesis</span>
        </label>
        <textarea
          value={hypothesis}
          onChange={e => setHypothesis(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Escribe tu idea aquí... ¿Qué crees que hay detrás de esta pregunta?"
          rows={3}
          disabled={cardState === 'submitting'}
          className={cn(
            'w-full resize-none rounded-lg border border-indigo-200 dark:border-indigo-700',
            'bg-white/80 dark:bg-indigo-950/30',
            'px-3 py-2.5 text-sm text-gray-800 dark:text-gray-100',
            'placeholder:text-indigo-400/60 dark:placeholder:text-indigo-400/40',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-colors',
          )}
        />
        <p className="text-xs text-indigo-600/50 dark:text-indigo-400/40">
          Ctrl+Enter para enviar
        </p>
      </div>

      {/* Submit button */}
      <Button
        onClick={handleSubmit}
        disabled={!hypothesis.trim() || cardState === 'submitting'}
        className="w-full gap-2 bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 dark:shadow-indigo-900/30"
      >
        {cardState === 'submitting' ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Send className="h-4 w-4" />
        )}
        {cardState === 'submitting' ? 'Guardando...' : 'Registrar mi hipótesis'}
      </Button>

      <p className="relative text-xs text-indigo-600/50 dark:text-indigo-400/40 text-center">
        No hay respuestas correctas — solo hipótesis que el módulo irá confirmando o desafiando.
      </p>
    </div>
  )
}
