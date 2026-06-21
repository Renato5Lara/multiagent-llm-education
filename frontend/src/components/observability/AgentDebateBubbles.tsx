import { useMemo } from 'react'
import { cn } from '@/lib/utils'
import { useTrace } from '@/hooks/useTrace'
import { extractDebateFromChain, getDebateState } from '@/types/trace'
import type { DebateResolution } from '@/types/trace'

// ── Chat bubble ───────────────────────────────────────────────────────────────

interface BubbleProps {
  icon: string
  agentName: string
  role: string
  message: string
  confidence?: number
  side: 'left' | 'right'
  isWinner?: boolean
  isSynthetic?: boolean
}

function AgentBubble({ icon, agentName, role, message, confidence, side, isWinner, isSynthetic }: BubbleProps) {
  const pct = confidence != null ? Math.round(confidence * 100) : null

  return (
    <div className={cn('flex items-start gap-2.5', side === 'right' && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className="w-9 h-9 rounded-full bg-primary/8 dark:bg-primary/12 border border-border flex items-center justify-center text-base shrink-0 select-none">
        {icon}
      </div>

      {/* Bubble */}
      <div className={cn('flex-1 max-w-[78%] space-y-1', side === 'right' && 'items-end flex flex-col')}>
        <div className="flex items-center gap-1.5 text-xs">
          <span className="font-semibold text-foreground/80">{agentName}</span>
          <span className="text-muted-foreground/50">·</span>
          <span className="text-muted-foreground/60">{role}</span>
          {isWinner && (
            <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-700 rounded px-1 py-0.5 bg-amber-50 dark:bg-amber-950/30">
              FINAL
            </span>
          )}
        </div>

        <div className={cn(
          'rounded-2xl px-4 py-3 text-sm leading-relaxed',
          side === 'left'
            ? 'rounded-tl-sm bg-primary/6 dark:bg-primary/10 text-foreground/85 border border-primary/12'
            : 'rounded-tr-sm bg-muted text-foreground/80 border border-border',
        )}>
          {message}
        </div>

        {/* Confidence bar */}
        {pct !== null && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground/60">
            <div className="h-1 w-20 rounded-full bg-muted overflow-hidden">
              <div className="h-full rounded-full bg-primary/40" style={{ width: `${pct}%` }} />
            </div>
            <span className="tabular-nums">{pct}% confianza</span>
            {isSynthetic && <span className="italic">(estimado)</span>}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Connectors ────────────────────────────────────────────────────────────────

function ConflictConnector() {
  return (
    <div className="flex flex-col items-center gap-1 py-1">
      <div className="h-4 w-px bg-amber-300 dark:bg-amber-700" />
      <div className="flex items-center gap-2 rounded-full border border-amber-300 dark:border-amber-700 bg-amber-50 dark:bg-amber-950/30 px-3 py-1">
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-400">⚡ Posiciones diferentes</span>
      </div>
      <div className="h-4 w-px bg-amber-300 dark:bg-amber-700" />
    </div>
  )
}

function AgreementConnector() {
  return (
    <div className="flex flex-col items-center gap-1 py-1">
      <div className="h-4 w-px bg-emerald-300 dark:bg-emerald-700" />
      <div className="flex items-center gap-2 rounded-full border border-emerald-300 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-950/30 px-3 py-1">
        <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400">✓ Propuesta aceptada</span>
      </div>
      <div className="h-4 w-px bg-emerald-300 dark:bg-emerald-700" />
    </div>
  )
}

function ConsensusConnector({ label }: { label: string }) {
  return (
    <div className="flex flex-col items-center gap-1 py-1">
      <div className="h-4 w-px bg-border" />
      <div className="flex items-center gap-2 rounded-full border border-border bg-muted/40 px-3 py-1">
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <div className="h-4 w-px bg-border" />
    </div>
  )
}

// ── Synthetic debate (no LLM keys) ───────────────────────────────────────────

const SYNTHETIC_MESSAGES = {
  adaptive: 'El perfil del estudiante indica preferencia por aprendizaje conceptual-visual. Propongo nivel intermedio con diagramas y ejemplos prácticos progresivos.',
  evaluation: 'El análisis de Taxonomía Bloom y el historial de errores sugieren consolidación conceptual incompleta. Ajusto la estrategia con validación previa.',
  consensus: 'Se adopta estrategia multimodal con validación progresiva. Nivel calibrado al perfil del estudiante. Plan pedagógico aprobado.',
}

function SyntheticDebate() {
  return (
    <div className="space-y-1.5 animate-in fade-in duration-300">
      <AgentBubble
        icon="🧠"
        agentName="Adaptive Learning Agent"
        role="Propuesta inicial"
        message={SYNTHETIC_MESSAGES.adaptive}
        confidence={0.82}
        side="left"
        isSynthetic
      />
      <ConflictConnector />
      <AgentBubble
        icon="📊"
        agentName="Evaluation Agent"
        role="Análisis de nivel"
        message={SYNTHETIC_MESSAGES.evaluation}
        confidence={0.75}
        side="right"
        isSynthetic
      />
      <ConsensusConnector label="🤝 Resolución" />
      <AgentBubble
        icon="🤝"
        agentName="Consensus Mediator"
        role="Decisión final"
        message={SYNTHETIC_MESSAGES.consensus}
        side="left"
        isWinner
        isSynthetic
      />
      <p className="text-center text-[10px] text-muted-foreground/50 pt-1 italic">
        Ejemplo representativo · trazas reales disponibles al configurar LLM
      </p>
    </div>
  )
}

// ── Real debate from trace data ───────────────────────────────────────────────

function RealDebate({ resolution }: { resolution: DebateResolution }) {
  const state = getDebateState(resolution)

  return (
    <div className="space-y-1.5 animate-in fade-in duration-300">
      <AgentBubble
        icon="🧠"
        agentName={resolution.adaptive_participant.agent_display_name}
        role={`Propone nivel ${resolution.adaptive_participant.proposed_difficulty}`}
        message={resolution.adaptive_participant.rationale}
        confidence={resolution.adaptive_participant.confidence}
        side="left"
        isWinner={resolution.adaptive_participant.is_winner}
      />

      {state === 'conflict' && resolution.evaluation_participant ? (
        <>
          <ConflictConnector />
          <AgentBubble
            icon="📊"
            agentName={resolution.evaluation_participant.agent_display_name}
            role={`Contraargumento: nivel ${resolution.evaluation_participant.proposed_difficulty}`}
            message={resolution.evaluation_participant.rationale}
            confidence={resolution.evaluation_participant.confidence}
            side="right"
            isWinner={resolution.evaluation_participant.is_winner}
          />
        </>
      ) : (
        <AgreementConnector />
      )}

      <ConsensusConnector label="🤝 Resolución del mediador" />

      <AgentBubble
        icon="🤝"
        agentName="Consensus Mediator"
        role={`Nivel final: ${resolution.resolved_difficulty}`}
        message={resolution.resolution_reason}
        side="left"
        isWinner
      />
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  sessionId?: string | null
}

/**
 * AgentDebateBubbles — Sprint G.
 *
 * Chat-bubble timeline of the inter-agent debate between AdaptiveLearning
 * and EvaluationAgent, resolved by ConsensusMediador.
 *
 * Two-layer same as AgentThoughtStream:
 *   Layer 1 — SyntheticDebate: representative example, always visible
 *   Layer 2 — RealDebate:     actual agent rationale from trace data (with LLM)
 *
 * Transitions from Synthetic → Real automatically when traces exist.
 */
export function AgentDebateBubbles({ sessionId }: Props) {
  const { data, isLoading } = useTrace(sessionId ?? undefined)

  const resolution = useMemo(
    () => (data ? extractDebateFromChain(data.chain) : null),
    [data],
  )

  const hasRealDebate = !isLoading && !!resolution && resolution.has_debate_context

  return (
    <div className="space-y-3">
      {hasRealDebate
        ? <RealDebate resolution={resolution} />
        : <SyntheticDebate />
      }
    </div>
  )
}
