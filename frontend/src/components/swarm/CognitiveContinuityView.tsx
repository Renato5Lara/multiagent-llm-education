import { Layers, RefreshCw, ShieldCheck } from 'lucide-react'
import type { AdaptationMetrics, StudentProfile } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface CognitiveContinuityViewProps {
  profile: StudentProfile | null
  metrics: AdaptationMetrics | null
}

const continuityItems = [
  { key: 'learning_style', label: 'Learning Style Continuity' },
  { key: 'preferred_analogies', label: 'Analogy Domain Continuity' },
  { key: 'cognitive_load_trend', label: 'Cognitive Load Tracking' },
  { key: 'engagement_pattern', label: 'Engagement Continuity' },
  { key: 'pacing', label: 'Pacing Consistency' },
  { key: 'bloom_level_reached', label: 'Bloom Progression' },
]

export function CognitiveContinuityView({ profile, metrics }: CognitiveContinuityViewProps) {
  if (!profile && !metrics) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Layers className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Cognitive Continuity</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No continuity data yet. Run multi-week orchestration to see continuity.</p>
      </section>
    )
  }

  const filled = profile ? continuityItems.filter((item) => profile[item.key as keyof typeof profile] != null).length : 0
  const total = continuityItems.length

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Layers className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Cognitive Continuity</h2>
        </div>
        {metrics && (
          <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
            <ShieldCheck className="h-4 w-4" />
            {Math.round(metrics.continuity_score * 100)}% continuity
          </span>
        )}
      </div>

      <div className="grid gap-4 p-4">
        {profile && (
          <div className="grid gap-1.5 text-sm">
            {continuityItems.map((item) => {
              const val = profile[item.key as keyof typeof profile]
              const present = val != null && val !== '' && !(Array.isArray(val) && val.length === 0)
              return (
                <div key={item.key} className="flex items-center justify-between rounded-md bg-slate-50 px-3 py-2">
                  <span className="flex items-center gap-2">
                    <span className={cn('h-2 w-2 rounded-full', present ? 'bg-emerald-500' : 'bg-slate-300')} />
                    <span className="text-slate-600">{item.label}</span>
                  </span>
                  <span className={cn('text-xs font-medium', present ? 'text-emerald-700' : 'text-slate-400')}>
                    {present ? String(val) : '—'}
                  </span>
                </div>
              )
            })}
          </div>
        )}

        <div className="rounded-md border bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
            <RefreshCw className="h-4 w-4" />
            <span>Continuity Coverage</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-emerald-500 transition-all"
              style={{ width: `${(filled / total) * 100}%` }}
            />
          </div>
          <p className="mt-1 text-xs text-slate-500">{filled} of {total} continuity dimensions tracked</p>
        </div>

        {metrics && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs text-slate-500">Longitudinal Coherence</p>
              <p className="text-lg font-bold text-slate-900">{Math.round(metrics.longitudinal_coherence * 100)}%</p>
            </div>
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs text-slate-500">Memory Reuse</p>
              <p className="text-lg font-bold text-slate-900">{Math.round(metrics.memory_reuse_score * 100)}%</p>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
