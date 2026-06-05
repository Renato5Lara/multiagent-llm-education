import { Minus, TrendingDown, TrendingUp } from 'lucide-react'
import type { ReplayTimeline, LongitudinalMetrics } from '@/types/replay'

interface StudentEvolutionViewProps {
  timeline: ReplayTimeline
  metrics: LongitudinalMetrics
}

export function StudentEvolutionView({ timeline, metrics }: StudentEvolutionViewProps) {
  return (
    <section className="rounded-lg border bg-white">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Longitudinal Evolution</h2>
      </div>
      <div className="grid gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricChart
          label="Bloom Levels"
          data={timeline.bloom_levels}
          icon={metrics.bloom_recovery > 0 ? TrendingUp : Minus}
          color="text-violet-600"
          bgColor="bg-violet-50"
          suffix=""
        />
        <MetricChart
          label="Confidence Scores"
          data={timeline.confidence_scores.map((v) => Math.round(v * 100))}
          icon={metrics.confidence_trend === 'up' ? TrendingUp : Minus}
          color="text-blue-600"
          bgColor="bg-blue-50"
          suffix="%"
        />
        <MetricChart
          label="Scaffolding Steps"
          data={timeline.scaffolding_counts}
          icon={Minus}
          color="text-cyan-600"
          bgColor="bg-cyan-50"
          suffix=""
        />
        <MetricChart
          label="Misconceptions"
          data={timeline.misconception_counts}
          icon={metrics.misconception_reduction > 0 ? TrendingDown : Minus}
          color="text-amber-600"
          bgColor="bg-amber-50"
          suffix=""
        />
        <MetricChart
          label="Memory Records"
          data={timeline.memory_records}
          icon={TrendingUp}
          color="text-emerald-600"
          bgColor="bg-emerald-50"
          suffix=""
        />
        <MetricChart
          label="Cognitive Load"
          data={timeline.cognitive_load_signals.map((v) => Math.round(v * 100))}
          icon={metrics.cognitive_load_trend === 'decreasing' ? TrendingDown : metrics.cognitive_load_trend === 'increasing' ? TrendingUp : Minus}
          color="text-rose-600"
          bgColor="bg-rose-50"
          suffix="%"
        />
      </div>
      <div className="grid gap-3 border-t p-4 sm:grid-cols-3">
        <div className="rounded-md bg-slate-50 p-3 text-center">
          <p className="text-xs font-medium text-slate-500">Bloom Recovery</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">+{metrics.bloom_recovery}</p>
        </div>
        <div className="rounded-md bg-slate-50 p-3 text-center">
          <p className="text-xs font-medium text-slate-500">Misconception Reduction</p>
          <p className="mt-1 text-2xl font-bold text-green-600">-{metrics.misconception_reduction}</p>
        </div>
        <div className="rounded-md bg-slate-50 p-3 text-center">
          <p className="text-xs font-medium text-slate-500">Adaptation Stability</p>
          <p className="mt-1 text-2xl font-bold text-slate-900">{Math.round(metrics.adaptation_stability * 100)}%</p>
        </div>
      </div>
    </section>
  )
}

function MetricChart({
  label,
  data,
  icon: Icon,
  color,
  bgColor,
  suffix,
}: {
  label: string
  data: number[]
  icon: React.ElementType
  color: string
  bgColor: string
  suffix: string
}) {
  if (data.length === 0) {
    return (
      <div className={`rounded-md ${bgColor} p-3`}>
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <p className="mt-1 text-sm text-slate-400">No data</p>
      </div>
    )
  }

  const max = Math.max(...data, 1)
  const min = Math.min(...data, 0)
  const range = max - min || 1

  return (
    <div className={`rounded-md ${bgColor} p-3`}>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        <Icon className={`h-4 w-4 ${color}`} />
      </div>
      <div className="mb-2 flex items-baseline gap-1">
        <span className={`text-2xl font-bold ${color}`}>{data[data.length - 1]}{suffix}</span>
        {data.length > 1 && (
          <span className="text-xs text-slate-400">
            {data[0]}{suffix} → {data[data.length - 1]}{suffix}
          </span>
        )}
      </div>
      <div className="flex items-end gap-0.5" style={{ height: 48 }}>
        {data.map((value, i) => (
          <div
            key={i}
            className="flex-1 rounded-t transition-all"
            style={{
              height: `${((value - min) / range) * 100}%`,
              minHeight: 4,
              backgroundColor: i === data.length - 1 ? 'currentColor' : undefined,
              opacity: i === data.length - 1 ? 1 : 0.4,
            }}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-slate-400">
        <span>W1</span>
        <span>W{data.length}</span>
      </div>
    </div>
  )
}
