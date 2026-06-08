import type { ConsensusPoint } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface ConsensusTimelineProps {
  timeline: ConsensusPoint[]
}

const decisionStyles: Record<string, string> = {
  approve: 'bg-emerald-600',
  reject: 'bg-red-600',
  abstain: 'bg-amber-500',
}

export function ConsensusTimeline({ timeline }: ConsensusTimelineProps) {
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Consensus Timeline</h2>
      </div>
      <div className="space-y-4 p-4">
        {timeline.length === 0 ? (
          <div className="rounded-md border border-dashed p-6 text-sm text-slate-500">
            El consenso aparecera cuando entren los votos.
          </div>
        ) : (
          timeline.map((point) => (
            <div key={`${point.step}-${point.agent}`} className="grid gap-2">
              <div className="flex items-center justify-between gap-3 text-sm">
                <span className="font-medium text-slate-900">{point.step}. {point.agent}</span>
                <span className="text-slate-600">{point.decision} · {(point.confidence * 100).toFixed(0)}%</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={cn('h-full rounded-full transition-all', decisionStyles[point.decision])}
                  style={{ width: `${Math.max(6, point.confidence * 100)}%` }}
                />
              </div>
              <div className="grid grid-cols-3 gap-2 text-xs text-slate-600">
                <span>Aprove: {point.approve}</span>
                <span>Reject: {point.reject}</span>
                <span>Abstain: {point.abstain}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </section>
  )
}

