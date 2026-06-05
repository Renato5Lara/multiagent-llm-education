import { Brain, Lightbulb, Network, ShieldCheck } from 'lucide-react'
import type { Explanation, DecisionGraph } from '@/types/replay'
import { DIMENSION_LABELS, DIMENSION_COLORS } from '@/types/swarmDemo'
import { cn } from '@/lib/utils'

interface ReplayReasoningPanelProps {
  explanations: Explanation[]
  decisionGraph: DecisionGraph
}

export function ReplayReasoningPanel({ explanations, decisionGraph }: ReplayReasoningPanelProps) {
  if (explanations.length === 0) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Reasoning</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No reasoning data for this week.</p>
      </section>
    )
  }

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <Brain className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Reasoning</h2>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <ShieldCheck className="h-4 w-4" />
          {explanations.length} dimensions · {decisionGraph.nodes.length} nodes
        </span>
      </div>

      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <div className="space-y-3">
          {explanations.map((exp) => {
            const avgConf = exp.reasons.reduce((s, r) => s + r.contribution, 0) / Math.max(exp.reasons.length, 1)
            return (
              <div key={exp.dimension} className="rounded-md border">
                <div className={cn('flex items-center justify-between border-b px-3 py-2', DIMENSION_COLORS[exp.dimension] || 'bg-slate-50')}>
                  <span className="text-xs font-semibold">{DIMENSION_LABELS[exp.dimension] || exp.dimension}</span>
                  <span className="text-xs text-slate-500">{Math.round(avgConf * 100)}% confident</span>
                </div>
                <div className="space-y-2 p-3">
                  {exp.reasons.map((r, i) => (
                    <div key={i} className="rounded-md bg-slate-50 p-2.5">
                      <div className="flex items-center gap-1.5">
                        <Lightbulb className="h-3.5 w-3.5 text-amber-500" />
                        <span className="text-xs font-semibold text-slate-700">{r.factor.replace(/_/g, ' ')}</span>
                        <span className="ml-auto text-xs text-slate-400">{(r.contribution * 100).toFixed(0)}%</span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{r.evidence}</p>
                    </div>
                  ))}
                  <div className="text-xs text-slate-400">
                    {formatValue(exp.previous_value)} → {formatValue(exp.new_value)}
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        <div className="rounded-md border bg-slate-50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Network className="h-4 w-4 text-slate-500" />
            <h3 className="text-sm font-semibold text-slate-700">Decision Graph</h3>
          </div>
          <div className="space-y-3">
            {decisionGraph.nodes.map((node) => (
              <div key={node.id} className="rounded-md border bg-white p-2.5 text-xs">
                <div className="flex items-center gap-2">
                  <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${node.type === 'decision' ? 'bg-primary/10 text-primary' : 'bg-amber-50 text-amber-700'}`}>
                    {node.type}
                  </span>
                  <span className="font-medium text-slate-800">{node.label}</span>
                </div>
                {node.factor && <p className="mt-1 text-slate-400">{node.factor}</p>}
              </div>
            ))}
            {decisionGraph.edges.length > 0 && (
              <div className="border-t pt-2">
                <p className="mb-1 text-[10px] font-medium uppercase text-slate-400">Edges</p>
                {decisionGraph.edges.map((edge, i: number) => (
                  <p key={i} className="text-xs text-slate-500">
                    {edge.from} → {edge.to} ({(edge.contribution * 100).toFixed(0)}%)
                  </p>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}

function formatValue(value: unknown): string {
  if (value == null) return '—'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return JSON.stringify(value)
}
