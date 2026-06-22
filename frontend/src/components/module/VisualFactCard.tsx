import { useEffect } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  fact:        string
  source?:     string
  stat?:       string
  onComplete?: () => void
}

// Passive card — grants XP on mount, no interaction required.
export function VisualFactCard({ fact, source, stat, onComplete }: Props) {
  useEffect(() => {
    onComplete?.()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className={cn(
      'rounded-xl border border-yellow-200 dark:border-yellow-800 overflow-hidden',
      'animate-in fade-in slide-in-from-bottom-2 duration-400',
    )}>
      {/* Top accent strip */}
      <div className="h-1.5 bg-gradient-to-r from-yellow-400 via-amber-400 to-orange-400" />

      <div className="bg-gradient-to-br from-yellow-50 via-amber-50 to-orange-50 dark:from-yellow-950/30 dark:via-amber-950/30 dark:to-orange-950/20 p-6 space-y-5">

        {/* Header */}
        <div className="flex items-center gap-3">
          <span className="text-3xl select-none leading-none animate-in zoom-in duration-500">🤯</span>
          <div>
            <p className="text-xs font-mono font-bold tracking-widest text-yellow-600 dark:text-yellow-400 uppercase">
              ¿Sabías que...?
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">Dato curioso del mundo real</p>
          </div>
        </div>

        {/* Stat — big dramatic number */}
        {stat && (
          <div className="flex justify-center py-3">
            <div className="text-center">
              <span className={cn(
                'block text-6xl font-black tracking-tight leading-none',
                'text-transparent bg-clip-text bg-gradient-to-r from-yellow-500 via-amber-500 to-orange-500',
                'drop-shadow-sm',
                'animate-in zoom-in duration-600',
              )}>
                {stat}
              </span>
              <div className="mt-2 h-0.5 w-16 mx-auto rounded-full bg-gradient-to-r from-yellow-300 to-orange-300" />
            </div>
          </div>
        )}

        {/* Fact */}
        <p className="text-base text-gray-800 dark:text-gray-100 leading-relaxed font-medium">
          {fact}
        </p>

        {/* Source */}
        {source && (
          <div className="flex items-center gap-2 border-t border-yellow-200/60 dark:border-yellow-800/40 pt-3">
            <span className="text-xs text-yellow-600/60 dark:text-yellow-400/50">📚</span>
            <p className="text-xs text-yellow-600/70 dark:text-yellow-400/60">
              {source}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
