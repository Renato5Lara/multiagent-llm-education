import { BrainCircuit } from 'lucide-react'
import type { BloomProgressionItem, DemoEvent, RetrievalCompletePayload } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface BloomProgressionViewProps {
  events: DemoEvent[]
}

export function BloomProgressionView({ events }: BloomProgressionViewProps) {
  const complete = [...events].reverse().find((event) => event.type === 'retrieval:complete')
  const payload = complete?.payload as RetrievalCompletePayload | undefined
  const progression: BloomProgressionItem[] = payload?.bloom_progression ?? []

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Bloom Progression</h2>
        <span className="text-xs font-medium text-slate-500">{payload ? Math.round(payload.bloom_alignment_score * 100) : 0}% aligned</span>
      </div>
      <div className="p-4">
        {progression.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">Esperando mapa Bloom.</div>
        ) : (
          <div className="grid gap-3">
            {progression.map((item) => (
              <div key={item.level} className="grid grid-cols-[36px_1fr] gap-3">
                <span
                  className={cn(
                    'flex h-9 w-9 items-center justify-center rounded-md text-sm font-bold',
                    item.status === 'target' && 'bg-emerald-600 text-white',
                    item.status === 'grounded' && 'bg-blue-100 text-blue-800',
                    item.status === 'extension' && 'bg-purple-100 text-purple-800',
                  )}
                >
                  {item.level}
                </span>
                <div className="rounded-md border bg-slate-50 p-3">
                  <div className="flex items-center gap-2">
                    <BrainCircuit className="h-4 w-4 text-slate-500" />
                    <p className="text-sm font-semibold text-slate-950">{item.label}</p>
                  </div>
                  <p className="mt-1 text-xs leading-relaxed text-slate-700">{item.activity}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
