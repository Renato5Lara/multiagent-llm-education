import { Brain, Database, GitBranch, ShieldCheck, TrendingUp } from 'lucide-react'
import type { AdaptationMetrics, StudentProfile } from '@/types/swarmDemo'

interface MemoryInfluencePanelProps {
  profile: StudentProfile | null
  metrics: AdaptationMetrics | null
}

const styleLabels: Record<string, string> = {
  visual: 'Visual',
  auditory: 'Auditivo',
  reading: 'Lectura',
  kinesthetic: 'Kinestésico',
}

export function MemoryInfluencePanel({ profile, metrics }: MemoryInfluencePanelProps) {
  const analogies = profile?.preferred_analogies ?? []
  const ls = profile?.learning_style ?? ''

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 className="text-base font-semibold text-slate-950">Memory Influence</h2>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <Brain className="h-4 w-4" />
          {metrics ? Math.round(metrics.pedagogical_adaptation_quality * 100) : 0}% influence
        </span>
      </div>

      <div className="grid gap-4 p-4">
        {profile && (
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs font-medium text-slate-500">Learning Style</p>
              <p className="mt-0.5 font-semibold text-slate-900">{styleLabels[ls] || ls || '—'}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs font-medium text-slate-500">Analogy Domain</p>
              <p className="mt-0.5 font-semibold text-slate-900">{analogies[0] || '—'}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs font-medium text-slate-500">Modality</p>
              <p className="mt-0.5 font-semibold text-slate-900">{profile.preferred_modality || '—'}</p>
            </div>
            <div className="rounded-md bg-slate-50 p-2.5">
              <p className="text-xs font-medium text-slate-500">Pacing</p>
              <p className="mt-0.5 font-semibold text-slate-900">{profile.pacing || '—'}</p>
            </div>
          </div>
        )}

        {metrics && (
          <div className="grid gap-2 sm:grid-cols-3">
            <Score icon={GitBranch} label="Consistency" value={metrics.adaptation_consistency} />
            <Score icon={TrendingUp} label="Personalization" value={metrics.personalization_strength} />
            <Score icon={ShieldCheck} label="Continuity" value={metrics.continuity_score} />
            <Score icon={Database} label="Memory Reuse" value={metrics.memory_reuse_score} />
            <Score icon={Brain} label="Pedagogical Quality" value={metrics.pedagogical_adaptation_quality} />
            <Score icon={GitBranch} label="Longitudinal" value={metrics.longitudinal_coherence} />
          </div>
        )}

        {metrics && (
          <div className="rounded-md border bg-slate-50 p-3 text-xs text-slate-600">
            <p><span className="font-medium">Records used:</span> {metrics.memory_records_used}</p>
            <p><span className="font-medium">Adaptations:</span> {metrics.adaptation_count}</p>
            <p><span className="font-medium">Weeks tracked:</span> {metrics.total_weeks}</p>
          </div>
        )}
      </div>
    </section>
  )
}

function Score({ icon: Icon, label, value }: { icon: typeof Brain; label: string; value: number }) {
  return (
    <div className="rounded-md border bg-slate-50 p-3">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-600">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <p className="mt-2 text-lg font-bold text-slate-950">{Math.round(value * 100)}%</p>
    </div>
  )
}
