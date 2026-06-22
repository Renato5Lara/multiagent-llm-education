import { useState } from 'react'
import { AlertTriangle, CheckCircle, Eye } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface Props {
  misconception: string
  correction: string
  severity: string
  index: number
  onReveal?: () => void
}

const SEVERITY_CONFIG = {
  high:   { label: 'Crítico',    color: 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800',    icon: 'text-red-500',    badge: 'destructive' as const },
  medium: { label: 'Importante', color: 'bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-800', icon: 'text-amber-500', badge: 'warning' as const },
  low:    { label: 'Menor',      color: 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-100 dark:border-yellow-900', icon: 'text-yellow-500', badge: 'secondary' as const },
}

/**
 * CommonMistakeCard — Sprint I1
 *
 * Muestra un error conceptual frecuente con mecánica de revelación:
 * el estudiante ve el error primero y decide si conoce la corrección
 * antes de verla. Esto activa la reflexión metacognitiva.
 */
export function CommonMistakeCard({ misconception, correction, severity, index, onReveal }: Props) {
  const [revealed, setRevealed] = useState(false)
  const cfg = SEVERITY_CONFIG[severity as keyof typeof SEVERITY_CONFIG] ?? SEVERITY_CONFIG.medium

  const handleReveal = () => {
    if (!revealed) {
      setRevealed(true)
      onReveal?.()
    }
  }

  return (
    <div className={cn('rounded-xl border overflow-hidden transition-all duration-300', cfg.color)}>
      {/* Header */}
      <div className="flex items-start gap-3 px-4 py-3.5">
        <AlertTriangle className={cn('h-4 w-4 mt-0.5 shrink-0', cfg.icon)} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold text-gray-600 dark:text-gray-400">
              Error #{index}
            </span>
            <Badge variant={cfg.badge} className="text-xs">
              {cfg.label}
            </Badge>
          </div>
          <p className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
            {misconception}
          </p>
        </div>
      </div>

      {/* Reveal / correction */}
      {revealed ? (
        <div className="mx-4 mb-4 rounded-lg bg-white/70 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800 px-4 py-3 flex items-start gap-2.5 animate-in fade-in duration-300">
          <CheckCircle className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
          <p className="text-sm text-emerald-800 dark:text-emerald-300 leading-relaxed">
            {correction}
          </p>
        </div>
      ) : (
        <button
          type="button"
          onClick={handleReveal}
          className="mx-4 mb-4 w-[calc(100%-2rem)] flex items-center justify-center gap-2 rounded-lg border border-dashed border-current/30 py-2.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:border-emerald-300 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20 transition-colors"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver la corrección
        </button>
      )}
    </div>
  )
}
