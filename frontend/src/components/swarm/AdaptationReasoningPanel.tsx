import { Brain, Lightbulb, ShieldCheck } from 'lucide-react'
import type { Explanation } from '@/types/swarmDemo'
import { DIMENSION_LABELS, DIMENSION_COLORS } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface AdaptationReasoningPanelProps {
  explanations: Explanation[]
}

export function AdaptationReasoningPanel({ explanations }: AdaptationReasoningPanelProps) {
  if (explanations.length === 0) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Reasoning</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No adaptation explanations yet. Run orchestration to generate reasoning.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Reasoning</h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4" />
          {explanations.length} dimensions explained
        </span>
      </div>

      <div className="grid gap-3 p-4">
        {explanations.map((exp) => {
          const avgConf = exp.reasons.reduce((s, r) => s + r.contribution, 0) / Math.max(exp.reasons.length, 1)

          return (
            <div key={exp.dimension} className="rounded-md border bg-white">
              <div className="flex items-center justify-between border-b bg-slate-50 px-3 py-2">
                <span className={cn('rounded-md px-2 py-0.5 text-xs font-semibold', DIMENSION_COLORS[exp.dimension] || 'bg-slate-100 text-slate-700')}>
                  {DIMENSION_LABELS[exp.dimension] || exp.dimension}
                </span>
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <ShieldCheck className="h-3 w-3" />
                  {Math.round(avgConf * 100)}% confidence
                </span>
              </div>

              <div className="grid gap-2 p-3 text-sm">
                {exp.reasons.map((reason, i) => (
                  <div key={i} className="rounded-md bg-slate-50 p-2.5">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                        <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                        {reason.factor.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-medium text-slate-500">
                        {Math.round(reason.contribution * 100)}% influence
                      </span>
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">{reason.evidence}</p>
                    {reason.value !== null && reason.value !== undefined && (
                      <p className="mt-1 text-xs font-medium text-slate-500">
                        Value: {String(reason.value).slice(0, 80)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </section>
  )
}
