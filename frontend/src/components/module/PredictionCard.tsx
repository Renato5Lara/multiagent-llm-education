import { useState } from 'react'
import { Eye, Lightbulb } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  question:   string
  reveal:     string
  hint?:      string
  onComplete: () => void
}

// Feedback del PO (Pruebas 1/5): revelar sin haber predicho convertía la
// tarjeta en un botón vacío. Ahora la predicción se escribe primero y al
// revelar se muestra junto a la respuesta, para que el estudiante compare
// lo que pensó con lo que realmente ocurre.
export function PredictionCard({ question, reveal, hint, onComplete }: Props) {
  const [prediction, setPrediction] = useState('')
  const [revealed,   setRevealed]   = useState(false)
  const [showHint,   setShowHint]   = useState(false)

  const canReveal = prediction.trim().length >= 3

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
          <p className="text-xs text-muted-foreground mt-0.5">Escribe lo que crees que pasará — después compruébalo</p>
        </div>
      </div>

      {/* Question */}
      <div className="rounded-lg border border-fuchsia-200 dark:border-fuchsia-700 bg-white/60 dark:bg-fuchsia-950/20 px-4 py-3.5">
        <p className="text-base font-semibold leading-snug text-gray-800 dark:text-gray-100">
          {question}
        </p>
      </div>

      {/* Tu predicción — requisito para revelar */}
      {!revealed && (
        <div className="space-y-1.5">
          <label htmlFor="prediction-input" className="text-xs font-semibold text-fuchsia-600 dark:text-fuchsia-400 uppercase tracking-wide">
            Tu predicción
          </label>
          <textarea
            id="prediction-input"
            value={prediction}
            onChange={e => setPrediction(e.target.value)}
            rows={2}
            placeholder="Ej.: «creo que fallaría porque…»"
            className="w-full rounded-lg border border-fuchsia-200 dark:border-fuchsia-700 bg-white/70 dark:bg-fuchsia-950/20 px-3 py-2.5 text-sm text-gray-800 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:border-fuchsia-400 dark:focus:border-fuchsia-500 resize-none"
          />
        </div>
      )}

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
              ¿Por dónde empezar?
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
        <div className="space-y-1.5">
          <Button
            onClick={handleReveal}
            disabled={!canReveal}
            className="w-full gap-2 bg-fuchsia-600 hover:bg-fuchsia-700 text-white shadow-md shadow-fuchsia-200 dark:shadow-fuchsia-900/30 disabled:opacity-50"
          >
            <Eye className="h-4 w-4" />
            Comprobar mi predicción
          </Button>
          {!canReveal && (
            <p className="text-[11px] text-fuchsia-500/70 dark:text-fuchsia-400/60 text-center">
              Primero escribe qué crees que pasará — así podrás comparar.
            </p>
          )}
        </div>
      ) : (
        <div className="space-y-2 animate-in fade-in slide-in-from-bottom-2 duration-400">
          <div className="rounded-lg border border-fuchsia-200 dark:border-fuchsia-800 bg-fuchsia-50/40 dark:bg-fuchsia-950/10 px-4 py-3">
            <p className="text-[10px] font-mono font-bold tracking-widest text-fuchsia-400 dark:text-fuchsia-500 uppercase mb-1">
              Lo que pensaste
            </p>
            <p className="text-sm text-gray-600 dark:text-gray-300 italic leading-relaxed">
              «{prediction.trim()}»
            </p>
          </div>
          <div className="rounded-lg border border-fuchsia-300 dark:border-fuchsia-700 bg-white/70 dark:bg-fuchsia-950/20 px-4 py-3.5">
            <p className="text-[10px] font-mono font-bold tracking-widest text-fuchsia-600 dark:text-fuchsia-400 uppercase mb-1">
              Lo que realmente ocurre
            </p>
            <p className="text-sm text-gray-700 dark:text-gray-200 leading-relaxed">
              {reveal}
            </p>
          </div>
          <p className="text-xs text-fuchsia-500 dark:text-fuchsia-400">
            Compara ambas: si tu idea cambió, eso es aprendizaje. Avanza para continuar.
          </p>
        </div>
      )}
    </div>
  )
}
