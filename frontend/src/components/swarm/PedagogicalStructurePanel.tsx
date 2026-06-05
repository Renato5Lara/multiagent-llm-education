import { Route } from 'lucide-react'
import type { DemoEvent, PedagogicalPhase, RetrievalCompletePayload } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface PedagogicalStructurePanelProps {
  events: DemoEvent[]
}

export function PedagogicalStructurePanel({ events }: PedagogicalStructurePanelProps) {
  const complete = [...events].reverse().find((event) => event.type === 'retrieval:complete')
  const payload = complete?.payload as RetrievalCompletePayload | undefined
  const phases: PedagogicalPhase[] = payload?.pedagogical_structure ?? []

  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Pedagogical Structure</h2>
      </div>
      <div className="space-y-3 p-4">
        {phases.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Esperando estructura pedagogica.</div>
        ) : (
          phases.map((phase, index) => (
            <div key={phase.phase} className="grid grid-cols-[32px_1fr] gap-3">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-100 text-slate-700">
                <Route className="h-4 w-4" />
              </span>
              <div className="rounded-md border bg-slate-50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-slate-950">{index + 1}. {phase.phase}</p>
                  <span
                    className={cn(
                      'rounded-md px-2 py-1 text-xs font-medium',
                      phase.load === 'low' && 'bg-emerald-100 text-emerald-800',
                      phase.load === 'medium' && 'bg-amber-100 text-amber-800',
                      phase.load === 'high' && 'bg-red-100 text-red-800',
                    )}
                  >
                    {phase.load}
                  </span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-slate-700">{phase.goal}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}
