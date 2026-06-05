import { Database, GitBranch, ShieldCheck } from 'lucide-react'
import type { ConsistencyPayload, DemoEvent } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface NarrativeConsistencyPanelProps {
  events: DemoEvent[]
}

const narrativeSteps = [
  'docente define objetivo',
  'swarm investiga',
  'retrieval recupera conocimiento',
  'agentes deliberan',
  'consensus decide',
  'prompts multimodales se generan',
  'consistency valida continuidad',
  'shared memory mantiene coherencia',
]

export function NarrativeConsistencyPanel({ events }: NarrativeConsistencyPanelProps) {
  const consistencyEvent = [...events].reverse().find((event) => event.type === 'consistency:validated')
  const consistency = consistencyEvent?.payload as ConsistencyPayload | undefined
  const has = (type: string) => events.some((event) => event.type === type)
  const completed = [
    has('session.started'),
    has('retrieval:start'),
    has('retrieval:source'),
    has('vote.cast'),
    has('session.completed') || has('consensus.updated'),
    has('prompt:generated'),
    has('consistency:validated'),
    events.some((event) => event.type === 'memory.published'),
  ]

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Narrative Consistency</h2>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4" />
          {consistency ? Math.round(consistency.continuity_score * 100) : 0}%
        </span>
      </div>
      <div className="grid gap-4 p-4">
        <div className="grid gap-2">
          {narrativeSteps.map((step, index) => (
            <div key={step} className="grid grid-cols-[28px_1fr] items-center gap-3">
              <span
                className={cn(
                  'flex h-7 w-7 items-center justify-center rounded-md text-xs font-bold',
                  completed[index] ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-500',
                )}
              >
                {index + 1}
              </span>
              <p className={cn('text-sm', completed[index] ? 'font-medium text-slate-950' : 'text-slate-500')}>{step}</p>
            </div>
          ))}
        </div>

        <div className="grid gap-2 sm:grid-cols-3">
          <Score icon={GitBranch} label="Continuity" value={consistency?.continuity_score ?? 0} />
          <Score icon={Database} label="Memory" value={consistency?.memory_coherence ?? 0} />
          <Score icon={ShieldCheck} label="Narrative" value={consistency?.narrative_consistency ?? 0} />
        </div>

        {consistency?.issues?.length ? (
          <div className="rounded-md border bg-slate-50 p-3 text-xs leading-relaxed text-slate-700">
            {consistency.issues[0].detail}
          </div>
        ) : null}
      </div>
    </section>
  )
}

function Score({ icon: Icon, label, value }: { icon: typeof GitBranch; label: string; value: number }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className="mt-2 text-lg font-bold text-slate-950">{Math.round(value * 100)}%</p>
    </div>
  )
}
