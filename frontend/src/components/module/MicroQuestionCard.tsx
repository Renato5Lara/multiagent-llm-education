import { useState } from 'react'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  question:   string
  options:    string[]
  correct?:   number    // índice correcto; si undefined, toda opción es válida
  feedback?:  string    // texto post-respuesta personalizado
  onComplete: () => void
}

export function MicroQuestionCard({ question, options, correct, feedback, onComplete }: Props) {
  const [selected, setSelected] = useState<number | null>(null)

  const isCorrect = selected !== null && (correct === undefined || selected === correct)

  const handleSelect = (i: number) => {
    if (selected !== null) return
    setSelected(i)
    onComplete()
  }

  const defaultFeedback = isCorrect
    ? '¡Buena respuesta! Sigue adelante.'
    : 'Interesante perspectiva. El módulo irá aclarando esto.'

  return (
    <div className="rounded-xl border border-cyan-200 dark:border-cyan-800 bg-gradient-to-br from-cyan-50 via-sky-50 to-blue-50 dark:from-cyan-950/30 dark:via-sky-950/30 dark:to-blue-950/20 p-6 space-y-5">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">❓</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-cyan-600 dark:text-cyan-400 uppercase">
            Pregunta rápida
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Sin presión — solo reflexiona</p>
        </div>
      </div>

      {/* Question */}
      <p className="text-base font-semibold leading-snug text-gray-800 dark:text-gray-100">
        {question}
      </p>

      {/* Options */}
      <div className="space-y-2">
        {options.map((opt, i) => {
          const isSelected  = selected === i
          const isCorrectOpt = correct !== undefined && i === correct && selected !== null
          return (
            <button
              key={i}
              type="button"
              onClick={() => handleSelect(i)}
              disabled={selected !== null}
              className={cn(
                'w-full flex items-center gap-3 px-4 py-3 rounded-lg border text-left text-sm font-medium transition-all duration-200 disabled:cursor-default',
                selected === null
                  ? 'border-cyan-200 dark:border-cyan-800 text-gray-700 dark:text-gray-300 hover:border-cyan-400 dark:hover:border-cyan-600 hover:bg-cyan-100/50 dark:hover:bg-cyan-900/30'
                  : isSelected
                    ? isCorrect
                      ? 'border-emerald-400 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-200'
                      : 'border-amber-400 bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200'
                    : isCorrectOpt
                      ? 'border-emerald-300 bg-emerald-50/50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-300 opacity-80'
                      : 'border-gray-100 dark:border-gray-800 text-gray-400 dark:text-gray-600 opacity-40',
              )}
            >
              <span className={cn(
                'shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all',
                isSelected && isCorrect   ? 'border-emerald-500 bg-emerald-500 text-white'
                : isSelected             ? 'border-amber-500 bg-amber-500 text-white'
                : isCorrectOpt           ? 'border-emerald-400 text-emerald-500'
                                         : 'border-current text-gray-500 dark:text-gray-400',
              )}>
                {isSelected ? <Check className="h-3 w-3" /> : String.fromCharCode(65 + i)}
              </span>
              {opt}
            </button>
          )
        })}
      </div>

      {/* Feedback */}
      {selected !== null && (
        <div className={cn(
          'rounded-lg border px-4 py-3 animate-in fade-in slide-in-from-bottom-1 duration-300',
          isCorrect
            ? 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/70 dark:bg-emerald-950/20'
            : 'border-cyan-200 dark:border-cyan-800 bg-cyan-50/70 dark:bg-cyan-950/20',
        )}>
          <p className={cn(
            'text-sm leading-relaxed',
            isCorrect
              ? 'text-emerald-700 dark:text-emerald-300'
              : 'text-cyan-700 dark:text-cyan-300',
          )}>
            {feedback ?? defaultFeedback}
          </p>
        </div>
      )}
    </div>
  )
}
