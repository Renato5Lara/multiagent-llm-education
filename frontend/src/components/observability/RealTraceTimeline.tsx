import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import { getStepMeta } from '@/constants/agentPipeline'
import { formatElapsedMs } from '@/types/trace'
import type { AgentDecisionTrace, TraceChainResponse } from '@/types/trace'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTimestamp(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso.slice(11, 19) // fallback: slice HH:MM:SS
  }
}

// ── Single agent row ──────────────────────────────────────────────────────────

function TraceRow({ trace, techMode }: { trace: AgentDecisionTrace; techMode: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const meta = getStepMeta(trace.agent_name)
  const hasSteps = trace.reasoning_steps?.length > 0

  return (
    <div className="group">
      <div className="flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-muted/40 transition-colors">

        {/* Icon + timeline line */}
        <div className="flex flex-col items-center shrink-0">
          <div className="w-8 h-8 rounded-full bg-primary/8 dark:bg-primary/10 flex items-center justify-center text-base select-none">
            {meta.icon}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-1">
          {/* Header row */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-mono text-muted-foreground tabular-nums">
              {formatTimestamp(trace.started_at)}
            </span>
            <span className="text-muted-foreground/40 text-xs">·</span>
            <span className="text-xs font-medium">
              {techMode ? (
                <span className="font-mono text-primary/80">{trace.agent_name}</span>
              ) : (
                meta.studentLabel
              )}
            </span>
            <span className="ml-auto text-xs text-muted-foreground/60 tabular-nums shrink-0">
              {formatElapsedMs(trace.elapsed_ms)}
            </span>
          </div>

          {/* Decision summary */}
          {trace.decision_summary && (
            <p className="text-sm text-foreground/70 leading-relaxed">
              {trace.decision_summary}
            </p>
          )}

          {/* Expand button for reasoning steps */}
          {hasSteps && (
            <button
              type="button"
              onClick={() => setExpanded(v => !v)}
              className="flex items-center gap-1 text-xs text-primary/70 hover:text-primary transition-colors mt-0.5"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? 'Ocultar razonamiento' : `Ver razonamiento (${trace.reasoning_steps.length} pasos)`}
            </button>
          )}

          {/* Reasoning steps */}
          {expanded && hasSteps && (
            <div className="mt-2 ml-1 space-y-1.5 animate-in fade-in duration-200">
              {trace.reasoning_steps.map((step, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <span className="shrink-0 font-mono text-primary/40 mt-0.5">{String(i + 1).padStart(2, '0')}</span>
                  <span className="leading-relaxed">{step.description}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Debate block ──────────────────────────────────────────────────────────────

function DebateBlock({ data }: { data: TraceChainResponse }) {
  const consensus = data.chain.find(t =>
    t.agent_name === 'consensus_mediator' || t.agent_type === 'consensus_mediator',
  )
  if (!consensus) return null

  const debateEv = consensus.evidence.find(e => e.key === 'debate_context')
  if (!debateEv) return null

  const deb = debateEv.value_summary as Record<string, unknown>
  const hasConflict = Boolean(deb['conflict'])
  if (!hasConflict) return null

  return (
    <div className="mx-3 my-1 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20 px-4 py-3 space-y-1">
      <p className="text-xs font-semibold text-amber-700 dark:text-amber-400">
        ⚡ Debate entre agentes detectado
      </p>
      {!!deb['adaptive_difficulty'] && !!deb['evaluation_override'] && (
        <p className="text-xs text-amber-700/70 dark:text-amber-400/70 leading-relaxed">
          <span className="font-medium">AdaptiveLearning</span> propuso{' '}
          <span className="italic">"{String(deb['adaptive_difficulty'])}"</span> ·{' '}
          <span className="font-medium">EvaluationAgent</span> ajustó a{' '}
          <span className="italic">"{String(deb['evaluation_override'])}"</span>
        </p>
      )}
      {!!deb['recommendation'] && (
        <p className="text-xs text-amber-600/60 dark:text-amber-400/50">
          Recomendación: {String(deb['recommendation'])}
        </p>
      )}
    </div>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

interface Props {
  data: TraceChainResponse
  techMode: boolean
}

/**
 * RealTraceTimeline — shown when the LLM pipeline ran and traces are available.
 *
 * Renders each AgentDecisionTrace in pipeline order.
 * Shows real timestamps, elapsed_ms, decision_summary, and
 * expandable reasoning_steps per agent.
 *
 * Inserts a DebateBlock between EvaluationAgent and ConsensusMediador
 * when inter-agent conflict was detected.
 */
export function RealTraceTimeline({ data, techMode }: Props) {
  const { chain, total_elapsed_ms } = data

  return (
    <div className="space-y-0.5">
      {chain.map((trace) => (
        <div key={trace.trace_id}>
          {/* Inject debate block before ConsensusMediador */}
          {(trace.agent_name === 'consensus_mediator' || trace.agent_type === 'consensus_mediator') && (
            <DebateBlock data={data} />
          )}
          <TraceRow trace={trace} techMode={techMode} />
        </div>
      ))}

      {/* Footer */}
      <div className="px-3 pt-2 flex items-center justify-between text-xs text-muted-foreground/60">
        <span>{chain.length} agentes · trazas reales</span>
        {total_elapsed_ms > 0 && (
          <span className="tabular-nums">{formatElapsedMs(total_elapsed_ms)} total</span>
        )}
      </div>
    </div>
  )
}
