import { CheckCircle2, FileSearch, Radio, Search } from 'lucide-react'
import type { DemoEvent, RetrievalCompletePayload, RetrievalQuery, RetrievalSource } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface RetrievalTimelineProps {
  events: DemoEvent[]
}

export function RetrievalTimeline({ events }: RetrievalTimelineProps) {
  const start = events.find((event) => event.type === 'retrieval:start')
  const sources = events
    .filter((event) => event.type === 'retrieval:source')
    .map((event) => event.payload as unknown as RetrievalSource)
  const complete = [...events].reverse().find((event) => event.type === 'retrieval:complete')
  const queries = ((start?.payload as { queries?: RetrievalQuery[] } | undefined)?.queries ?? [])
  const summary = complete?.payload as RetrievalCompletePayload | undefined

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Retrieval Timeline</h2>
        <span className="text-xs font-medium text-slate-500">{sources.length}/{queries.length || 6} sources</span>
      </div>
      <div className="grid gap-4 p-4">
        <div className="grid gap-2">
          {queries.length === 0 ? (
            <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">
              Las queries pedagogicas apareceran al iniciar la investigacion.
            </div>
          ) : (
            queries.map((query) => {
              const resolved = sources.some((source) => source.query_id === query.id)
              return (
                <div key={query.id} className="grid grid-cols-[32px_1fr_auto] items-start gap-3">
                  <span
                    className={cn(
                      'flex h-8 w-8 items-center justify-center rounded-md border',
                      resolved ? 'border-emerald-200 bg-emerald-50 text-emerald-700' : 'border-slate-200 bg-slate-50 text-slate-500',
                    )}
                  >
                    {resolved ? <CheckCircle2 className="h-4 w-4" /> : <Search className="h-4 w-4" />}
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-950">{query.query}</p>
                    <p className="text-xs text-slate-500">{query.category}</p>
                  </div>
                  <span className="rounded-md bg-slate-100 px-2 py-1 text-xs text-slate-600">{query.id}</span>
                </div>
              )
            })
          )}
        </div>

        <div className="grid gap-2">
          {sources.slice(-4).map((source) => (
            <article key={`${source.query_id}-${source.url}`} className="rounded-md border bg-slate-50 p-3">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-8 w-8 items-center justify-center rounded-md bg-white text-primary">
                  <FileSearch className="h-4 w-4" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate text-sm font-semibold text-slate-950">{source.title}</p>
                    <span className="text-xs text-slate-500">{Math.round(source.confidence * 100)}%</span>
                  </div>
                  <p className="text-xs text-slate-500">{source.domain}</p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-700">{source.summary}</p>
                </div>
              </div>
            </article>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <Gauge label="Retrieval" value={summary?.retrieval_confidence ?? 0} tone="emerald" />
          <Gauge label="Pedagogy" value={summary?.pedagogical_confidence ?? 0} tone="sky" />
          <Gauge label="Grounding" value={summary?.prompt_grounding_score ?? 0} tone="violet" />
        </div>
      </div>
    </section>
  )
}

function Gauge({ label, value, tone }: { label: string; value: number; tone: 'emerald' | 'sky' | 'violet' }) {
  const colors = {
    emerald: 'bg-emerald-600',
    sky: 'bg-sky-600',
    violet: 'bg-violet-600',
  }
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <div className="mb-2 flex items-center justify-between gap-2 text-xs font-medium text-slate-600">
        <span className="flex items-center gap-1.5"><Radio className="h-3.5 w-3.5" />{label}</span>
        <span>{Math.round(value * 100)}%</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-white">
        <div className={cn('h-full rounded-full transition-all', colors[tone])} style={{ width: `${Math.max(3, value * 100)}%` }} />
      </div>
    </div>
  )
}
