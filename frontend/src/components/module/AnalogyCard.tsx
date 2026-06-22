import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, ImageIcon } from 'lucide-react'

interface Props {
  source:       string    // lo que el estudiante ya conoce
  target:       string    // el concepto nuevo
  explanation:  string    // el puente "porque…"
  image_hint?:  string    // descripción de imagen mental sugerida
  onComplete?:  () => void
}

export function AnalogyCard({ source, target, explanation, image_hint, onComplete }: Props) {
  const [showImageHint, setShowImageHint] = useState(false)

  // Pasivo: XP al ver la tarjeta
  useEffect(() => {
    onComplete?.()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="rounded-xl border border-green-200 dark:border-green-800 bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 dark:from-green-950/30 dark:via-emerald-950/30 dark:to-teal-950/20 p-6 space-y-4">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">🌀</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-green-600 dark:text-green-400 uppercase">
            Analogía
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">Una imagen que lo hace más fácil</p>
        </div>
      </div>

      {/* Analogía principal: "X es como Y" */}
      <div className="rounded-lg border border-green-200 dark:border-green-700 bg-white/60 dark:bg-green-950/20 px-4 py-3.5 space-y-1">
        <div className="flex items-baseline gap-2 flex-wrap">
          <span className="text-base font-bold text-green-800 dark:text-green-200">
            {target}
          </span>
          <span className="text-sm text-green-600 dark:text-green-400 font-medium">es como</span>
          <span className="text-base font-bold text-green-800 dark:text-green-200">
            {source}
          </span>
        </div>
      </div>

      {/* Explicación "porque…" */}
      <div className="pl-1 border-l-2 border-green-300 dark:border-green-700 ml-1">
        <p className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-1">
          Porque...
        </p>
        <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {explanation}
        </p>
      </div>

      {/* Imagen mental (opcional, colapsable) */}
      {image_hint && (
        <div>
          <button
            type="button"
            onClick={() => setShowImageHint(v => !v)}
            className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200 transition-colors"
          >
            <ImageIcon className="h-3.5 w-3.5" />
            {showImageHint ? 'Ocultar imagen mental' : 'Ver imagen mental'}
            {showImageHint
              ? <ChevronUp   className="h-3.5 w-3.5" />
              : <ChevronDown className="h-3.5 w-3.5" />
            }
          </button>
          {showImageHint && (
            <div className="mt-2 rounded-lg border border-dashed border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-950/20 px-3 py-2.5 animate-in fade-in duration-200">
              <p className="text-sm text-green-700 dark:text-green-300 leading-relaxed italic">
                🖼️ {image_hint}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
