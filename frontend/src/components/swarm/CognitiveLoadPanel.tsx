import { AlertTriangle, Brain, ShieldCheck, TrendingUp } from 'lucide-react'
import type { Explanation } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface CognitiveLoadPanelProps {
  explanation: Explanation | null
}

const severityColor = (severity: string) => {
  if (severity.includes('high')) return 'text-red-600 bg-red-50 border-red-200'
  if (severity.includes('moderate')) return 'text-amber-600 bg-amber-50 border-amber-200'
  return 'text-emerald-600 bg-emerald-50 border-emerald-200'
}

const severityIcon = (severity: string) => {
  if (severity.includes('high')) return <AlertTriangle className="h-5 w-5 text-red-500" />
  if (severity.includes('moderate')) return <TrendingUp className="h-5 w-5 text-amber-500" />
  return <Brain className="h-5 w-5 text-emerald-500" />
}

export function CognitiveLoadPanel({ explanation }: CognitiveLoadPanelProps) {
  if (!explanation) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Cognitive Load Analysis</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No cognitive load data yet.</p>
      </section>
    )
  }

  const newVal = String(explanation.new_value ?? 'unknown')
  const severity = newVal.includes('high') ? 'high' : newVal.includes('moderate') ? 'moderate' : 'low'
  const isOverload = newVal.includes('overload')

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Cognitive Load Analysis</h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4" />
          {Math.round(explanation.confidence * 100)}% confidence
        </span>
      </div>

      <div className="grid gap-4 p-4">
        <div className={cn('flex items-center gap-3 rounded-md border p-3', severityColor(severity))}>
          {severityIcon(severity)}
          <div>
            <p className="text-sm font-semibold">
              {isOverload ? `Overload Detected (${severity})` : 'Within Normal Range'}
            </p>
            <p className="text-xs opacity-80">
              {isOverload
                ? 'Cognitive load signals indicate the student may be overwhelmed. Adapting to reduce difficulty.'
                : 'Cognitive load signals are within manageable range. No adaptation needed.'}
            </p>
          </div>
        </div>

        <div className="grid gap-2">
          {explanation.reasons.map((reason, i) => (
            <div key={i} className="rounded-md bg-slate-50 p-3 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-900">{reason.factor.replace(/_/g, ' ')}</span>
                <span className="text-xs font-medium text-slate-500">
                  {Math.round(reason.contribution * 100)}% influence
                </span>
              </div>
              <p className="mt-1 text-xs text-slate-600">{reason.evidence}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
