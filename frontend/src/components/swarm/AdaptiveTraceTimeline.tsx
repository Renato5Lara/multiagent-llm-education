import { GitBranch } from 'lucide-react'
import type { DecisionGraph, DecisionGraphNode } from '@/types/swarmDemo'

interface AdaptiveTraceTimelineProps {
  graph: DecisionGraph | null
}

export function AdaptiveTraceTimeline({ graph }: AdaptiveTraceTimelineProps) {
  if (!graph || graph.nodes.length === 0) {
    return (
      <section className="rounded-lg border bg-white">
        <div className="flex items-center gap-3 border-b px-4 py-3">
          <GitBranch className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Trace Timeline</h2>
        </div>
        <p className="p-4 text-sm text-slate-500">No decision graph available yet.</p>
      </section>
    )
  }

  const signals = graph.nodes.filter((n) => n.type === 'signal')
  const decisions = graph.nodes.filter((n) => n.type === 'decision')

  return (
    <section className="rounded-lg border bg-white">
      <div className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <div className="flex items-center gap-3">
          <GitBranch className="h-5 w-5 text-slate-400" />
          <h2 className="text-base font-semibold text-slate-950">Adaptation Trace Timeline</h2>
        </div>
        <span className="text-xs text-slate-500">{graph.nodes.length} nodes, {graph.edges.length} edges</span>
      </div>

      <div className="grid gap-4 p-4">
        {signals.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Signals</h3>
            <div className="grid gap-1.5">
              {signals.map((node) => {
                const relevantEdges = graph.edges.filter((e) => e.from === node.id)
                return (
                  <SignalNode key={node.id} node={node} edges={relevantEdges} />
                )
              })}
            </div>
          </div>
        )}

        {decisions.length > 0 && (
          <div>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Decisions</h3>
            <div className="grid gap-1.5">
              {decisions.map((node) => {
                const incomingEdges = graph.edges.filter((e) => e.to === node.id)
                return (
                  <DecisionNode key={node.id} node={node} edges={incomingEdges} />
                )
              })}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function SignalNode({ node, edges }: { node: DecisionGraphNode; edges: { to: string; contribution: number }[] }) {
  return (
    <div className="flex items-center justify-between rounded-md bg-amber-50 px-3 py-2 text-sm">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-amber-500" />
        <span className="font-medium text-slate-900">{node.label}</span>
      </div>
      {edges.length > 0 && (
        <span className="text-xs text-slate-500">
          → {edges.length} decision{edges.length > 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}

function DecisionNode({ node, edges }: { node: DecisionGraphNode; edges: { from: string; contribution: number }[] }) {
  return (
    <div className="rounded-md border bg-white px-3 py-2 text-sm">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500" />
          <span className="font-medium text-slate-900">{node.label}</span>
        </div>
        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-700">
          {node.dimension}
        </span>
      </div>
      {edges.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {edges.map((edge, i) => (
            <span key={i} className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-600">
              {Math.round(edge.contribution * 100)}% influence
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
