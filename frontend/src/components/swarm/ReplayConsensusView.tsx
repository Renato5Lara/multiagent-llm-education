import { ShieldCheck } from 'lucide-react'
import type { AdaptationReplay } from '@/types/replay'

interface ReplayConsensusViewProps {
  consensus: AdaptationReplay['consensus']
  bloom: AdaptationReplay['bloom']
}

export function ReplayConsensusView({ consensus, bloom }: ReplayConsensusViewProps) {
  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center gap-2 border-b px-4 py-3">
        <ShieldCheck className="h-4 w-4 text-slate-500" />
        <h3 className="text-sm font-semibold text-slate-900">Consensus Replay</h3>
      </div>
      <div className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label="Decision" value={consensus.decision} />
        <Metric label="Confidence" value={`${Math.round(consensus.confidence * 100)}%`} />
        <Metric label="Memory Influence" value={`${Math.round(consensus.memory_influence * 100)}%`} />
        <Metric label="Bloom" value={`${bloom.previous ?? '?'} -> ${bloom.current}`} />
      </div>
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-bold text-slate-900">{value}</p>
    </div>
  )
}
