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

/**
 * ConceptCard — Sprint L5 / Sprint 2.1 (refinamiento visual)
 *
 * Referencia: pantalla "Contenido Adaptativo" — sección "Understanding Base Cases"
 * con tipografía grande, espaciado generoso y bloques informativos bien separados.
 *
 * Mejoras vs versión anterior:
 *   • Header más alto: icono text-3xl, padding generoso (px-5 py-4)
 *   • Barra de acento superior en vez de borde lateral — más impacto visual
 *   • "Idea clave" callout más grande (text-sm → text-base para el contenido)
 *   • Sección expandible con mayor separación entre párrafos
 */
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
      {/* Thin accent bar top — referencia: "Contenido Adaptativo" section divider */}
      <div className={cn(
        'h-[3px] w-full transition-colors duration-300',
        read ? 'bg-indigo-400 dark:bg-indigo-600' : 'bg-gray-200 dark:bg-gray-700',
      )} />

      {/* Gradient header — más alto y espacioso */}
      <div className={cn(
        'px-5 py-4 flex items-center gap-4 transition-colors duration-300',
        read
          ? 'bg-gradient-to-r from-indigo-50 to-violet-50 dark:from-indigo-950/40 dark:to-violet-950/30'
          : 'bg-gradient-to-r from-gray-50 to-slate-50 dark:from-gray-900/60 dark:to-slate-900/40',
      )}>
        {/* Domain icon + index badge — icon más grande */}
        <div className="relative shrink-0">
          <span className="text-3xl select-none leading-none">{icon}</span>
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
          <p className={cn(
            'text-[10px] font-mono font-bold tracking-[0.25em] uppercase',
            read
              ? 'text-indigo-600 dark:text-indigo-400'
              : 'text-gray-500 dark:text-gray-400',
          )}>
            📖 Concepto
          </p>
          {title && (
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 mt-0.5 leading-snug">
              {title}
            </p>
          )}
        </div>

        {hasMore && (
          <button
            type="button"
            onClick={handleToggle}
            className={cn(
              'shrink-0 p-1.5 rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/5',
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

      {/* Key idea callout — más espacioso, texto más grande */}
      <div className={cn(
        'mx-5 mt-5 rounded-xl border-l-4 px-4 py-4 transition-colors duration-300',
        read
          ? 'border-indigo-400 dark:border-indigo-600 bg-indigo-50/60 dark:bg-indigo-950/20'
          : 'border-gray-300 dark:border-gray-600 bg-gray-50/60 dark:bg-gray-800/20',
      )}>
        <p className={cn(
          'text-[10px] font-semibold uppercase tracking-wide mb-2',
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
          'mx-5 mt-3 overflow-hidden transition-all duration-300',
          expanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0',
        )}>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed pb-1">
            {rest}
          </p>
        </div>
      )}

      {/* Footer: ver más / ver menos */}
      <div className="px-5 py-4 mt-1">
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
