import { BarChart3, CheckCircle, Clock, Cpu, TrendingDown, TrendingUp } from 'lucide-react'
import type { AdaptationMetrics, AdaptationRationale } from '@/types/swarmDemo'

interface AdaptationEvolutionProps {
  rationale: AdaptationRationale | null
  metrics: AdaptationMetrics | null
}

const trendIcon = (trend: string) => {
  if (trend === 'increasing') return <TrendingUp className="h-4 w-4 text-amber-500" />
  if (trend === 'decreasing') return <TrendingDown className="h-4 w-4 text-emerald-500" />
  return <Clock className="h-4 w-4 text-slate-400" />
}

export function AdaptationEvolution({ rationale, metrics }: AdaptationEvolutionProps) {
  if (!rationale && !metrics) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <BarChart3 className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Evolution</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No adaptation data yet. Run orchestration to see evolution.</p>
      </section>
    )
  }

  const bloomReason = rationale?.bloom_adjusted_reason ?? 'normal'

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <BarChart3 className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Evolution</h2>
        </div>
        {metrics && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <Cpu className="h-4 w-4" />
            {Math.round(metrics.personalization_strength * 100)}% personalized
          </span>
        )}
      </div>

      <div className="grid gap-3 p-4">
        {rationale && (
          <>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <SignalRow label="Cognitive Load" value={rationale.cognitive_load_trend} icon={trendIcon(rationale.cognitive_load_trend)} />
              <SignalRow label="Pacing" value={rationale.pacing} />
              <SignalRow label="Style" value={rationale.learning_style} />
              <SignalRow label="Analogy Domain" value={rationale.analogy_domain ?? '—'} />
            </div>

            <div className="rounded-md border bg-slate-50 p-3 text-xs">
              <div className="flex items-center gap-2 font-medium text-slate-700">
                <CheckCircle className="h-4 w-4 text-emerald-500" />
                Adaptation Decision
              </div>
              <p className="mt-1 text-slate-600">{bloomReason === 'normal' ? 'No adjustment needed.' : `Bloom target reduced: ${bloomReason}`}</p>
            </div>
          </>
        )}

        {metrics && (
          <div className="grid gap-2 sm:grid-cols-3">
            <MiniScore label="Consistency" value={metrics.adaptation_consistency} />
            <MiniScore label="Quality" value={metrics.pedagogical_adaptation_quality} />
            <MiniScore label="Coherence" value={metrics.longitudinal_coherence} />
          </div>
        )}
      </div>
    </section>
  )
}

function SignalRow({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-slate-50 px-2.5 py-2">
      {icon}
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-sm font-medium text-slate-900 capitalize">{value.replace(/_/g, ' ')}</p>
      </div>
    </div>
  )
}

function MiniScore({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border bg-white px-2.5 py-2 text-center">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-base font-bold text-slate-900">{Math.round(value * 100)}%</p>
    </div>
  )
}
