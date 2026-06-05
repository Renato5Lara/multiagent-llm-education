import { BrainCircuit, Fingerprint } from 'lucide-react'
import type { CognitiveReplay, CognitiveReplayEvent } from '@/types/swarmDemo'

interface CognitiveReplayViewProps {
  replay: CognitiveReplay | null
  activeEvent: CognitiveReplayEvent | null
}

export function CognitiveReplayView({ replay, activeEvent }: CognitiveReplayViewProps) {
  const summary = replay?.summary
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Cognitive Replay View</h2>
      </div>
      <div className="grid gap-4 p-4">
        <div className="grid gap-3 sm:grid-cols-4">
          <Metric label="Events" value={String(summary?.event_count ?? 0)} />
          <Metric label="Sources" value={String(summary?.retrieval_sources ?? 0)} />
          <Metric label="Votes" value={String(summary?.consensus_votes ?? 0)} />
          <Metric label="Prompts" value={String(summary?.generated_prompts ?? 0)} />
        </div>
        <div className="rounded-md border bg-slate-50 p-4">
          {activeEvent ? (
            <div className="grid gap-3">
              <div className="flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-primary" />
                <p className="text-sm font-semibold text-slate-950">{activeEvent.cognitive_label}</p>
              </div>
              <p className="text-sm text-slate-700">{activeEvent.narrative_step || activeEvent.event_type}</p>
              <div className="grid gap-2 text-xs text-slate-600 md:grid-cols-2">
                <span>Phase: {activeEvent.phase}</span>
                <span>Agent: {activeEvent.agent_name}</span>
                <span>Trace: {activeEvent.trace_id.slice(0, 18)}</span>
                <span>Correlation: {activeEvent.correlation_id}</span>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Fingerprint className="h-4 w-4" />
              Esperando frame cognitivo.
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <p className="text-xs font-medium uppercase text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-950">{value}</p>
    </div>
  )
}
