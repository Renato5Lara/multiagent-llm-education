import { useState } from 'react'
import { ChevronDown, ChevronUp, Sparkles, FlaskConical } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTrace } from '@/hooks/useTrace'
import { PIPELINE_STEPS, TOTAL_ESTIMATED_MS } from '@/constants/agentPipeline'
import { formatElapsedMs } from '@/types/trace'
import { SyntheticTimeline } from './SyntheticTimeline'
import { RealTraceTimeline } from './RealTraceTimeline'

interface Props {
  sessionId: string | null | undefined
  /** Called when the user opens the full technical TraceExplorer. */
  onOpenTechnical?: () => void
}

/**
 * AgentThoughtStream — Sprint E.
 *
 * Two-layer architecture:
 *   Layer 1 (student, always works): SyntheticTimeline from PIPELINE_STEPS constants
 *   Layer 2 (real, needs LLM keys):  RealTraceTimeline from /api/trace/session/{id}
 *
 * Switch is automatic: when the trace endpoint returns data, RealTraceTimeline is shown.
 * When it returns 404 (template-fallback mode), SyntheticTimeline is shown.
 * Adding OPENAI_API_KEY to the environment upgrades the display with no frontend changes.
 *
 * Tech toggle: shows technical agent names instead of student-friendly labels.
 */
export function AgentThoughtStream({ sessionId, onOpenTechnical }: Props) {
  const [open, setOpen]           = useState(false)
  const [techMode, setTechMode]   = useState(false)

  const { data: traceData, isLoading } = useTrace(sessionId ?? undefined)

  const hasRealTraces = !isLoading && !!traceData && traceData.chain.length > 0
  const agentCount    = hasRealTraces ? traceData.chain.length : PIPELINE_STEPS.length
  const totalTime     = hasRealTraces
    ? formatElapsedMs(traceData.total_elapsed_ms)
    : `~${(TOTAL_ESTIMATED_MS / 1000).toFixed(0)}s`

  return (
    <div className="rounded-xl border border-border/60 bg-card overflow-hidden">

      {/* ── Collapsed header ──────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3.5 hover:bg-muted/30 transition-colors text-left"
      >
        <Sparkles className="h-4 w-4 text-primary/70 shrink-0" />

        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground/80">
            Este módulo fue preparado por {agentCount} agentes de IA
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            {hasRealTraces ? 'Trazas de razonamiento reales disponibles' : 'Sistema de orquestación multiagente'}
            {' · '}
            {totalTime}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {hasRealTraces && (
            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 border border-emerald-300 dark:border-emerald-700 rounded px-1.5 py-0.5 bg-emerald-50 dark:bg-emerald-950/30">
              LIVE
            </span>
          )}
          {open
            ? <ChevronUp className="h-4 w-4 text-muted-foreground" />
            : <ChevronDown className="h-4 w-4 text-muted-foreground" />
          }
        </div>
      </button>

      {/* ── Expanded content ──────────────────────────────────────────── */}
      {open && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-200">

          {/* Divider */}
          <div className="h-px bg-border/60 mx-4" />

          {/* Timeline */}
          <div className="py-2">
            {hasRealTraces
              ? <RealTraceTimeline data={traceData} techMode={techMode} />
              : <SyntheticTimeline techMode={techMode} />
            }
          </div>

          {/* Footer controls */}
          <div className="h-px bg-border/60 mx-4" />
          <div className="px-4 py-2.5 flex items-center justify-between gap-3">

            {/* Tech mode toggle */}
            <button
              type="button"
              onClick={() => setTechMode(v => !v)}
              className={cn(
                'flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-all',
                techMode
                  ? 'border-primary/50 bg-primary/5 text-primary font-medium'
                  : 'border-border text-muted-foreground hover:border-primary/30 hover:text-foreground',
              )}
            >
              <FlaskConical className="h-3 w-3" />
              Modo técnico
            </button>

            {/* Link to full TraceExplorer */}
            {onOpenTechnical && (
              <button
                type="button"
                onClick={onOpenTechnical}
                className="text-xs text-primary/70 hover:text-primary transition-colors underline-offset-2 hover:underline"
              >
                Ver análisis técnico completo →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
