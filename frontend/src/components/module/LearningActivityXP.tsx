import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface Props {
  total: number
  flash: { amount: number; key: number } | null
}

/**
 * LearningActivityXP — Sprint I3
 *
 * Micro-gamificación para el tab de contenido del módulo. Muestra el XP
 * acumulado en este módulo por interacciones (concepto explorado +2, ejemplo
 * completado +3, reflexión +5). Completamente local — sin llamadas al backend.
 * El Sprint I5 conectará esto al sistema de XP persistente.
 */
export function LearningActivityXP({ total, flash }: Props) {
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (total > 0) setVisible(true)
  }, [total])

  if (!visible) return null

  return (
    <div className="flex items-center justify-between rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50/60 dark:bg-amber-950/20 px-4 py-2.5">
      <div className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
        <span className="text-base select-none">⭐</span>
        <span className="font-medium">XP del módulo</span>
        <span className="font-mono font-bold text-amber-800 dark:text-amber-300">
          {total} XP
        </span>
      </div>

      {flash && (
        <span
          key={flash.key}
          className={cn(
            'text-sm font-bold text-amber-600 dark:text-amber-400',
            'animate-in fade-in slide-in-from-right-2 duration-200',
          )}
        >
          +{flash.amount} XP ✨
        </span>
      )}
    </div>
  )
}
