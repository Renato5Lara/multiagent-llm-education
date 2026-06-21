import { useState, useCallback, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Loader2, ChevronRight } from 'lucide-react'
import { useInteractEngagement } from '@/hooks/useEngagement'
import type { EngagementResource } from '@/types/engagement'
import { cn } from '@/lib/utils'

type KnowledgeLevel = 'never_seen' | 'heard_about_it' | 'know_a_bit' | 'know_well'

const OPTIONS: { value: KnowledgeLevel; label: string; emoji: string; firstTime: boolean }[] = [
  { value: 'never_seen',     label: 'Nunca había escuchado de esto.',                  emoji: '🌱', firstTime: true  },
  { value: 'heard_about_it', label: 'Lo había escuchado, pero no sé de qué trata.',   emoji: '👂', firstTime: true  },
  { value: 'know_a_bit',     label: 'Sé un poco del tema.',                           emoji: '📖', firstTime: false },
  { value: 'know_well',      label: 'Ya tengo conocimientos del tema.',               emoji: '🎓', firstTime: false },
]

interface FeedbackDef {
  icon:     string
  headline: string
  body:     string
  bullets?: string[]
  closing?: string
}

const FEEDBACK: Record<KnowledgeLevel, FeedbackDef> = {
  never_seen: {
    icon:     '🌱',
    headline: 'Primera vez aquí.',
    body:     '¡Perfecto!\n\nNo necesitas saber nada antes de comenzar.\nEn este módulo descubrirás:',
    bullets:  ['qué es este concepto', 'dónde se utiliza', 'por qué es importante'],
    closing:  '🚀 Empecemos.',
  },
  heard_about_it: {
    icon:     '🧩',
    headline: 'Ya has oído hablar del tema.',
    body:     'Excelente.\n\nMientras avances, intenta conectar las nuevas ideas con aquello que ya conocías.',
  },
  know_a_bit: {
    icon:     '🚀',
    headline: 'Ya tienes algunas bases.',
    body:     'Veamos si este módulo puede ayudarte a profundizar y descubrir algo nuevo.',
  },
  know_well: {
    icon:     '🎯',
    headline: 'Ya tienes experiencia.',
    body:     'Te propongo un reto:\nidentifica qué conceptos nuevos o diferentes encuentras en este módulo.',
  },
}

interface Props {
  resource:  EngagementResource
  sessionId: string
  onAnswer?: () => void
}

/**
 * PriorKnowledgeCard — Sprint H1.1 + H1.2
 *
 * Autoevaluación de conocimiento previo al inicio del Engage.
 * Persiste { knowledge_level, first_time_topic } en response_data.
 * Muestra feedback adaptativo para los 4 niveles tras la selección.
 */
