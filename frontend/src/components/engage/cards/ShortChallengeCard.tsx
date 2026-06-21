import { useState, useRef, useCallback, useEffect } from 'react'
import { Lightbulb, Send, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useInteractEngagement } from '@/hooks/useEngagement'
import type { EngagementResource, ShortChallengeMetadata } from '@/types/engagement'

type ChallengeState = 'idle' | 'submitting' | 'submitted'

// score thresholds
const TIERS = [
  { min: 0.67, emoji: '🏆', label: 'Excelente',        msg: 'Tu respuesta cubre los conceptos fundamentales del tema.' },
  { min: 0.33, emoji: '🚀', label: 'Buena respuesta',  msg: 'Vas en la dirección correcta. El módulo reforzará estas ideas.' },
  { min: 0,    emoji: '🌱', label: 'Buen inicio',      msg: 'Identificaste algunas ideas clave. Seguir explorando ampliará tu respuesta.' },
]

function getTier(score: number) {
  return TIERS.find(t => score >= t.min) ?? TIERS[TIERS.length - 1]
}

/**
 * Soft keyword match: case-insensitive, diacritic-normalized, substring.
 * Returns the set of keywords found in the answer text.
 */
function matchKeywords(answer: string, keywords: string[]): Set<string> {
  const normalize = (s: string) =>
    s.toLowerCase()
     .normalize('NFD')
     .replace(/[̀-ͯ]/g, '')
     .trim()
  const normalizedAnswer = normalize(answer)
  return new Set(keywords.filter(kw => normalizedAnswer.includes(normalize(kw))))
}

interface Props {
  resource: EngagementResource
  sessionId: string
}

/**
 * ShortChallengeCard — Sprint C5
 *
 * Free-text challenge with soft keyword matching against expected_keywords.
 * score = keywords_found / keywords_total (0–1).
 * response_data: { answer, keyword_matches, score }
 *
 * Hint toggle encourages attempting the challenge before reading the hint.
 */
