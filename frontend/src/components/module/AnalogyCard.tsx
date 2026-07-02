import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

const TRUNCATE_AT = 220

interface Props {
  source:       string
  target:       string
  explanation:  string
  image_hint?:  string
  onComplete?:  () => void
}

/**
 * AnalogyCard — Sprint L5 / Sprint 2.1 (refinamiento visual)
 *
 * Referencia: pantalla "Contenido Adaptativo" con bloques de dos columnas
 * ("Recursive Step" | "Exit Condition") y diagrama SVG de puente.
 *
 * Mejoras vs versión anterior:
 *   • Diagrama SVG de puente: [Origen] ──→ [Destino] — convierte la analogía
 *     de texto puro a una imagen visual, reforzando el perfil visual.
 *   • Dos tarjetas en grid (source | target) en vez de texto inline.
 *   • Más padding y separación entre secciones.
 */
export function AnalogyCard({ source, target, explanation, image_hint, onComplete }: Props) {
  const [showImageHint, setShowImageHint] = useState(false)
  const [expandExplain, setExpandExplain] = useState(false)

  const needsTruncation = explanation.length > TRUNCATE_AT
  const displayText     = needsTruncation && !expandExplain
    ? explanation.slice(0, TRUNCATE_AT).trimEnd() + '…'
    : explanation

  useEffect(() => {
    onComplete?.()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="rounded-xl border border-green-200 dark:border-green-800 bg-gradient-to-br from-green-50 via-emerald-50 to-teal-50 dark:from-green-950/30 dark:via-emerald-950/30 dark:to-teal-950/20 overflow-hidden animate-in fade-in slide-in-from-bottom-2 duration-400">

      {/* Thin accent bar — referencia: section dividers de Contenido Adaptativo */}
      <div className="h-[3px] w-full bg-green-400 dark:bg-green-600" />

      <div className="p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-3">
          <span className="text-3xl select-none leading-none">🌀</span>
          <div>
            <p className="text-[10px] font-mono font-bold tracking-[0.25em] text-green-600 dark:text-green-400 uppercase">
              Analogía
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">Una imagen que lo hace más fácil</p>
          </div>
        </div>

        {/* Bridge diagram SVG — referencia: dos bloques de info + flecha entre ellos
            Reproduce la estructura de "Recursive Step" → "Exit Condition" pero como puente.
            Convierte la analogía textual en una representación visual clara. */}
        <div className="flex items-stretch gap-0" role="img" aria-label={`${source} es como ${target}`}>
          {/* Source card */}
          <div className={cn(
            'flex-1 rounded-l-xl border border-green-200 dark:border-green-700',
            'bg-white/70 dark:bg-green-950/30 px-4 py-4',
          )}>
            <p className="text-[9px] font-mono font-bold tracking-[0.2em] text-green-500 dark:text-green-500 uppercase mb-2">
              Lo conocido
            </p>
            <p className="text-sm font-bold text-green-800 dark:text-green-200 leading-snug">
              {source}
            </p>
          </div>

          {/* SVG bridge arrow — inline, semantic */}
          <div className="flex flex-col items-center justify-center px-1 shrink-0" aria-hidden="true">
            <svg width="36" height="40" viewBox="0 0 36 40" fill="none" xmlns="http://www.w3.org/2000/svg">
              {/* Horizontal line */}
              <line x1="2" y1="20" x2="28" y2="20" stroke="#4ade80" strokeWidth="2" strokeDasharray="4 2" />
              {/* Arrowhead */}
              <path d="M24 14 L32 20 L24 26" stroke="#4ade80" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              {/* "es como" label */}
              <text x="18" y="12" textAnchor="middle" fontSize="7" fill="#4ade80" fontFamily="monospace" opacity="0.8">es como</text>
            </svg>
          </div>

          {/* Target card */}
          <div className={cn(
            'flex-1 rounded-r-xl border border-green-200 dark:border-green-700',
            'bg-green-100/60 dark:bg-green-900/20 px-4 py-4',
          )}>
            <p className="text-[9px] font-mono font-bold tracking-[0.2em] text-green-600 dark:text-green-400 uppercase mb-2">
              Lo nuevo
            </p>
            <p className="text-sm font-bold text-green-800 dark:text-green-200 leading-snug">
              {target}
            </p>
          </div>
        </div>

        {/* Explanation with "Ver más" */}
        <div className="pl-1 border-l-2 border-green-300 dark:border-green-700 ml-1">
          <p className="text-[10px] font-semibold text-green-600 dark:text-green-400 uppercase tracking-wide mb-1.5">
            Porque...
          </p>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {displayText}
          </p>
          {needsTruncation && (
            <button
              type="button"
              onClick={() => setExpandExplain(v => !v)}
              className="mt-2 text-xs font-semibold text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200 transition-colors hover:underline"
            >
              {expandExplain ? '↑ Ver menos' : '↓ Ver más'}
            </button>
          )}
        </div>

        {/* Image hint (collapsible) */}
        {image_hint && (
          <div>
            <button
              type="button"
              onClick={() => setShowImageHint(v => !v)}
              className="flex items-center gap-1.5 text-xs text-green-600 dark:text-green-400 hover:text-green-800 dark:hover:text-green-200 transition-colors"
            >
              🖼️ {showImageHint ? 'Ocultar imagen mental' : 'Ver imagen mental'}
              {showImageHint
                ? <ChevronUp   className="h-3.5 w-3.5" />
                : <ChevronDown className="h-3.5 w-3.5" />
              }
            </button>
            {showImageHint && (
              <div className="mt-2 rounded-lg border border-dashed border-green-300 dark:border-green-700 bg-green-50/50 dark:bg-green-950/20 px-3 py-2.5 animate-in fade-in duration-200">
                <p className="text-sm text-green-700 dark:text-green-300 leading-relaxed italic">
                  {image_hint}
                </p>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
