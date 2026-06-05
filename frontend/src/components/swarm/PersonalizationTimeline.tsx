import { History, Route } from 'lucide-react'
import type { PromptAdaptationInfo } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface PersonalizationTimelineProps {
  currentAdaptation: PromptAdaptationInfo | null
  previousAdaptations?: PromptAdaptationInfo[]
}

export function PersonalizationTimeline({ currentAdaptation, previousAdaptations = [] }: PersonalizationTimelineProps) {
  const all = currentAdaptation ? [...previousAdaptations, currentAdaptation] : previousAdaptations

  if (all.length === 0) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Route className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Personalization Timeline</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No personalization history yet.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <Route className="h-5 w-5 text-slate-400" />
        <h2 className="text-base font-semibold text-slate-950">Personalization Timeline</h2>
      </div>

      <div className="grid gap-3 p-4">
        {all.map((ad, i) => {
          const isLatest = i === all.length - 1
          const phaseLabels = ad.phase_labels ?? []

          return (
            <div key={i} className={cn('rounded-md border bg-white p-3', isLatest && 'ring-2 ring-emerald-200')}>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <History className="h-3.5 w-3.5" />
                <span>{isLatest ? 'Current (latest)' : `Step ${i + 1}`}</span>
                {ad.analogy_domain && (
                  <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 font-medium text-slate-600">
                    {ad.analogy_domain}
                  </span>
                )}
              </div>

              <div className="mt-2 grid gap-1.5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Learning Style</span>
                  <span className="font-medium text-slate-900">{ad.learning_style || '—'}</span>
                </div>
                {ad.tone && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-500">Tone</span>
                    <span className="font-medium text-slate-900 capitalize">{ad.tone}</span>
                  </div>
                )}
                {phaseLabels.length > 0 && (
                  <div className="pt-1">
                    <p className="mb-1 text-xs text-slate-500">Phase Structure</p>
                    <div className="flex flex-wrap gap-1">
                      {phaseLabels.map((p) => (
                        <span key={p} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-700">
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
