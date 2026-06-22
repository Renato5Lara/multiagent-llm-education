import { useState } from 'react'
import { Send, Check } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { ConceptCard }              from '@/components/module/ConceptCard'
import { DidYouKnowInlineCard }     from '@/components/module/DidYouKnowInlineCard'
import { ExampleCard }              from '@/components/module/ExampleCard'
import { PracticalApplicationCard } from '@/components/module/PracticalApplicationCard'
import { ReflectionCheckpoint }     from '@/components/module/ReflectionCheckpoint'
import type {
  LearningJourneyStep  as StepData,
  EvaluationMeta,
  ChallengeMeta,
} from '@/types/learningJourney'

// ── Shared sub-renderer props ─────────────────────────────────────────────────

interface SubProps {
  step:       StepData
  onComplete: () => void
}

// ── prior_knowledge ───────────────────────────────────────────────────────────

const PRIOR_OPTIONS = [
  { value: 'never_seen',     label: 'Nunca había escuchado de esto.',                emoji: '🌱' },
  { value: 'heard_about_it', label: 'Lo había escuchado, pero no sé de qué trata.', emoji: '👂' },
  { value: 'know_a_bit',     label: 'Sé un poco del tema.',                         emoji: '📖' },
  { value: 'know_well',      label: 'Ya tengo conocimientos del tema.',             emoji: '🎓' },
] as const

function PriorKnowledgeStep({ step, onComplete }: SubProps) {
  const [selected, setSelected] = useState<string | null>(null)

  const handleSelect = (value: string) => {
    if (selected) return
    setSelected(value)
    onComplete()
  }

  return (
    <div className="rounded-xl border border-sky-200 dark:border-sky-800 bg-gradient-to-br from-sky-50 via-cyan-50 to-teal-50 dark:from-sky-950/30 dark:via-cyan-950/30 p-6 space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🧭</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-sky-600 dark:text-sky-400 uppercase">
            Punto de partida
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Sin respuestas correctas</p>
        </div>
      </div>

      <p className="text-lg font-semibold leading-snug text-gray-800 dark:text-gray-100">
        {step.title ?? '¿Qué tanto conocías este tema antes de hoy?'}
      </p>

      <div className="space-y-2">
        {PRIOR_OPTIONS.map(opt => (
          <button
            key={opt.value}
            type="button"
            onClick={() => handleSelect(opt.value)}
            disabled={!!selected}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left transition-all duration-200',
              selected === opt.value
                ? 'border-sky-500 bg-sky-100 dark:bg-sky-900/40 shadow-sm'
                : selected
                  ? 'border-gray-100 dark:border-gray-800 opacity-50'
                  : 'border-sky-100 dark:border-sky-800 hover:border-sky-300 dark:hover:border-sky-600 hover:bg-sky-50/50 dark:hover:bg-sky-950/30',
            )}
          >
            <span className="text-xl select-none shrink-0">{opt.emoji}</span>
            <span className={cn(
              'text-sm font-medium flex-1',
              selected === opt.value
                ? 'text-sky-800 dark:text-sky-200'
                : 'text-gray-700 dark:text-gray-300',
            )}>
              {opt.label}
            </span>
            {selected === opt.value && (
              <Check className="h-4 w-4 text-sky-500 shrink-0" />
            )}
          </button>
        ))}
      </div>

      {selected && (
        <p className="text-sm text-sky-700 dark:text-sky-400 animate-in fade-in duration-300">
          ✓ Registrado. Avanza cuando estés listo.
        </p>
      )}
    </div>
  )
}

// ── question ──────────────────────────────────────────────────────────────────

