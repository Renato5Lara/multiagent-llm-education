import { useState, useCallback } from 'react'
import { ExternalLink, MessageSquare, Send, ChevronDown, Loader2, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useInteractEngagement } from '@/hooks/useEngagement'
import type { EngagementResource } from '@/types/engagement'

type TheoryState = 'collapsed' | 'open' | 'submitting' | 'saved'

interface Props {
  resource: EngagementResource
  sessionId: string
}

/**
 * RealNewsCard — Sprint C3 (+ theory reflection)
 *
 * Shows a real-world news item to anchor the module topic in current reality.
 * Optionally collects a student "theory" about why this happened — stored as:
 *   { theory: "..." }  in engagement_interactions.response_data
 *
 * Metadata fields: source_hint (string), year (string)
 * resource.media_url: optional link to original article
 */
export function RealNewsCard({ resource, sessionId }: Props) {
  const [theoryState, setTheoryState] = useState<TheoryState>('collapsed')
  const [theoryText, setTheoryText]   = useState('')
  const [savedTheory, setSavedTheory] = useState('')
  const { mutate: interactMutate }    = useInteractEngagement()

  const meta       = resource.resource_metadata as Record<string, unknown>
  const sourceHint = meta.source_hint ? String(meta.source_hint) : null
  const year       = meta.year ? String(meta.year) : null
  const hasLink    = !!resource.media_url

  const handleSaveTheory = useCallback(() => {
    const trimmed = theoryText.trim()
    if (!trimmed) return
    setTheoryState('submitting')
    interactMutate(
      {
        session_id:       sessionId,
        resource_id:      resource.id,
        interaction_type: 'submit',
        response_data:    { theory: trimmed },
      },
      {
        onSuccess: () => { setSavedTheory(trimmed); setTheoryState('saved') },
        onError:   () => { setSavedTheory(trimmed); setTheoryState('saved') },
      },
    )
  }, [theoryText, sessionId, resource.id, interactMutate])

  return (
    <div className="relative overflow-hidden rounded-xl border border-blue-200 dark:border-blue-800 bg-gradient-to-br from-slate-50 via-blue-50 to-sky-50 dark:from-slate-900/50 dark:via-blue-950/30 dark:to-sky-950/20">

      {/* Newspaper-strip top bar */}
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-600 via-sky-500 to-blue-600" />
      <div className="pointer-events-none absolute -top-8 -right-8 w-32 h-32 rounded-full bg-blue-200/20 dark:bg-blue-500/10" />

      <div className="p-6 space-y-4">

        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="text-3xl select-none leading-none">📰</span>
            <div>
              <p className="text-xs font-mono font-bold tracking-widest text-blue-600 dark:text-blue-400 uppercase">
                Noticia real
              </p>
              <p className="text-xs text-blue-700/60 dark:text-blue-400/50 mt-0.5">
                Esto está pasando en el mundo ahora mismo
              </p>
            </div>
          </div>
          {year && (
            <span className="shrink-0 text-xs font-mono text-blue-500 dark:text-blue-400 border border-blue-200 dark:border-blue-700 rounded px-2 py-0.5 bg-white/60 dark:bg-blue-950/30">
              {year}
            </span>
          )}
        </div>

        {/* Headline + body */}
        <div className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold leading-snug text-gray-900 dark:text-gray-100">
            {resource.title}
          </h2>
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {resource.content}
          </p>
        </div>

        {/* Divider */}
        <div className="h-px bg-blue-200/60 dark:bg-blue-700/40" />

        {/* Source + link */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {sourceHint ? (
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="text-xs text-blue-700 dark:text-blue-400 font-medium">{sourceHint}</span>
            </div>
          ) : (
            <span className="text-xs text-muted-foreground italic">Fuente verificada</span>
          )}
          {hasLink && (
            <a
              href={resource.media_url!}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors underline-offset-2 hover:underline"
            >
              Ver artículo original
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>

        {/* Theory section */}
        <div className="border-t border-blue-200/60 dark:border-blue-700/40 pt-3">
          {theoryState === 'saved' ? (
            <div className="flex items-start gap-2 animate-in fade-in duration-400">
              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
              <div className="space-y-0.5">
                <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">Teoría guardada</p>
                <p className="text-xs text-gray-600 dark:text-gray-400 italic">"{savedTheory}"</p>
                <p className="text-xs text-gray-500 dark:text-gray-500">
                  Los agentes la usan para conocer tu intuición inicial: al final del módulo podrás compararla con lo que descubriste.
                </p>
              </div>
            </div>
          ) : theoryState === 'collapsed' ? (
            <button
              type="button"
              onClick={() => setTheoryState('open')}
              className="flex items-center gap-2 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              💭 Tengo una teoría sobre por qué ocurrió esto
              <ChevronDown className="h-3 w-3 opacity-60" />
            </button>
          ) : (
            <div className="space-y-2 animate-in fade-in slide-in-from-top-1 duration-300">
              <p className="text-xs font-semibold text-blue-700 dark:text-blue-400 flex items-center gap-1.5">
                <MessageSquare className="h-3.5 w-3.5" />
                ¿Por qué crees que esto ocurrió?
              </p>
              <textarea
                value={theoryText}
                onChange={e => setTheoryText(e.target.value)}
                placeholder="Tu teoría aquí..."
                rows={2}
                disabled={theoryState === 'submitting'}
                className={cn(
                  'w-full resize-none rounded-lg border border-blue-200 dark:border-blue-700',
                  'bg-white/80 dark:bg-blue-950/30 px-3 py-2 text-sm',
                  'text-gray-800 dark:text-gray-100 placeholder:text-blue-400/50',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-400',
                  'disabled:opacity-50 disabled:cursor-not-allowed transition-colors',
                )}
              />
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleSaveTheory}
                  disabled={!theoryText.trim() || theoryState === 'submitting'}
                  className="gap-1.5 h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white"
                >
                  {theoryState === 'submitting'
                    ? <Loader2 className="h-3 w-3 animate-spin" />
                    : <Send className="h-3 w-3" />
                  }
                  Guardar teoría
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setTheoryState('collapsed')}
                  disabled={theoryState === 'submitting'}
                  className="h-7 text-xs text-muted-foreground"
                >
                  Cancelar
                </Button>
              </div>
              <p className="text-[11px] text-blue-600/70 dark:text-blue-400/60">
                Tu teoría se guarda para el cierre del módulo: ahí la compararás con lo que hayas descubierto.
              </p>
            </div>
          )}
        </div>

        <p className="text-xs text-blue-600/60 dark:text-blue-400/50 italic">
          Este caso real conecta directamente con los conceptos que explorarás en este módulo.
        </p>
      </div>
    </div>
  )
}
