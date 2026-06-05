import { Database } from 'lucide-react'
import type { CognitiveReplayEvent } from '@/types/swarmDemo'

interface SharedMemoryReplayProps {
  events: CognitiveReplayEvent[]
}

export function SharedMemoryReplay({ events }: SharedMemoryReplayProps) {
  const memory = events.filter((event) => event.event_type === 'memory.published')
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Shared Memory Replay</h2>
      </div>
      <div className="space-y-3 p-4">
        {memory.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Sin publicaciones de memoria en este frame.</div>
        ) : (
          memory.map((event) => (
            <article key={`${event.id}-${String(event.payload.key)}`} className="rounded-md border bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex min-w-0 items-center gap-2 text-sm font-semibold text-slate-950">
                  <Database className="h-4 w-4 shrink-0 text-emerald-700" />
                  <span className="truncate">{String(event.payload.key || event.metadata.key || 'memory')}</span>
                </span>
                <span className="text-xs text-slate-500">{event.confidence != null ? `${Math.round(event.confidence * 100)}%` : ''}</span>
              </div>
              <p className="mt-2 text-xs text-slate-600">agent={event.agent_name} · trace={event.trace_id.slice(0, 12)}</p>
            </article>
          ))
        )}
      </div>
    </section>
  )
}
