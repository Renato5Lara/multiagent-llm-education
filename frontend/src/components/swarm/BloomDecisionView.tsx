import { ArrowDown, ArrowRight, ArrowUp, BarChart3, TrendingDown, TrendingUp } from 'lucide-react'
import type { Explanation } from '@/types/swarmDemo'

interface BloomDecisionViewProps {
  explanation: Explanation | null
}

const bloomLabels = ['', 'Recordar', 'Comprender', 'Aplicar', 'Analizar', 'Evaluar', 'Crear']

export function BloomDecisionView({ explanation }: BloomDecisionViewProps) {
  if (!explanation) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <BarChart3 className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Bloom Decision</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No Bloom adaptation data yet.</p>
      </section>
    )
  }

  const prev = typeof explanation.previous_value === 'number' ? explanation.previous_value : null
  const curr = typeof explanation.new_value === 'number' ? explanation.new_value : null
  const changed = prev !== null && curr !== null && prev !== curr
  const direction = changed && prev !== null && curr !== null ? (curr > prev ? 'up' : 'down') : 'same'

  const ArrowIcon = direction === 'up' ? ArrowUp : direction === 'down' ? ArrowDown : ArrowRight
  const TrendIcon = direction === 'up' ? TrendingUp : direction === 'down' ? TrendingDown : ArrowRight
  const arrowColor = direction === 'up' ? 'text-emerald-600' : direction === 'down' ? 'text-amber-600' : 'text-slate-400'

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Bloom Decision</h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          {Math.round(explanation.confidence * 100)}% confidence
        </span>
      </div>

      <div className="grid gap-4 p-4">
        {prev !== null && curr !== null && (
          <div className="flex items-center justify-center gap-4 rounded-md bg-slate-50 px-4 py-4">
            <div className="text-center">
              <p className="text-xs font-medium text-slate-500">Previous</p>
              <p className="mt-1 text-2xl font-bold text-slate-700">{prev}</p>
              <p className="text-xs text-slate-400">{bloomLabels[prev] || ''}</p>
            </div>
            <div className="flex flex-col items-center">
              <ArrowIcon className={cn('h-6 w-6', arrowColor)} />
              <span className="mt-1 text-xs font-medium text-slate-500">
                {changed ? `-${prev - curr}` : 'unchanged'}
              </span>
            </div>
            <div className="text-center">
              <p className="text-xs font-medium text-slate-500">Current</p>
              <p className={cn('mt-1 text-2xl font-bold', direction === 'up' ? 'text-emerald-600' : direction === 'down' ? 'text-amber-600' : 'text-slate-700')}>
                {curr}
              </p>
              <p className="text-xs text-slate-400">{bloomLabels[curr] || ''}</p>
            </div>
          </div>
        )}

        <div className="grid gap-2">
          {explanation.reasons.map((reason, i) => (
            <div key={i} className="flex items-start gap-3 rounded-md border bg-white p-2.5 text-sm">
              <TrendIcon className={cn('mt-0.5 h-4 w-4 shrink-0', arrowColor)} />
              <div>
                <p className="font-medium text-slate-900">{reason.factor.replace(/_/g, ' ')}</p>
                <p className="mt-0.5 text-xs text-slate-600">{reason.evidence}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ')
}