export function PriorKnowledgeCard({ resource, sessionId, onAnswer }: Props) {
  const [selected, setSelected]     = useState<KnowledgeLevel | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted]   = useState<KnowledgeLevel | null>(null)
  const startTimeRef                = useRef(Date.now())
  const { mutate: interactMutate }  = useInteractEngagement()

  const handleSubmit = useCallback(() => {
    if (!selected) return
    const opt = OPTIONS.find(o => o.value === selected)!
    const secondsSpent = Math.round((Date.now() - startTimeRef.current) / 1000)
    setSubmitting(true)

    interactMutate(
      {
        session_id:         sessionId,
        resource_id:        resource.id,
        interaction_type:   'answer',
        time_spent_seconds: secondsSpent,
        response_data: {
          knowledge_level:  selected,
          first_time_topic: opt.firstTime,
        },
      },
      {
        onSuccess: () => {
          sessionStorage.setItem(`engage:knowledge_level:${sessionId}`, selected)
          setSubmitting(false)
          setSubmitted(selected)
          onAnswer?.()
        },
        onError: () => {
          sessionStorage.setItem(`engage:knowledge_level:${sessionId}`, selected)
          setSubmitting(false)
          setSubmitted(selected)
          onAnswer?.()
        },
      },
    )
  }, [selected, sessionId, resource.id, interactMutate])

  // ── Estado: respuesta guardada ─────────────────────────────────────────────

  if (submitted) {
    const fb  = FEEDBACK[submitted]
    const opt = OPTIONS.find(o => o.value === submitted)!

    return (
      <div className="relative overflow-hidden rounded-xl border border-sky-200 dark:border-sky-800 bg-gradient-to-br from-sky-50 via-cyan-50 to-teal-50 dark:from-sky-950/30 dark:via-cyan-950/30 dark:to-teal-950/20 p-6 space-y-4 animate-in fade-in duration-500">
        <div className="pointer-events-none absolute -top-8 -right-10 w-36 h-36 rounded-full bg-sky-200/30 dark:bg-sky-500/10" />

        {/* Header */}
        <div className="relative flex items-center gap-3">
          <span className="text-3xl select-none">{fb.icon}</span>
          <div>
            <p className="text-xs font-mono font-bold tracking-widest text-sky-600 dark:text-sky-400 uppercase">
              Punto de partida registrado
            </p>
            <p className="text-sm font-semibold text-sky-800 dark:text-sky-300 mt-0.5">
              {fb.headline}
            </p>
          </div>
        </div>

        {/* Cuerpo adaptativo */}
        <div className="relative rounded-lg border border-sky-200 dark:border-sky-700 bg-white/70 dark:bg-sky-950/20 px-4 py-3 space-y-2">
          {fb.body.split('\n').map((line, i) =>
            line ? (
              <p
                key={i}
                className={cn(
                  'text-sm leading-relaxed',
                  i === 0
                    ? 'font-semibold text-sky-800 dark:text-sky-200'
                    : 'text-gray-700 dark:text-gray-300',
                )}
              >
                {line}
              </p>
            ) : (
              <div key={i} className="h-1" />
            ),
          )}

          {fb.bullets && (
            <ul className="space-y-1 pt-1">
              {fb.bullets.map(b => (
                <li key={b} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                  <span className="text-sky-500 font-bold shrink-0">✓</span>
                  {b}
                </li>
              ))}
            </ul>
          )}

          {fb.closing && (
            <p className="text-sm font-semibold text-sky-700 dark:text-sky-300 pt-1">
              {fb.closing}
            </p>
          )}
        </div>

        {/* Opción elegida */}
        <p className="relative text-xs text-sky-600/60 dark:text-sky-400/40 flex items-center gap-1.5">
          <span className="text-base">{opt.emoji}</span>
          <span>Tu respuesta: {opt.label}</span>
        </p>
      </div>
    )
  }

  // ── Estado: pregunta ───────────────────────────────────────────────────────

  return (
    <div className="relative overflow-hidden rounded-xl border border-sky-200 dark:border-sky-800 bg-gradient-to-br from-sky-50 via-cyan-50 to-teal-50 dark:from-sky-950/30 dark:via-cyan-950/20 dark:to-teal-950/10 p-6 space-y-5">
      <div className="pointer-events-none absolute -top-10 -right-10 w-40 h-40 rounded-full bg-sky-200/30 dark:bg-sky-500/10" />
      <div className="pointer-events-none absolute -bottom-14 -left-8 w-48 h-48 rounded-full bg-cyan-200/20 dark:bg-cyan-500/10" />

      {/* Header */}
      <div className="relative flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🧭</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-sky-600 dark:text-sky-400 uppercase">
            Punto de partida
          </p>
          <p className="text-xs text-sky-700/60 dark:text-sky-400/50 mt-0.5">
            Sin respuestas correctas — solo queremos conocerte
          </p>
        </div>
      </div>

      {/* Pregunta */}
      <div className="relative">
        <p className="text-lg sm:text-xl font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {resource.title}
        </p>
      </div>

      <div className="relative h-px bg-sky-200/60 dark:bg-sky-700/40" />

      {/* Opciones */}
      <div className="relative space-y-2">
        {OPTIONS.map(opt => (
          <button
            key={opt.value}
            type="button"
            onClick={() => setSelected(prev => prev === opt.value ? null : opt.value)}
            disabled={submitting}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-all duration-200',
              selected === opt.value
                ? 'border-sky-500 bg-sky-50 dark:bg-sky-900/40 shadow-sm shadow-sky-200/50 dark:shadow-sky-900/20'
                : 'border-sky-100 dark:border-sky-800 hover:border-sky-300 dark:hover:border-sky-600 hover:bg-sky-50/50 dark:hover:bg-sky-950/30',
              'disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            <span className="text-xl select-none shrink-0">{opt.emoji}</span>
            <span className={cn(
              'text-sm font-medium',
              selected === opt.value
                ? 'text-sky-800 dark:text-sky-200'
                : 'text-gray-700 dark:text-gray-300',
            )}>
              {opt.label}
            </span>
            {selected === opt.value && (
              <span className="ml-auto shrink-0 w-4 h-4 rounded-full bg-sky-500 flex items-center justify-center">
                <svg className="w-2.5 h-2.5 text-white" fill="currentColor" viewBox="0 0 8 8">
                  <path d="M6.564.75l-3.59 3.612-1.538-1.55L0 4.26l2.974 2.99L8 2.193z" />
                </svg>
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Submit */}
      <Button
        onClick={handleSubmit}
        disabled={!selected || submitting}
        className="w-full gap-2 bg-sky-600 hover:bg-sky-700 text-white shadow-md shadow-sky-200 dark:shadow-sky-900/30"
      >
        {submitting ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <ChevronRight className="h-4 w-4" />
        )}
        {submitting ? 'Guardando...' : 'Continuar'}
      </Button>

      <p className="relative text-xs text-sky-600/50 dark:text-sky-400/40 text-center">
        Tu respuesta es privada y ayuda a personalizar tu experiencia en este módulo.
      </p>
    </div>
  )
}
