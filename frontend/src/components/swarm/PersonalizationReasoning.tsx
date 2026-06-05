import { Lightbulb, Sparkles } from 'lucide-react'
import type { Explanation } from '@/types/swarmDemo'
import { DIMENSION_COLORS } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface PersonalizationReasoningProps {
  explanations: Explanation[]
}

const DIM_ORDER = ['prompt', 'modality', 'pacing', 'scaffolding']

export function PersonalizationReasoning({ explanations }: PersonalizationReasoningProps) {
  const personalization = explanations.filter(
    (e) => DIM_ORDER.includes(e.dimension),
  )

  if (personalization.length === 0) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Sparkles className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Personalization Reasoning</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No personalization decisions yet.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center gap-3 border-b px-4 py-3">
        <Sparkles className="h-5 w-5 text-slate-400" />
        <h2 className="text-base font-semibold text-slate-950">Personalization Reasoning</h2>
      </div>

      <div className="grid gap-3 p-4">
        {personalization.map((exp) => {
          const dimColor = DIMENSION_COLORS[exp.dimension] || 'bg-slate-100 text-slate-700'
          return (
            <div key={exp.dimension} className="rounded-md border bg-white">
              <div className={cn('rounded-t-md border-b px-3 py-2 text-xs font-semibold', dimColor)}>
                {exp.dimension.charAt(0).toUpperCase() + exp.dimension.slice(1)}
              </div>

              <div className="grid gap-2 p-3">
                {exp.reasons.map((reason, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-sm">
                    <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                    <div>
                      <p className="font-medium text-slate-900">{reason.factor.replace(/_/g, ' ')}</p>
                      <p className="mt-0.5 text-xs text-slate-600">{reason.evidence}</p>
                    </div>
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
