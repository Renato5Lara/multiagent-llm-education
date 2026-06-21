import { useState, useRef, useCallback, useEffect } from 'react'
import { Check, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useInteractEngagement } from '@/hooks/useEngagement'
import type { EngagementResource, MiniQuizMetadata } from '@/types/engagement'

type QuizState = 'idle' | 'answered'

const OPTION_LETTERS = ['A', 'B', 'C', 'D', 'E']

interface Props {
  resource: EngagementResource
  sessionId: string
}

/**
 * MiniQuizCard — Sprint C4
 *
 * Interactive quiz card with immediate local feedback.
 * Correctness is computed from resource_metadata.correct_index (no round-trip wait).
 * Backend is called in the background for XP and analytics.
 *
 * response_data: { selected_index: number, is_correct: boolean }
 */
export function MiniQuizCard({ resource, sessionId }: Props) {
  const meta      = resource.resource_metadata as MiniQuizMetadata
  const options   = meta?.options ?? []
  const question  = (resource.resource_metadata as Record<string, unknown>).question
    ? String((resource.resource_metadata as Record<string, unknown>).question)
    : null

  const [quizState, setQuizState]   = useState<QuizState>('idle')
  const [selectedIdx, setSelected]  = useState<number | null>(null)
  const [pendingIdx, setPending]     = useState<number | null>(null)
  const [isCorrect, setIsCorrect]   = useState<boolean | null>(null)
  const [xpDelta, setXpDelta]       = useState<number | null>(null)
  const [showXp, setShowXp]         = useState(false)
  const startTimeRef                = useRef(Date.now())
  const xpTimer                     = useRef<ReturnType<typeof setTimeout>>()

  const { mutate: interactMutate } = useInteractEngagement()

  // Clean up timer on unmount
  useEffect(() => () => clearTimeout(xpTimer.current), [])

  const handleConfirm = useCallback(() => {
    if (pendingIdx === null) return

    // Compute correctness immediately from metadata (no wait for server)
    const correct = pendingIdx === meta.correct_index
    setSelectedIdx(pendingIdx)
    setIsCorrect(correct)
    setQuizState('answered')

    const secondsSpent = Math.round((Date.now() - startTimeRef.current) / 1000)

    interactMutate(
      {
        session_id:         sessionId,
        resource_id:        resource.id,
        interaction_type:   'answer',
        time_spent_seconds: secondsSpent,
        response_data:      { selected_index: pendingIdx, is_correct: correct },
      },
      {
        onSuccess: (result) => {
          if (result.xp_delta > 0) {
            setXpDelta(result.xp_delta)
            setShowXp(true)
            clearTimeout(xpTimer.current)
            xpTimer.current = setTimeout(() => setShowXp(false), 2200)
          }
        },
      },
    )
  }, [pendingIdx, meta.correct_index, sessionId, resource.id, interactMutate])

  // ── Option styling helpers ───────────────────────────────────────────────

  function getOptionStyle(i: number): string {
    if (quizState === 'idle') {
      return pendingIdx === i
        ? 'border-violet-500 bg-violet-100 dark:bg-violet-900/40 text-violet-800 dark:text-violet-200 shadow-sm'
        : 'border-violet-200 dark:border-violet-700 hover:border-violet-400 hover:bg-violet-50 dark:hover:bg-violet-900/20 cursor-pointer'
    }
    // answered state
    if (i === meta.correct_index) {
      return 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-800 dark:text-emerald-200'
    }
    if (i === selectedIdx && !isCorrect) {
      return 'border-rose-400 bg-rose-50 dark:bg-rose-900/20 text-rose-700 dark:text-rose-300 opacity-80'
    }
    return 'border-gray-200 dark:border-gray-700 opacity-50'
  }

  function getOptionIcon(i: number) {
    if (quizState !== 'answered') return null
    if (i === meta.correct_index) return <Check className="h-4 w-4 text-emerald-600 shrink-0" />
    if (i === selectedIdx && !isCorrect) return <X className="h-4 w-4 text-rose-500 shrink-0" />
    return null
  }

  // ── Background for answered state ────────────────────────────────────────

  const cardBg = quizState === 'answered'
    ? isCorrect
      ? 'border-emerald-200 dark:border-emerald-800 bg-gradient-to-br from-emerald-50 via-teal-50 to-green-50 dark:from-emerald-950/30 dark:via-teal-950/20 dark:to-green-950/20'
      : 'border-rose-200 dark:border-rose-800 bg-gradient-to-br from-rose-50 via-orange-50 to-amber-50 dark:from-rose-950/30 dark:via-orange-950/20 dark:to-amber-950/20'
    : 'border-violet-200 dark:border-violet-800 bg-gradient-to-br from-violet-50 via-purple-50 to-fuchsia-50 dark:from-violet-950/30 dark:via-purple-950/20 dark:to-fuchsia-950/20'

  return (
    <div className={cn('relative overflow-hidden rounded-xl border p-6 space-y-5 transition-colors duration-500', cardBg)}>
      <div className="pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full bg-violet-200/20 dark:bg-violet-500/10" />

      {/* XP float animation */}
      <style>{`
        @keyframes xp-float {
          0%   { transform: translateY(0);    opacity: 1; }
          80%  { transform: translateY(-36px); opacity: 0.8; }
          100% { transform: translateY(-52px); opacity: 0; }
        }
      `}</style>
      {showXp && xpDelta && (
        <span
          className="pointer-events-none absolute top-4 right-6 text-amber-500 font-bold text-base z-10"
          style={{ animation: 'xp-float 2s ease-out forwards' }}
        >
          ✨ +{xpDelta} XP
        </span>
      )}

      {/* Header */}
      <div className="relative flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🧩</span>
        <div>
          <p className={cn(
            'text-xs font-mono font-bold tracking-widest uppercase',
            quizState === 'answered'
              ? isCorrect ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400'
              : 'text-violet-600 dark:text-violet-400',
          )}>
            {quizState === 'answered'
              ? isCorrect ? '¡Correcto!' : 'Casi...'
              : 'Mini desafío'}
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {quizState === 'answered'
              ? isCorrect ? 'Sumaste puntos de experiencia' : 'La respuesta correcta fue otra'
              : 'Pon a prueba lo que ya intuyes'}
          </p>
        </div>
      </div>

      {/* Question */}
      <div className="relative">
        <p className="text-base sm:text-lg font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {question ?? resource.title}
        </p>
        {resource.content && resource.content !== resource.title && question == null && (
          <p className="text-sm text-muted-foreground mt-1.5 leading-relaxed">{resource.content}</p>
        )}
      </div>

      {/* Options */}
      <div className="relative space-y-2.5">
        {options.map((opt, i) => (
          <button
            key={i}
            type="button"
            disabled={quizState === 'answered'}
            onClick={() => quizState === 'idle' && setPending(i)}
            className={cn(
              'w-full text-left flex items-center gap-3 px-4 py-3 rounded-xl border-2 text-sm transition-all duration-200',
              getOptionStyle(i),
              quizState === 'answered' && 'cursor-default',
            )}
          >
            {/* Letter badge */}
            <span className={cn(
              'shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold border transition-colors',
              quizState === 'idle' && pendingIdx === i
                ? 'border-violet-500 bg-violet-500 text-white'
                : quizState === 'answered' && i === meta.correct_index
                ? 'border-emerald-500 bg-emerald-500 text-white'
                : quizState === 'answered' && i === selectedIdx && !isCorrect
                ? 'border-rose-400 bg-rose-400 text-white'
                : 'border-current text-current',
            )}>
              {OPTION_LETTERS[i]}
            </span>

            <span className="flex-1">{opt}</span>

            {getOptionIcon(i)}
          </button>
        ))}
      </div>

      {/* Confirm button (idle) or Explanation (answered) */}
      {quizState === 'idle' ? (
        <Button
          onClick={handleConfirm}
          disabled={pendingIdx === null}
          className="w-full gap-2 bg-violet-600 hover:bg-violet-700 text-white shadow-md shadow-violet-200 dark:shadow-violet-900/30"
        >
          Confirmar respuesta
        </Button>
      ) : (
        meta.explanation && (
          <div className={cn(
            'relative rounded-xl border px-5 py-4 space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-400',
            isCorrect
              ? 'border-emerald-200 dark:border-emerald-700 bg-white/70 dark:bg-emerald-950/20'
              : 'border-amber-200 dark:border-amber-700 bg-white/70 dark:bg-amber-950/20',
          )}>
            {/* Conversational lead */}
            <p className={cn(
              'text-sm font-semibold',
              isCorrect ? 'text-emerald-700 dark:text-emerald-400' : 'text-amber-700 dark:text-amber-400',
            )}>
              {isCorrect ? '🎉 ¡Exacto!' : '🤔 Casi...'}
            </p>

            {/* Explanation */}
            <div className="space-y-1">
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                {isCorrect ? 'Porque...' : '¿Por qué?'}
              </p>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {meta.explanation}
              </p>
            </div>

            {/* Separator + fun fact field (if present in metadata) */}
            {(resource.resource_metadata as Record<string, unknown>).fun_fact && (
              <>
                <div className="h-px bg-border" />
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">
                    ¿Sabías que...?
                  </p>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                    {String((resource.resource_metadata as Record<string, unknown>).fun_fact)}
                  </p>
                </div>
              </>
            )}
          </div>
        )
      )}
    </div>
  )
}
