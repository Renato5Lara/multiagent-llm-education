import { useState } from 'react'
import { Eye, Lightbulb } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  question:   string
  reveal:     string
  hint?:      string
  onComplete: () => void
}

export function PredictionCard({ question, reveal, hint, onComplete }: Props) {
  const [revealed,  setRevealed]  = useState(false)
  const [showHint,  setShowHint]  = useState(false)

  const handleReveal = () => {
    setRevealed(true)
    onComplete()
  }

  return (
    <div className="rounded-xl border border-fuchsia-200 dark:border-fuchsia-800 bg-gradient-to-br from-fuchsia-50 via-pink-50 to-purple-50 dark:from-fuchsia-950/30 dark:via-pink-950/30 dark:to-purple-950/20 p-6 space-y-5">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">🔮</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-fuchsia-600 dark:text-fuchsia-400 uppercase">
            Predicción
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Piensa antes de revelar</p>
        </div>
      </div>

      {/* Question */}
      <div className="rounded-lg border border-fuchsia-200 dark:border-fuchsia-700 bg-white/60 dark:bg-fuchsia-950/20 px-4 py-3.5">
        <p className="text-base font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {question}
        </p>
      </div>

      {/* Hint (optional, collapsible) */}
      {hint && !revealed && (
        <div>
          {!showHint ? (
            <button
              type="button"
              onClick={() => setShowHint(true)}
              className="flex items-center gap-1.5 text-xs text-fuchsia-500 dark:text-fuchsia-400 hover:text-fuchsia-700 dark:hover:text-fuchsia-300 transition-colors"
            >
              <Lightbulb className="h-3.5 w-3.5" />
              Ver pista
            </button>
          ) : (
            <div className="rounded-lg border border-dashed border-fuchsia-300 dark:border-fuchsia-700 bg-fuchsia-50/50 dark:bg-fuchsia-950/20 px-3 py-2.5 animate-in fade-in duration-200">
              <p className="text-xs text-fuchsia-600 dark:text-fuchsia-400 leading-relaxed">
                💡 {hint}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Reveal / Revealed */}
      {!revealed ? (
        <Button
          onClick={handleReveal}
          className="w-full gap-2 bg-fuchsia-600 hover:bg-fuchsia-700 text-white shadow-md shadow-fuchsia-200 dark:shadow-fuchsia-900/30"
        >
          <Eye className="h-4 w-4" />
          Revelar respuesta
        </Button>
      ) : (
        <div className="space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-400">
          <p className="text-xs font-mono font-bold tracking-widest text-fuchsia-600 dark:text-fuchsia-400 uppercase">
            ✓ Revelado
          </p>
          <div className="rounded-lg border border-fuchsia-300 dark:border-fuchsia-700 bg-white/70 dark:bg-fuchsia-950/20 px-4 py-3.5">
            <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
              {reveal}
            </p>
          </div>
          <p className="text-xs text-fuchsia-500 dark:text-fuchsia-400">
            ¿Tu predicción se acercó? Avanza para continuar.
          </p>
        </div>
      )}
    </div>
  )
}
