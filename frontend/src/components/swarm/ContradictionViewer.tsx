import { AlertTriangle, CheckCircle2, Lightbulb } from 'lucide-react'
import type { ContradictionPayload, DemoEvent, MisconceptionPayload } from '@/types/swarmDemo'

interface ContradictionViewerProps {
  events: DemoEvent[]
}

export function ContradictionViewer({ events }: ContradictionViewerProps) {
  const contradictions = events
    .filter((event) => event.type === 'contradiction:detected')
    .map((event) => event.payload as unknown as ContradictionPayload)
  const misconceptions = events
    .filter((event) => event.type === 'misconception:detected')
    .map((event) => event.payload as unknown as MisconceptionPayload)

  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Contradictions & Misconceptions</h2>
      </div>
      <div className="space-y-3 p-4">
        {contradictions.length === 0 && misconceptions.length === 0 ? (
          <div className="rounded-md border border-dashed p-5 text-sm text-slate-500">
            El panel mostrara conflictos entre fuentes y misconceptions detectadas.
          </div>
        ) : null}
        {contradictions.map((item, index) => (
          <article key={`${item.claim_a}-${index}`} className="rounded-md border border-amber-200 bg-amber-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm font-semibold text-amber-950">
                <AlertTriangle className="h-4 w-4" /> Contradiction
              </span>
              <span className="text-xs text-amber-800">{Math.round(item.confidence * 100)}%</span>
            </div>
            <div className="mt-3 grid gap-2 text-xs leading-relaxed text-amber-950">
              <p><strong>A:</strong> {item.claim_a}</p>
              <p><strong>B:</strong> {item.claim_b}</p>
              <p className="rounded-md bg-white/70 p-2"><strong>Resolution:</strong> {item.resolution}</p>
            </div>
          </article>
        ))}
        {misconceptions.map((item, index) => (
          <article key={`${item.misconception}-${index}`} className="rounded-md border bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <span className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                <Lightbulb className="h-4 w-4 text-fuchsia-700" /> Misconception
              </span>
              <span className="text-xs text-slate-600">{Math.round(item.confidence * 100)}%</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-slate-700">{item.misconception}</p>
            <p className="mt-2 flex gap-2 rounded-md bg-white p-2 text-xs text-slate-700">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
              {item.remediation}
            </p>
          </article>
        ))}
      </div>
    </section>
  )
}
