import { useState } from 'react'
import { cn } from '@/lib/utils'

type Response = 'clear' | 'partial' | 'stuck'

interface Props {
  question?:   string
  onResponse?: (level: Response) => void
}

const OPTIONS: { value: Response; label: string; emoji: string }[] = [
  { value: 'clear',   label: 'Todo claro',     emoji: '✅' },
  { value: 'partial', label: 'Más o menos',     emoji: '🤔' },
  { value: 'stuck',   label: 'Necesito repasar', emoji: '↩' },
]

const RESPONSES: Record<Response, { headline: string; body: string }> = {
  clear:   {
    headline: '¡Excelente!',
    body:     'Sigue adelante — el próximo bloque profundiza en este tema.',
  },
  partial: {
    headline: 'Completamente normal.',
    body:     'Los conceptos se afinan a medida que avanzas. Sigue al siguiente bloque — la repetición espaciada hará el resto.',
  },
  stuck:   {
    headline: 'Sin problema.',
    body:     'Puedes volver a las secciones anteriores cuando quieras. El aprendizaje no es lineal.',
  },
}

/**
 * ReflectionCheckpoint — Sprint I2
 *
 * Punto de auto-evaluación metacognitiva entre secciones del módulo.
 * 3 opciones de una sola selección + retroalimentación inmediata.
 * Llama onResponse() con el nivel elegido (para micro-XP en el padre).
 * No hay persistencia en backend en este sprint — eso es Sprint I5.
 */
export function ReflectionCheckpoint({ question, onResponse }: Props) {
  const [selected, setSelected] = useState<Response | null>(null)

  const handleSelect = (value: Response) => {
    if (selected) return
    setSelected(value)
    onResponse?.(value)
  }

  const defaultQuestion = '¿Cómo vas con el contenido hasta aquí?'

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-900/30 px-4 py-4 space-y-3">
      {/* Question */}
      <div className="flex items-center gap-2">
        <span className="text-base select-none">🧘</span>
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {question ?? defaultQuestion}
        </p>
      </div>

      {/* Options / result */}
      {selected ? (
        <div className="animate-in fade-in duration-300 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 px-4 py-3 space-y-1">
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">
            {RESPONSES[selected].headline}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
            {RESPONSES[selected].body}
          </p>
          {selected === 'clear' && (
            <p className="text-xs text-amber-500 font-semibold mt-1.5">✨ +5 XP</p>
          )}
        </div>
      ) : (
        <div className="flex flex-wrap gap-2">
          {OPTIONS.map(opt => (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSelect(opt.value)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2 rounded-full border text-xs font-medium transition-all duration-150',
                'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400',
                'hover:border-primary/50 hover:bg-primary/5 hover:text-primary',
              )}
            >
              <span>{opt.emoji}</span>
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
