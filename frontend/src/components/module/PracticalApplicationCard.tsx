import { useState } from 'react'
import { Rocket, Bookmark, BookmarkCheck } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  items: string[]
  onSave?: () => void
}

/**
 * PracticalApplicationCard — Sprint I1 + I2
 *
 * Muestra aplicaciones reales en una cuadrícula interactiva. El estudiante
 * puede "guardar" ítems para futuras referencias (estado local). La primera
 * vez que guarda un ítem dispara el callback onSave() para micro-XP.
 */
export function PracticalApplicationCard({ items, onSave }: Props) {
  const [saved,    setSaved]    = useState<Set<number>>(new Set())
  const [xpFired, setXpFired]  = useState(false)

  const toggleSave = (i: number) => {
    setSaved(prev => {
      const next = new Set(prev)
      if (next.has(i)) {
        next.delete(i)
      } else {
        next.add(i)
        if (!xpFired) {
          setXpFired(true)
          onSave?.()
        }
      }
      return next
    })
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-emerald-700 dark:text-emerald-400">
        <Rocket className="h-4 w-4" />
        <span>Guarda las que te parezcan más relevantes para tu carrera</span>
        {saved.size > 0 && (
          <span className="ml-auto text-xs font-semibold text-emerald-600 dark:text-emerald-400">
            {saved.size} guardada{saved.size > 1 ? 's' : ''}
          </span>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((app, i) => (
          <button
            key={i}
            type="button"
            onClick={() => toggleSave(i)}
            className={cn(
              'group flex items-start gap-3 p-3.5 rounded-xl border text-left transition-all duration-200',
              saved.has(i)
                ? 'border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/20 shadow-sm shadow-emerald-100 dark:shadow-emerald-900/10'
                : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 hover:border-emerald-200 dark:hover:border-emerald-800 hover:bg-emerald-50/30 dark:hover:bg-emerald-950/10',
            )}
          >
            <span className={cn(
              'shrink-0 mt-0.5 transition-colors',
              saved.has(i) ? 'text-emerald-500' : 'text-gray-300 dark:text-gray-600 group-hover:text-emerald-300',
            )}>
              {saved.has(i)
                ? <BookmarkCheck className="h-4 w-4" />
                : <Bookmark      className="h-4 w-4" />
              }
            </span>
            <p className={cn(
              'text-sm leading-relaxed transition-colors',
              saved.has(i)
                ? 'text-emerald-800 dark:text-emerald-200'
                : 'text-gray-700 dark:text-gray-300',
            )}>
              {app}
            </p>
          </button>
        ))}
      </div>
    </div>
  )
}
