import { useState } from 'react'
import { ChevronDown, ChevronUp, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  index: number
  content: string
  onExplore?: () => void
}

function getPreview(text: string): string {
  const period = text.indexOf('. ')
  if (period > 0 && period < 120) return text.slice(0, period + 1)
  return text.slice(0, 110).trim() + (text.length > 110 ? '...' : '')
}

const BLOOM_LABELS = ['Recordar', 'Comprender', 'Aplicar', 'Analizar', 'Evaluar', 'Crear']

/**
 * ExampleCard — Sprint I1 + I2
 *
 * Ejemplo progresivo con mecánica de expansión. Muestra solo el inicio del
 * ejemplo hasta que el estudiante elige "Explorar" — acción que registra el
 * evento de XP y revela el contenido completo.
 */
export function ExampleCard({ index, content, onExplore }: Props) {
  const [expanded,  setExpanded]  = useState(false)
  const [explored,  setExplored]  = useState(false)

  const preview  = getPreview(content)
  const hasMore  = content.length > preview.length

  const bloom    = Math.min(index, BLOOM_LABELS.length - 1)
  const bloomLabel = BLOOM_LABELS[bloom]

  const handleExpand = () => {
    if (!expanded && !explored) {
      setExplored(true)
      onExplore?.()
    }
    setExpanded(v => !v)
  }

  return (
    <div className={cn(
      'rounded-xl border overflow-hidden transition-all duration-200',
      explored
        ? 'border-blue-200 dark:border-blue-800 bg-blue-50/40 dark:bg-blue-950/20'
        : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50',
    )}>
      <button
        type="button"
        onClick={hasMore ? handleExpand : undefined}
        className={cn(
          'w-full text-left px-4 py-3.5 flex items-start gap-3',
          hasMore && 'hover:bg-blue-50/50 dark:hover:bg-blue-950/10 transition-colors',
        )}
      >
        {/* Index + Bloom chip */}
        <div className="shrink-0 mt-0.5 flex flex-col items-center gap-1">
          <div className={cn(
            'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold',
            explored
              ? 'bg-blue-500 text-white'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
          )}>
            {index + 1}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-mono text-blue-500 dark:text-blue-400 font-medium">
              {bloomLabel}
            </span>
            {explored && (
              <span className="flex items-center gap-0.5 text-[10px] text-amber-500 font-semibold animate-in fade-in duration-300">
                <Zap className="h-2.5 w-2.5" /> +3 XP
              </span>
            )}
          </div>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {expanded ? content : preview}
            {!expanded && hasMore && (
              <span className="text-blue-400/60 dark:text-blue-500/40"> …</span>
            )}
          </p>
        </div>

        {/* Chevron */}
        {hasMore && (
          <span className="shrink-0 mt-1 text-muted-foreground">
            {expanded
              ? <ChevronUp  className="h-4 w-4" />
              : <ChevronDown className="h-4 w-4" />
            }
          </span>
        )}
      </button>
    </div>
  )
}
