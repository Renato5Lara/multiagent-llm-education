import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { getConceptIcon } from '@/lib/conceptIcons'

interface Props {
  index:    number
  content:  string
  title?:   string
  onRead?:  () => void
}

// Split content into key idea (first sentence) + rest.
function splitContent(text: string): { keyIdea: string; rest: string } {
  const sentences = text.split(/(?<=[.!?])\s+/)
  if (sentences.length <= 1) return { keyIdea: text, rest: '' }
  return {
    keyIdea: sentences[0],
    rest:    sentences.slice(1).join(' '),
  }
}

export function ConceptCard({ index, content, title, onRead }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [read,     setRead]     = useState(false)

  const { keyIdea, rest } = splitContent(content)
  const hasMore = rest.length > 0
  const icon    = getConceptIcon(title ?? content.slice(0, 60))

  const handleToggle = () => {
    if (!expanded && !read) {
      setRead(true)
      onRead?.()
    }
    if (hasMore) setExpanded(v => !v)
  }

  // Fire onRead immediately on first render if there's nothing to expand
  const handleSingleSentenceRead = () => {
    if (!hasMore && !read) {
      setRead(true)
      onRead?.()
    }
  }

  return (
    <div
      className={cn(
        'rounded-xl border overflow-hidden transition-all duration-300',
        'animate-in fade-in slide-in-from-bottom-2 duration-400',
        read
          ? 'border-indigo-200 dark:border-indigo-800'
          : 'border-gray-200 dark:border-gray-700',
      )}
      onMouseEnter={!hasMore ? handleSingleSentenceRead : undefined}
    >
      {/* Gradient header */}
      <div className={cn(
        'px-4 py-3 flex items-center gap-3 transition-colors duration-300',
        read
          ? 'bg-gradient-to-r from-indigo-50 to-violet-50 dark:from-indigo-950/40 dark:to-violet-950/30'
          : 'bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-900/60 dark:to-slate-900/40',
      )}>
        {/* Domain icon + index badge */}
        <div className="relative shrink-0">
          <span className="text-2xl select-none leading-none">{icon}</span>
          <span className={cn(
            'absolute -bottom-1 -right-1 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold border',
            read
              ? 'bg-indigo-500 text-white border-indigo-400'
              : 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 border-gray-300 dark:border-gray-600',
          )}>
            {index}
          </span>
        </div>

        <div className="flex-1 min-w-0">
          {title && (
            <p className={cn(
              'text-xs font-mono font-bold tracking-widest uppercase truncate',
              read
                ? 'text-indigo-600 dark:text-indigo-400'
                : 'text-gray-500 dark:text-gray-400',
            )}>
              📖 Concepto
            </p>
          )}
          {title && (
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 truncate">
              {title}
            </p>
          )}
          {!title && (
            <p className={cn(
              'text-xs font-mono font-bold tracking-widest uppercase',
              read ? 'text-indigo-600 dark:text-indigo-400' : 'text-gray-500 dark:text-gray-400',
            )}>
              📖 Concepto
            </p>
          )}
        </div>

        {hasMore && (
          <button
            type="button"
            onClick={handleToggle}
            className={cn(
              'shrink-0 p-1 rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/5',
              read ? 'text-indigo-400 dark:text-indigo-500' : 'text-muted-foreground',
            )}
            aria-label={expanded ? 'Contraer' : 'Expandir'}
          >
            {expanded
              ? <ChevronUp   className="h-4 w-4" />
              : <ChevronDown className="h-4 w-4" />
            }
          </button>
        )}
      </div>

      {/* Key idea callout */}
      <div className={cn(
        'mx-4 mt-4 mb-0 rounded-lg border-l-4 px-4 py-3 transition-colors duration-300',
        read
          ? 'border-indigo-400 dark:border-indigo-600 bg-indigo-50/60 dark:bg-indigo-950/20'
          : 'border-gray-300 dark:border-gray-600 bg-gray-50/60 dark:bg-gray-800/20',
      )}>
        <p className={cn(
          'text-xs font-semibold uppercase tracking-wide mb-1',
          read ? 'text-indigo-500 dark:text-indigo-400' : 'text-gray-400 dark:text-gray-500',
        )}>
          💡 Idea clave
        </p>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-100 leading-relaxed">
          {keyIdea}
        </p>
      </div>

      {/* Expandable rest */}
      {hasMore && (
        <div className={cn(
          'mx-4 mt-3 mb-0 overflow-hidden transition-all duration-300',
          expanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0',
        )}>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed pb-1">
            {rest}
          </p>
        </div>
      )}

      {/* Footer: ver más / ver menos */}
      <div className="px-4 py-3 mt-2">
        {hasMore ? (
          <button
            type="button"
            onClick={handleToggle}
            className={cn(
              'text-xs font-semibold transition-colors hover:underline',
              read
                ? 'text-indigo-500 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-200'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700',
            )}
          >
            {expanded ? '↑ Ver menos' : '↓ Ver explicación completa'}
          </button>
        ) : (
          <div className="h-1" />
        )}
      </div>
    </div>
  )
}
