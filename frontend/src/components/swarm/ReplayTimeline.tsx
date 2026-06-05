import { Clock3, GitCommitHorizontal } from 'lucide-react'
import type { CognitiveReplayEvent } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface ReplayTimelineProps {
  events: CognitiveReplayEvent[]
  activeIndex: number
}

export function ReplayTimeline({ events, activeIndex }: ReplayTimelineProps) {
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Cognitive Replay Timeline</h2>
      </div>
      <div className="max-h-[420px] space-y-2 overflow-y-auto p-4">
        {events.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Carga un replay para ver la linea cognitiva.</div>
        ) : (
          events.map((event, index) => (
            <article
              key={`${event.id}-${event.event_type}`}
              className={cn(
                'grid grid-cols-[28px_1fr] gap-3 rounded-md border p-3',
                index <= activeIndex ? 'bg-slate-50' : 'bg-white opacity-45',
                index === activeIndex && 'border-primary',
              )}
            >
              <span className="mt-0.5 flex h-7 w-7 items-center justify-center rounded-md bg-white text-primary">
                <GitCommitHorizontal className="h-4 w-4" />
              </span>
              <div className="min-w-0">
                <div className="flex items-center justify-between gap-3">
                  <p className="truncate text-sm font-semibold text-slate-950">{event.cognitive_label}</p>
                  <span className="text-xs text-slate-500">#{event.id}</span>
                </div>
                <p className="mt-1 text-xs text-slate-600">{event.phase} · {event.agent_name} · {event.event_type}</p>
                <p className="mt-1 flex items-center gap-1.5 text-xs text-slate-500">
                  <Clock3 className="h-3.5 w-3.5" />
                  +{Math.round(event.latency_ms)}ms {event.confidence != null ? `· ${Math.round(event.confidence * 100)}%` : ''}
                </p>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  )
}