function QuestionStep({ step, onComplete }: SubProps) {
  const [hypothesis, setHypothesis] = useState('')
  const [submitted,  setSubmitted]  = useState(false)

  const handleSubmit = () => {
    if (!hypothesis.trim()) return
    setSubmitted(true)
    onComplete()
  }

  if (submitted) {
    return (
      <div className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/20 p-6 space-y-3 animate-in fade-in duration-300">
        <div className="flex items-center gap-3">
          <span className="text-3xl select-none">💡</span>
          <p className="text-xs font-mono font-bold tracking-widest text-emerald-600 dark:text-emerald-400 uppercase">
            Hipótesis registrada
          </p>
        </div>
        <div className="rounded-lg border border-emerald-200 dark:border-emerald-700 bg-white/70 dark:bg-emerald-950/20 px-4 py-3">
          <p className="text-sm text-gray-700 dark:text-gray-200 italic">"{hypothesis}"</p>
        </div>
        <p className="text-sm text-emerald-700 dark:text-emerald-400 leading-relaxed">
          A lo largo del módulo descubrirás si tu hipótesis estaba cerca de la realidad.
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-gradient-to-br from-indigo-50 via-violet-50 to-purple-50 dark:from-indigo-950/30 p-6 space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🤔</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-indigo-600 dark:text-indigo-400 uppercase">
            Pregunta de investigación
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Reflexiona antes de continuar</p>
        </div>
      </div>

      <p className="text-lg font-semibold leading-snug text-gray-800 dark:text-gray-100">
        {step.title ?? step.content}
      </p>

      {step.content && step.content !== step.title && (
        <p className="text-sm text-indigo-700/70 dark:text-indigo-300/60 leading-relaxed">
          {step.content}
        </p>
      )}

      <div className="space-y-2">
        <label className="text-xs font-semibold text-indigo-700 dark:text-indigo-400">
          ✍️ Tu hipótesis
        </label>
        <textarea
          value={hypothesis}
          onChange={e => setHypothesis(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit() }}
          rows={3}
          placeholder="Escribe tu idea aquí... ¿Qué crees que hay detrás de esta pregunta?"
          className={cn(
            'w-full resize-none rounded-lg border border-indigo-200 dark:border-indigo-700',
            'bg-white/80 dark:bg-indigo-950/30 px-3 py-2.5 text-sm text-gray-800 dark:text-gray-100',
            'placeholder:text-indigo-400/60 dark:placeholder:text-indigo-400/40',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 transition-colors',
          )}
        />
      </div>

      <Button
        onClick={handleSubmit}
        disabled={!hypothesis.trim()}
        className="w-full gap-2 bg-indigo-600 hover:bg-indigo-700 text-white shadow-md shadow-indigo-200 dark:shadow-indigo-900/30"
      >
        <Send className="h-4 w-4" />
        Registrar mi hipótesis
      </Button>

      <p className="text-xs text-indigo-600/50 dark:text-indigo-400/40 text-center">
        No hay respuestas correctas — solo hipótesis que el módulo irá confirmando. · Ctrl+Enter para enviar
      </p>
    </div>
  )
}

// ── challenge ─────────────────────────────────────────────────────────────────

function ChallengeStep({ step, onComplete }: SubProps) {
  const [response,  setResponse]  = useState('')
  const [submitted, setSubmitted] = useState(false)
  const meta = step.metadata as ChallengeMeta | undefined

  if (submitted) {
    return (
      <div className="rounded-xl border border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-950/20 p-6 space-y-3 animate-in fade-in duration-300">
        <div className="flex items-center gap-3">
          <span className="text-3xl select-none">🎯</span>
          <p className="text-xs font-mono font-bold tracking-widest text-orange-600 dark:text-orange-400 uppercase">
            Reto completado
          </p>
        </div>
        <div className="rounded-lg border border-orange-200 dark:border-orange-700 bg-white/70 dark:bg-orange-950/20 px-4 py-3">
          <p className="text-sm text-gray-700 dark:text-gray-200 italic">"{response}"</p>
        </div>
      </div>
    )
  }

  return (
    <div className="rounded-xl border border-orange-200 dark:border-orange-800 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-950/30 p-6 space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-4xl select-none leading-none">🎯</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-orange-600 dark:text-orange-400 uppercase">
            Reto rápido
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">2–3 minutos</p>
        </div>
      </div>

      <p className="text-base font-semibold text-gray-800 dark:text-gray-100">
        {step.title ?? step.content}
      </p>

      {meta?.prompt && (
        <p className="text-sm text-orange-700 dark:text-orange-400 leading-relaxed">
          {meta.prompt}
        </p>
      )}

      {meta?.hint && (
        <div className="rounded-lg border border-dashed border-orange-300 dark:border-orange-700 bg-orange-50/50 dark:bg-orange-950/20 px-3 py-2">
          <p className="text-xs text-orange-600 dark:text-orange-400">
            💡 Pista: {meta.hint}
          </p>
        </div>
      )}

      <div className="space-y-2">
        <textarea
          value={response}
          onChange={e => setResponse(e.target.value)}
          rows={3}
          placeholder="Tu respuesta..."
          className={cn(
            'w-full resize-none rounded-lg border border-orange-200 dark:border-orange-700',
            'bg-white/80 dark:bg-orange-950/30 px-3 py-2.5 text-sm text-gray-800 dark:text-gray-100',
            'placeholder:text-orange-400/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-orange-400 transition-colors',
          )}
        />
      </div>

      <Button
        onClick={() => { setSubmitted(true); onComplete() }}
        disabled={!response.trim()}
        className="w-full gap-2 bg-orange-500 hover:bg-orange-600 text-white"
      >
        <Send className="h-4 w-4" />
        Enviar respuesta
      </Button>
    </div>
  )
}

// ── evaluation ────────────────────────────────────────────────────────────────

function EvaluationStep({ step, onComplete }: SubProps) {
  const [selected, setSelected] = useState<number | null>(null)
  const meta = step.metadata as EvaluationMeta | undefined

  const options     = meta?.options       ?? []
  const correctIdx  = meta?.correct_index ?? -1
  const explanation = meta?.explanation   ?? ''

  const isCorrect = selected === correctIdx

  const handleSelect = (i: number) => {
    if (selected !== null) return
    setSelected(i)
    onComplete()
  }

  return (
    <div className="rounded-xl border border-violet-200 dark:border-violet-800 bg-gradient-to-br from-violet-50 to-purple-50 dark:from-violet-950/30 p-6 space-y-5">
      <div className="flex items-center gap-3">
        <span className="text-4xl select-none leading-none">📋</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-violet-600 dark:text-violet-400 uppercase">
            Evaluación
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Pon a prueba tu comprensión</p>
        </div>
      </div>

      <p className="text-base font-semibold text-gray-800 dark:text-gray-100">
        {step.title ?? step.content}
      </p>

      {step.content && step.content !== step.title && (
        <p className="text-sm text-violet-700/70 dark:text-violet-300/60 leading-relaxed">
          {step.content}
        </p>
      )}

      <div className="space-y-2">
        {options.map((opt, i) => (
          <button
            key={i}
            type="button"
            onClick={() => handleSelect(i)}
            disabled={selected !== null}
            className={cn(
              'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left text-sm transition-all duration-200',
              selected === null
                ? 'border-violet-100 dark:border-violet-800 hover:border-violet-300 dark:hover:border-violet-600 hover:bg-violet-50/50 dark:hover:bg-violet-950/30'
                : i === correctIdx
                  ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/20'
                  : selected === i
                    ? 'border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-950/20 opacity-80'
                    : 'border-gray-100 dark:border-gray-800 opacity-40',
            )}
          >
            <span className={cn(
              'shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-colors',
              selected !== null && i === correctIdx
                ? 'border-emerald-500 text-emerald-600 dark:text-emerald-400'
                : selected === i
                  ? 'border-red-400 text-red-500'
                  : 'border-current text-gray-500 dark:text-gray-400',
            )}>
              {selected !== null && i === correctIdx
                ? '✓'
                : selected === i
                  ? '✗'
                  : String.fromCharCode(65 + i)
              }
            </span>
            <span className={cn(
              'flex-1 leading-relaxed',
              selected !== null && i === correctIdx
                ? 'text-emerald-800 dark:text-emerald-200 font-medium'
                : selected === i
                  ? 'text-red-700 dark:text-red-300'
                  : 'text-gray-700 dark:text-gray-300',
            )}>
              {opt}
            </span>
          </button>
        ))}
      </div>

      {selected !== null && explanation && (
        <div className={cn(
          'rounded-lg border px-4 py-3 animate-in fade-in duration-300',
          isCorrect
            ? 'border-emerald-200 dark:border-emerald-700 bg-emerald-50/60 dark:bg-emerald-950/20'
            : 'border-amber-200 dark:border-amber-700 bg-amber-50/60 dark:bg-amber-950/20',
        )}>
          <p className={cn(
            'text-sm font-semibold mb-1',
            isCorrect ? 'text-emerald-700 dark:text-emerald-300' : 'text-amber-700 dark:text-amber-300',
          )}>
            {isCorrect ? '✓ Correcto' : 'No exactamente'}
          </p>
          <p className={cn(
            'text-sm leading-relaxed',
            isCorrect ? 'text-emerald-800 dark:text-emerald-200' : 'text-amber-800 dark:text-amber-200',
          )}>
            {explanation}
          </p>
        </div>
      )}
    </div>
  )
}

// ── Main dispatcher ───────────────────────────────────────────────────────────

interface Props {
  step:       StepData
  onComplete: () => void
  onXp:       (amount: number) => void
}

/**
 * LearningJourneyStep — Sprint J1
 *
 * Dispatcher que renderiza el componente correcto según step.type.
 * Centraliza la lógica de XP: llama onXp(step.xpReward) antes de
 * propagar onComplete al padre, excepto en casos donde la XP depende
 * del nivel de respuesta (reflection: solo 'clear' da XP).
 */
export function LearningJourneyStep({ step, onComplete, onXp }: Props) {
  const handleComplete = () => {
    if (step.xpReward) onXp(step.xpReward)
    onComplete()
  }

  switch (step.type) {

    case 'did_you_know':
      return <DidYouKnowInlineCard content={step.content ?? step.title ?? ''} />

    case 'prior_knowledge':
      return <PriorKnowledgeStep step={step} onComplete={handleComplete} />

    case 'concept':
      return (
        <ConceptCard
          index={1}
          content={step.content ?? ''}
          onRead={handleComplete}
        />
      )

    case 'question':
      return <QuestionStep step={step} onComplete={handleComplete} />

    case 'example':
      return (
        <ExampleCard
          index={0}
          content={step.content ?? ''}
          onExplore={handleComplete}
        />
      )

    case 'challenge':
      return <ChallengeStep step={step} onComplete={handleComplete} />

    case 'application': {
      const rawItems = step.metadata?.items
      const items    = Array.isArray(rawItems)
        ? rawItems.filter((x): x is string => typeof x === 'string')
        : step.content ? [step.content] : []
      return <PracticalApplicationCard items={items} onSave={handleComplete} />
    }

    case 'reflection':
      return (
        <ReflectionCheckpoint
          question={step.title}
          onResponse={(level) => {
            onComplete()
            if (level === 'clear' && step.xpReward) onXp(step.xpReward)
          }}
        />
      )

    case 'evaluation':
      return <EvaluationStep step={step} onComplete={handleComplete} />

    default:
      return null
  }
}
