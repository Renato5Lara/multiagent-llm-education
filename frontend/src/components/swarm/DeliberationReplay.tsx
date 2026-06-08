import { Vote } from 'lucide-react'
import type { CognitiveReplayEvent } from '@/types/swarmDemo'

interface DeliberationReplayProps {
  events: CognitiveReplayEvent[]
}

export function DeliberationReplay({ events }: DeliberationReplayProps) {
  const deliberation = events.filter((event) => ['agent.thinking', 'vote.cast', 'consensus.updated', 'session.completed'].includes(event.event_type))
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Deliberation Replay</h2>
      </div>
      <div className="space-y-3 p-4">
        {deliberation.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">La deliberacion aparecera cuando avance el replay.</div>
        ) : (
          deliberation.map((event) => (
            <article key={`${event.id}-${event.event_type}`} className="rounded-md border bg-slate-50 p-3">
              <div className="flex items-center justify-between gap-3">
                <span className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <Vote className="h-4 w-4 text-primary" />
                  {event.agent_name}
                </span>
                <span className="text-xs text-slate-500">{event.event_type}</span>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-slate-700">
                {String(event.payload.reason || event.cognitive_label)}
              </p>
            </article>
          ))
        )}
      </div>
    </section>
  )
}
