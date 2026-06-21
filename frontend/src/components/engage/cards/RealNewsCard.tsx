import { ExternalLink } from 'lucide-react'
import type { EngagementResource } from '@/types/engagement'

interface Props {
  resource: EngagementResource
}

/**
 * RealNewsCard — Sprint C3
 *
 * Shows a real-world news item to anchor the module topic in current reality.
 * Designed to signal "this is happening now — what you learn today is relevant."
 *
 * Metadata fields used:
 *   source_hint : string  — publication or author name
 *   year        : string  — publication year
 *
 * resource.media_url : optional link to original article
 */
export function RealNewsCard({ resource }: Props) {
  const meta       = resource.resource_metadata as Record<string, unknown>
  const sourceHint = meta.source_hint ? String(meta.source_hint) : null
  const year       = meta.year ? String(meta.year) : null
  const hasLink    = !!resource.media_url

  return (
    <div className="relative overflow-hidden rounded-xl border border-blue-200 dark:border-blue-800 bg-gradient-to-br from-slate-50 via-blue-50 to-sky-50 dark:from-slate-900/50 dark:via-blue-950/30 dark:to-sky-950/20">

      {/* Newspaper-strip top bar */}
      <div className="h-1.5 w-full bg-gradient-to-r from-blue-600 via-sky-500 to-blue-600" />

      {/* Decorative circles */}
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

          {/* Year badge */}
          {year && (
            <span className="shrink-0 text-xs font-mono text-blue-500 dark:text-blue-400 border border-blue-200 dark:border-blue-700 rounded px-2 py-0.5 bg-white/60 dark:bg-blue-950/30">
              {year}
            </span>
          )}
        </div>

        {/* Headline */}
        <div className="space-y-2">
          <h2 className="text-lg sm:text-xl font-bold leading-snug text-gray-900 dark:text-gray-100">
            {resource.title}
          </h2>

          {/* Article body */}
          <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
            {resource.content}
          </p>
        </div>

        {/* Divider */}
        <div className="h-px bg-blue-200/60 dark:bg-blue-700/40" />

        {/* Footer: source + optional link */}
        <div className="flex items-center justify-between gap-3 flex-wrap">
          {sourceHint ? (
            <div className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
              <span className="text-xs text-blue-700 dark:text-blue-400 font-medium">
                {sourceHint}
              </span>
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

        {/* Relevance note */}
        <p className="text-xs text-blue-600/60 dark:text-blue-400/50 italic">
          Este caso real conecta directamente con los conceptos que explorarás en este módulo.
        </p>
      </div>
    </div>
  )
}
