import { Activity, AlertTriangle, Brain, Database, FileSearch, Lightbulb, MessageSquareText, Search, ShieldAlert, ShieldCheck, Vote } from 'lucide-react'
import type { DemoEvent } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface LiveSessionFeedProps {
  events: DemoEvent[]
}

const iconByType: Record<string, typeof Activity> = {
  'agent.thinking': Brain,
  'vote.cast': Vote,
  'memory.published': Database,
  'anomaly.detected': ShieldAlert,
  'retrieval:start': Search,
  'retrieval:source': FileSearch,
  'retrieval:complete': FileSearch,
  'contradiction:detected': AlertTriangle,
  'misconception:detected': Lightbulb,
  'prompt:generated': MessageSquareText,
  'consistency:validated': ShieldCheck,
}

export function LiveSessionFeed({ events }: LiveSessionFeedProps) {
  const visible = [...events].reverse().slice(0, 18)

  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Live Session Feed</h2>
      </div>
      <div className="max-h-[560px] space-y-3 overflow-y-auto p-4">
        {visible.length === 0 ? (
          <div className="rounded-md border border-dashed p-6 text-sm text-slate-500">
            Esperando eventos SSE de la sesion.
          </div>
        ) : (
          visible.map((event) => {
            const Icon = iconByType[event.type] ?? Activity
            return (
              <article key={event.id} className="rounded-md border bg-slate-50 p-3">
                <div className="flex items-center gap-2">
                  <span className="flex h-8 w-8 items-center justify-center rounded-md bg-white text-primary">
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-3">
                      <p className="truncate text-sm font-semibold text-slate-950">{event.type}</p>
                      <span className="text-xs text-slate-500">#{event.id}</span>
                    </div>
                    <p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleTimeString()}</p>
                  </div>
                </div>
                <pre
                  className={cn(
                    'mt-3 max-h-28 overflow-auto rounded-md bg-white p-2 text-xs leading-relaxed text-slate-700',
                    event.type === 'anomaly.detected' && 'border border-red-200 bg-red-50 text-red-900',
                  )}
                >
                  {JSON.stringify(event.payload, null, 2)}
                </pre>
              </article>
            )
          })
        )}
      </div>
    </section>
  )
}
