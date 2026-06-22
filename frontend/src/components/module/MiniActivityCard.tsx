import { useState } from 'react'
import { Check, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  instructions: string
  steps:        string[]
  onComplete:   () => void
}

export function MiniActivityCard({ instructions, steps, onComplete }: Props) {
  const [checked,   setChecked]   = useState<Set<number>>(new Set())
  const [finished,  setFinished]  = useState(false)

  const allChecked = checked.size === steps.length && steps.length > 0

  const toggleStep = (i: number) => {
    if (finished) return
    setChecked(prev => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  const handleFinish = () => {
    setFinished(true)
    onComplete()
  }

  return (
    <div className="rounded-xl border border-teal-200 dark:border-teal-800 bg-gradient-to-br from-teal-50 via-cyan-50 to-emerald-50 dark:from-teal-950/30 dark:via-cyan-950/30 dark:to-emerald-950/20 p-6 space-y-5">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">✏️</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-teal-600 dark:text-teal-400 uppercase">
            Mini actividad
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {finished ? 'Completada' : `${checked.size} de ${steps.length} pasos`}
          </p>
        </div>
        {finished && (
          <CheckCircle2 className="h-5 w-5 text-teal-500 ml-auto shrink-0 animate-in zoom-in duration-300" />
        )}
      </div>

      {/* Instructions */}
      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
        {instructions}
      </p>

      {/* Checklist */}
      <div className="space-y-2">
        {steps.map((step, i) => {
          const isChecked = checked.has(i)
          return (
            <button
              key={i}
              type="button"
              onClick={() => toggleStep(i)}
              disabled={finished}
              className={cn(
                'w-full flex items-start gap-3 px-4 py-3 rounded-lg border text-left text-sm transition-all duration-200 disabled:cursor-default',
                isChecked
                  ? 'border-teal-300 dark:border-teal-700 bg-teal-50 dark:bg-teal-950/30'
                  : 'border-teal-100 dark:border-teal-800 bg-white/60 dark:bg-teal-950/10 hover:border-teal-300 dark:hover:border-teal-600 hover:bg-teal-50/50 dark:hover:bg-teal-950/20',
              )}
            >
              {/* Checkbox */}
              <span className={cn(
                'shrink-0 mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-200',
                isChecked
                  ? 'border-teal-500 bg-teal-500'
                  : 'border-teal-300 dark:border-teal-600',
              )}>
                {isChecked && (
                  <Check className="h-3 w-3 text-white animate-in zoom-in duration-150" />
                )}
              </span>
              {/* Step number + text */}
              <div className="flex-1">
                <span className={cn(
                  'text-xs font-mono font-bold mr-2',
                  isChecked
                    ? 'text-teal-500 dark:text-teal-400'
                    : 'text-teal-400 dark:text-teal-500',
                )}>
                  {i + 1}.
                </span>
                <span className={cn(
                  'transition-colors',
                  isChecked
                    ? 'text-teal-800 dark:text-teal-200 line-through decoration-teal-400 dark:decoration-teal-600'
                    : 'text-gray-700 dark:text-gray-300',
                )}>
                  {step}
                </span>
              </div>
            </button>
          )
        })}
      </div>

      {/* Finish button */}
      {!finished ? (
        <Button
          onClick={handleFinish}
          disabled={!allChecked}
          className={cn(
            'w-full gap-2 transition-all',
            allChecked
              ? 'bg-teal-600 hover:bg-teal-700 text-white shadow-md shadow-teal-200 dark:shadow-teal-900/30'
              : 'opacity-50',
          )}
          title={!allChecked ? 'Completa todos los pasos para finalizar' : undefined}
        >
          <CheckCircle2 className="h-4 w-4" />
          Finalizar actividad
        </Button>
      ) : (
        <div className="rounded-lg border border-teal-200 dark:border-teal-700 bg-teal-50/60 dark:bg-teal-950/20 px-4 py-3 animate-in fade-in duration-300">
          <p className="text-sm font-semibold text-teal-700 dark:text-teal-300">
            ✓ ¡Actividad completada!
          </p>
          <p className="text-xs text-teal-600/70 dark:text-teal-400/60 mt-0.5">
            Avanza cuando estés listo.
          </p>
        </div>
      )}
    </div>
  )
}
