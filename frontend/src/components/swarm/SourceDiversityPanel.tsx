import { Globe2 } from 'lucide-react'
import type { DemoEvent, RetrievalCompletePayload, RetrievalSource } from '@/types/swarmDemo'

interface SourceDiversityPanelProps {
  events: DemoEvent[]
}

export function SourceDiversityPanel({ events }: SourceDiversityPanelProps) {
  const sources = events
    .filter((event) => event.type === 'retrieval:source')
    .map((event) => event.payload as unknown as RetrievalSource)
  const complete = [...events].reverse().find((event) => event.type === 'retrieval:complete')
  const summary = complete?.payload as RetrievalCompletePayload | undefined
  const domains = sources.reduce<Record<string, number>>((acc, source) => {
    acc[source.domain] = (acc[source.domain] ?? 0) + 1
    return acc
  }, {})
  const max = Math.max(1, ...Object.values(domains))

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Source Diversity</h2>
        <span className="text-xs font-medium text-slate-500">{summary ? Math.round(summary.diversity_score * 100) : 0}% diversity</span>
      </div>
      <div className="space-y-3 p-4">
        {sources.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Esperando fuentes Tavily.</div>
        ) : (
          Object.entries(domains).map(([domain, count]) => (
            <div key={domain} className="grid gap-1.5">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="flex min-w-0 items-center gap-2 font-medium text-slate-900">
                  <Globe2 className="h-4 w-4 shrink-0 text-slate-500" />
                  <span className="truncate">{domain}</span>
                </span>
                <span className="text-slate-600">{count}</span>
              </div>
              <div className="h-2.5 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full rounded-full bg-cyan-600" style={{ width: `${Math.max(8, (count / max) * 100)}%` }} />
              </div>
            </div>
          ))
        )}
        <div className="grid grid-cols-3 gap-2 pt-2 text-xs text-slate-600">
          <span>Sources {summary?.source_count ?? sources.length}</span>
          <span>Domains {summary?.unique_domains ?? Object.keys(domains).length}</span>
          <span>Avg {sources.length ? Math.round((sources.reduce((sum, source) => sum + source.confidence, 0) / sources.length) * 100) : 0}%</span>
        </div>
      </div>
    </section>
  )
}
