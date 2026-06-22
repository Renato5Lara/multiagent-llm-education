import { useEffect } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  fact:        string
  source?:     string
  stat?:       string     // número / stat destacable, ej. "73%"
  onComplete?: () => void // pasivo: se llama al montar para otorgar XP
}

export function CuriosityCard({ fact, source, stat, onComplete }: Props) {
  // Pasivo: el estudiante no necesita interactuar para avanzar.
  // XP se otorga al ver la tarjeta (primer render).
  useEffect(() => {
    onComplete?.()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="rounded-xl border border-yellow-200 dark:border-yellow-800 bg-gradient-to-br from-yellow-50 via-amber-50 to-orange-50 dark:from-yellow-950/30 dark:via-amber-950/30 dark:to-orange-950/20 p-6 space-y-4">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">✨</span>
        <p className="text-xs font-mono font-bold tracking-widest text-yellow-600 dark:text-yellow-400 uppercase">
          ¿Sabías que...?
        </p>
      </div>

      {/* Stat destacado */}
      {stat && (
        <div className="flex justify-center py-2">
          <span className={cn(
            'text-5xl font-black tracking-tight',
            'text-yellow-600 dark:text-yellow-400',
            'drop-shadow-sm',
          )}>
            {stat}
          </span>
        </div>
      )}

      {/* Fact */}
      <p className="text-base text-gray-800 dark:text-gray-100 leading-relaxed">
        {fact}
      </p>

      {/* Source */}
      {source && (
        <p className="text-xs text-yellow-600/70 dark:text-yellow-400/60 border-t border-yellow-200/60 dark:border-yellow-800/40 pt-3">
          Fuente: {source}
        </p>
      )}
    </div>
  )
}
