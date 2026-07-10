import { useMemo, useState } from 'react'
import { Check, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  instructions: string
  steps:        string[]
  onComplete:   () => void
}

// Feedback del PO (Pruebas 1): la versión checklist «no se entiende como
// actividad y no aporta nada» — marcar casillas no ejercita nada. Ahora los
// pasos aparecen DESORDENADOS y el estudiante debe tocarlos en el orden
// correcto: la misma mecánica de secuencias que practica el resto del módulo.
function shuffled(steps: string[]): number[] {
  const idx = steps.map((_, i) => i)
  for (let i = idx.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[idx[i], idx[j]] = [idx[j], idx[i]]
  }
  // Si el azar los dejó en orden, invertir para que siempre haya trabajo real.
  if (idx.length > 1 && idx.every((v, i) => v === i)) idx.reverse()
  return idx
}

export function MiniActivityCard({ instructions, steps, onComplete }: Props) {
  const display = useMemo(() => shuffled(steps), [steps])
  const [nextExpected, setNextExpected] = useState(0)
  const [wrongIdx,     setWrongIdx]     = useState<number | null>(null)
  const [finished,     setFinished]     = useState(false)

  const singleStep = steps.length <= 1

  const handlePick = (originalIndex: number) => {
    if (finished) return
    if (originalIndex === nextExpected) {
      setWrongIdx(null)
      const next = nextExpected + 1
      setNextExpected(next)
      if (next >= steps.length) {
        setFinished(true)
        onComplete()
      }
    } else {
      setWrongIdx(originalIndex)
    }
  }

  const handleSingleFinish = () => {
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
            {finished
              ? 'Completada'
              : singleStep
                ? 'Hazlo y márcalo'
                : `Toca los pasos en el orden correcto · ${nextExpected} de ${steps.length}`}
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
      {!singleStep && !finished && (
        <p className="text-xs text-teal-600 dark:text-teal-400">
          Los pasos están desordenados. Toca primero el que debe ocurrir primero.
        </p>
      )}

      {/* Pasos desordenados — se ordenan tocándolos en secuencia */}
      <div className="space-y-2">
        {display.map((originalIndex) => {
          const done   = originalIndex < nextExpected
          const wrong  = wrongIdx === originalIndex
          return (
            <button
              key={originalIndex}
              type="button"
              onClick={() => handlePick(originalIndex)}
              disabled={finished || done}
              className={cn(
                'w-full flex items-start gap-3 px-4 py-3 rounded-lg border text-left text-sm transition-all duration-200 disabled:cursor-default',
                done
                  ? 'border-teal-300 dark:border-teal-700 bg-teal-50 dark:bg-teal-950/30'
                  : wrong
                    ? 'border-amber-400 dark:border-amber-600 bg-amber-50 dark:bg-amber-950/20'
                    : 'border-teal-100 dark:border-teal-800 bg-white/60 dark:bg-teal-950/10 hover:border-teal-300 dark:hover:border-teal-600 hover:bg-teal-50/50 dark:hover:bg-teal-950/20',
              )}
            >
              <span className={cn(
                'shrink-0 mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center transition-all duration-200',
                done ? 'border-teal-500 bg-teal-500' : 'border-teal-300 dark:border-teal-600',
              )}>
                {done && <Check className="h-3 w-3 text-white animate-in zoom-in duration-150" />}
              </span>
              <div className="flex-1">
                {done && (
                  <span className="text-xs font-mono font-bold mr-2 text-teal-500 dark:text-teal-400">
                    {originalIndex + 1}.
                  </span>
                )}
                <span className={cn(
                  'transition-colors',
                  done ? 'text-teal-800 dark:text-teal-200' : 'text-gray-700 dark:text-gray-300',
                )}>
                  {steps[originalIndex]}
                </span>
                {wrong && (
                  <p className="text-xs text-amber-600 dark:text-amber-400 mt-1 animate-in fade-in duration-200">
                    Ese paso aún no toca — ¿qué tendría que haber pasado antes?
                  </p>
                )}
              </div>
            </button>
          )
        })}
      </div>

      {/* Cierre */}
      {singleStep && !finished && (
        <Button onClick={handleSingleFinish} className="w-full gap-2 bg-teal-600 hover:bg-teal-700 text-white">
          <CheckCircle2 className="h-4 w-4" />
          Ya lo hice
        </Button>
      )}
      {finished && (
        <div className="rounded-lg border border-teal-200 dark:border-teal-700 bg-teal-50/60 dark:bg-teal-950/20 px-4 py-3 animate-in fade-in duration-300">
          <p className="text-sm font-semibold text-teal-700 dark:text-teal-300">
            ✓ Secuencia correcta
          </p>
          <p className="text-xs text-teal-600/70 dark:text-teal-400/60 mt-0.5">
            Ordenaste los pasos como lo haría un programa. Avanza cuando estés listo.
          </p>
        </div>
      )}
    </div>
  )
}
