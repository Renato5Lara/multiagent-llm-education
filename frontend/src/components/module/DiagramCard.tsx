import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  title:        string
  description?: string
  steps:        string[]
  onComplete?:  () => void
}

export function DiagramCard({ title, description, steps, onComplete }: Props) {
  const [visibleCount, setVisibleCount] = useState(0)

  // Passive: grant XP on mount + stagger step reveal
  useEffect(() => {
    onComplete?.()
    let i = 0
    const iv = setInterval(() => {
      i++
      setVisibleCount(i)
      if (i >= steps.length) clearInterval(iv)
    }, 180)
    return () => clearInterval(iv)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="rounded-xl border border-indigo-200 dark:border-indigo-800 bg-gradient-to-br from-indigo-50 via-violet-50 to-purple-50 dark:from-indigo-950/30 dark:via-violet-950/30 dark:to-purple-950/20 p-6 space-y-5 animate-in fade-in slide-in-from-bottom-2 duration-400">

      {/* Header */}
      <div className="flex items-center gap-3">
        <span className="text-3xl select-none leading-none">🔄</span>
        <div>
          <p className="text-xs font-mono font-bold tracking-widest text-indigo-600 dark:text-indigo-400 uppercase">
            Flujo del proceso
          </p>
          <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mt-0.5">
            {title}
          </p>
        </div>
      </div>

      {description && (
        <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
          {description}
        </p>
      )}

      {/* Flowchart steps */}
      <div className="relative pl-6">
        {steps.map((step, i) => (
          <div
            key={i}
            className={cn(
              'relative transition-all duration-300',
              i < visibleCount
                ? 'opacity-100 translate-y-0'
                : 'opacity-0 translate-y-2',
            )}
          >
            {/* Vertical connector line */}
            {i < steps.length - 1 && (
              <div className="absolute left-[-12px] top-8 h-8 w-0.5 bg-indigo-200 dark:bg-indigo-700" />
            )}

            {/* Step row */}
            <div className="flex items-start gap-3 mb-2">
              {/* Circle indicator */}
              <div className={cn(
                'absolute left-[-20px] top-1.5 w-4 h-4 rounded-full border-2 flex items-center justify-center',
                i < visibleCount
                  ? 'border-indigo-500 bg-indigo-100 dark:bg-indigo-900/40'
                  : 'border-indigo-200 dark:border-indigo-700 bg-white dark:bg-indigo-950/30',
              )}>
                <div className={cn(
                  'w-1.5 h-1.5 rounded-full transition-colors',
                  i < visibleCount
                    ? 'bg-indigo-500'
                    : 'bg-indigo-200 dark:bg-indigo-700',
                )} />
              </div>

              {/* Step content */}
              <div className={cn(
                'flex-1 rounded-lg border px-3 py-2.5 mb-6 transition-colors duration-200',
                i < visibleCount
                  ? 'border-indigo-200 dark:border-indigo-700 bg-white/70 dark:bg-indigo-950/20'
                  : 'border-indigo-100 dark:border-indigo-800 bg-white/30 dark:bg-indigo-950/10',
              )}>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-indigo-400 dark:text-indigo-500 shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                    {step}
                  </p>
                </div>
              </div>
            </div>

            {/* Arrow between steps */}
            {i < steps.length - 1 && i < visibleCount - 1 && (
              <div className="absolute left-[-13px] top-[42px] text-indigo-400 dark:text-indigo-600 text-xs leading-none select-none">
                ↓
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