export function ShortChallengeCard({ resource, sessionId }: Props) {
  const meta     = resource.resource_metadata as ShortChallengeMetadata & Record<string, unknown>
  const prompt   = meta.prompt ?? resource.title
  const hint     = meta.hint ?? null
  const keywords = (meta.expected_keywords ?? []) as string[]

  const [state, setState]           = useState<ChallengeState>('idle')
  const [answer, setAnswer]         = useState('')
  const [showHint, setShowHint]     = useState(false)
  const [xpDelta, setXpDelta]       = useState<number | null>(null)
  const [showXp, setShowXp]         = useState(false)
  const [foundKws, setFoundKws]     = useState<Set<string>>(new Set())
  const [score, setScore]           = useState(0)
  const [savedAnswer, setSaved]     = useState('')
  const startTimeRef                = useRef(Date.now())
  const xpTimer                     = useRef<ReturnType<typeof setTimeout>>()

  const { mutate: interactMutate } = useInteractEngagement()

  useEffect(() => () => clearTimeout(xpTimer.current), [])

  const handleSubmit = useCallback(() => {
    const trimmed = answer.trim()
    if (!trimmed) return

    const found    = matchKeywords(trimmed, keywords)
    const computed = keywords.length > 0 ? found.size / keywords.length : 1

    setFoundKws(found)
    setScore(computed)
    setSaved(trimmed)
    setState('submitting')

    const secondsSpent = Math.round((Date.now() - startTimeRef.current) / 1000)

    interactMutate(
      {
        session_id:         sessionId,
        resource_id:        resource.id,
        interaction_type:   'submit',
        time_spent_seconds: secondsSpent,
        response_data:      {
          answer:           trimmed,
          keyword_matches:  found.size,
          score:            Math.round(computed * 100) / 100,
        },
      },
      {
        onSuccess: (result) => {
          if (result.xp_delta > 0) {
            setXpDelta(result.xp_delta)
            setShowXp(true)
            clearTimeout(xpTimer.current)
            xpTimer.current = setTimeout(() => setShowXp(false), 2200)
          }
          setState('submitted')
        },
        onError: () => setState('submitted'),
      },
    )
  }, [answer, keywords, sessionId, resource.id, interactMutate])

  // ── Submitted state ──────────────────────────────────────────────────────

  if (state === 'submitted' || state === 'submitting') {
    const tier      = getTier(score)
    const missedKws = keywords.filter(kw => !foundKws.has(kw))

    return (
      <div className="relative overflow-hidden rounded-xl border border-amber-200 dark:border-amber-800 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 dark:from-amber-950/30 dark:via-yellow-950/20 dark:to-orange-950/20 p-6 space-y-4 animate-in fade-in duration-500">
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

        <div className="pointer-events-none absolute -top-8 -right-8 w-36 h-36 rounded-full bg-amber-200/30 dark:bg-amber-500/10" />

        {/* Header */}
        <div className="relative flex items-center gap-3">
          <span className="text-3xl select-none">{tier.emoji}</span>
          <div>
            <p className="text-xs font-mono font-bold tracking-widest text-amber-700 dark:text-amber-400 uppercase">
              {state === 'submitting' ? 'Procesando...' : 'Reto completado'}
            </p>
            {state === 'submitted' && keywords.length > 0 && (
              <p className="text-xs text-amber-700/60 dark:text-amber-400/50 mt-0.5">
                {foundKws.size} de {keywords.length} conceptos clave identificados
              </p>
            )}
          </div>
        </div>

        {/* Quoted answer */}
        <div className="relative rounded-lg border border-amber-200 dark:border-amber-700 bg-white/70 dark:bg-amber-950/20 px-4 py-3">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">Tu respuesta:</p>
          <p className="text-sm text-gray-800 dark:text-gray-200 italic leading-relaxed line-clamp-4">
            "{savedAnswer}"
          </p>
        </div>

        {/* Keyword breakdown */}
        {keywords.length > 0 && state === 'submitted' && (
          <div className="relative space-y-2">
            <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">Conceptos encontrados:</p>
            <div className="flex flex-wrap gap-2">
              {keywords.map(kw => (
                <span
                  key={kw}
                  className={cn(
                    'inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium border',
                    foundKws.has(kw)
                      ? 'border-emerald-300 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300'
                      : 'border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/30 text-gray-400 dark:text-gray-500',
                  )}
                >
                  {foundKws.has(kw) ? '✓' : '○'} {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Tier feedback */}
        {state === 'submitted' && (
          <div className="relative rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-100/50 dark:bg-amber-900/20 px-4 py-3 space-y-0.5 animate-in fade-in slide-in-from-bottom-2 duration-400">
            <p className="text-sm font-semibold text-amber-800 dark:text-amber-300">
              {tier.emoji} {tier.label}
            </p>
            <p className="text-sm text-amber-700 dark:text-amber-400/80 leading-relaxed">{tier.msg}</p>
          </div>
        )}
      </div>
    )
  }

  // ── Idle state ───────────────────────────────────────────────────────────

  return (
    <div className="relative overflow-hidden rounded-xl border border-amber-200 dark:border-amber-800 bg-gradient-to-br from-amber-50 via-yellow-50 to-orange-50 dark:from-amber-950/30 dark:via-yellow-950/20 dark:to-orange-950/20 p-6 space-y-5">
      <div className="pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full bg-amber-200/30 dark:bg-amber-500/10" />
      <div className="pointer-events-none absolute -bottom-14 -left-8 w-48 h-48 rounded-full bg-yellow-200/20 dark:bg-yellow-500/10" />

      {/* Header */}
      <div className="relative flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🏆</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-amber-700 dark:text-amber-400 uppercase">
            Reto final
          </p>
          <p className="text-xs text-amber-700/60 dark:text-amber-400/50 mt-0.5">
            Demuestra lo que ya intuyes
          </p>
        </div>
      </div>

      {/* Challenge prompt */}
      <div className="relative">
        <p className="text-base sm:text-lg font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {prompt}
        </p>
        {resource.content && resource.content !== resource.title && resource.content !== prompt && (
          <p className="text-sm text-amber-700/70 dark:text-amber-400/60 mt-2 leading-relaxed">
            {resource.content}
          </p>
        )}
      </div>

      {/* Hint toggle */}
      {hint && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowHint(v => !v)}
            className="flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 transition-colors"
          >
            <Lightbulb className="h-3.5 w-3.5" />
            {showHint ? 'Ocultar pista' : 'Ver una pista'}
          </button>
          {showHint && (
            <div className="mt-2 px-3 py-2 rounded-lg border border-amber-200 dark:border-amber-700 bg-amber-100/40 dark:bg-amber-900/20 animate-in fade-in slide-in-from-top-1 duration-200">
              <p className="text-xs text-amber-700 dark:text-amber-400 leading-relaxed">{hint}</p>
            </div>
          )}
        </div>
      )}

      <div className="relative h-px bg-amber-200/60 dark:bg-amber-700/40" />

      {/* Answer textarea */}
      <div className="relative space-y-2">
        <label className="text-xs font-semibold text-amber-700 dark:text-amber-400">
          Tu respuesta
        </label>
        <textarea
          value={answer}
          onChange={e => setAnswer(e.target.value)}
          placeholder="Escribe tu respuesta aquí. No hay respuestas perfectas — solo el inicio de tu comprensión."
          rows={4}
          className={cn(
            'w-full resize-none rounded-lg border border-amber-200 dark:border-amber-700',
            'bg-white/80 dark:bg-amber-950/30',
            'px-3 py-2.5 text-sm text-gray-800 dark:text-gray-100',
            'placeholder:text-amber-400/60 dark:placeholder:text-amber-400/40',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400',
            'transition-colors',
          )}
        />
        {keywords.length > 0 && (
          <p className="text-xs text-amber-600/50 dark:text-amber-400/40">
            Intenta incorporar conceptos del tema en tu respuesta.
          </p>
        )}
      </div>

      <Button
        onClick={handleSubmit}
        disabled={!answer.trim()}
        className="w-full gap-2 bg-amber-600 hover:bg-amber-700 text-white shadow-md shadow-amber-200 dark:shadow-amber-900/30"
      >
        <Send className="h-4 w-4" />
        Enviar respuesta
      </Button>
    </div>
  )
}
