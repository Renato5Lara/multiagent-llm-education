import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  index: number
  content: string
  onRead?: () => void
}

function splitContent(text: string): { preview: string; rest: string } {
  const sentences = text.split(/(?<=[.!?])\s+/)
  if (sentences.length <= 2) return { preview: text, rest: '' }
  return {
    preview:  sentences.slice(0, 2).join(' '),
    rest:     sentences.slice(2).join(' '),
  }
}

/**
 * ConceptCard — Sprint I1
 *
 * Muestra un párrafo conceptual de la explicación pedagógica como bloque
 * interactivo con vista previa y expansión. Llama onRead() la primera vez
 * que el estudiante abre el contenido (señal para micro-XP).
 */
export function ConceptCard({ index, content, onRead }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [read,     setRead]     = useState(false)

  const { preview, rest } = splitContent(content)
  const hasMore = rest.length > 0

  const handleToggle = () => {
    if (!expanded && !read) {
      setRead(true)
      onRead?.()
    }
    setExpanded(v => !v)
  }

  return (
    <div className={cn(
      'rounded-xl border transition-all duration-200 overflow-hidden',
      read
        ? 'border-indigo-200 dark:border-indigo-800 bg-indigo-50/40 dark:bg-indigo-950/20'
        : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50',
    )}>
      <button
        type="button"
        onClick={hasMore ? handleToggle : undefined}
        className={cn(
          'w-full text-left px-4 py-3.5 flex items-start gap-3',
          hasMore && 'hover:bg-indigo-50/50 dark:hover:bg-indigo-950/10 transition-colors',
        )}
      >
        {/* Index badge */}
        <div className={cn(
          'w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 mt-0.5',
          read
            ? 'bg-indigo-500 text-white'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
        )}>
          {index}
        </div>

        {/* Text */}
        <p className="flex-1 text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
          {preview}
          {!expanded && rest && (
            <span className="text-indigo-400/70 dark:text-indigo-500/60"> …</span>
          )}
        </p>

        {/* Chevron */}
        {hasMore && (
          <span className="shrink-0 mt-0.5 text-muted-foreground">
            {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </span>
        )}
      </button>

      {/* Expanded rest */}
      {expanded && rest && (
        <div className="px-4 pb-4 pt-0 animate-in fade-in duration-200">
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed pl-10">
            {rest}
          </p>
        </div>
      )}
    </div>
  )
}
