import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import {
  getAgentDisplayName,
  getConfidenceLevel,
  formatElapsedMs,
} from "@/types/trace";
import type { AgentDecisionTrace } from "@/types/trace";
import { Badge } from "@/components/ui/badge";
import {
  Brain,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  Database,
  GitBranch,
  ListOrdered,
  Layers,
  Server,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface ThoughtSummaryProps {
  trace: AgentDecisionTrace;
}

// ── Confidence config ─────────────────────────────────────────────

const CONFIDENCE_CONFIG = {
  high: {
    badge: "bg-green-100 text-green-700 border-green-200",
    bar: "bg-green-500",
    label: "High confidence",
  },
  medium: {
    badge: "bg-amber-100 text-amber-700 border-amber-200",
    bar: "bg-amber-400",
    label: "Medium confidence",
  },
  low: {
    badge: "bg-red-100 text-red-700 border-red-200",
    bar: "bg-red-400",
    label: "Low confidence",
  },
} as const;

// ── Phase labels ──────────────────────────────────────────────────

const PHASE_LABELS: Record<string, string> = {
  research: "Research",
  structural_pedagogical: "Pedagogical",
  adaptive_learning: "Adaptive",
  adaptive_learning_evaluation: "Evaluation",
  multimodal_planning: "Multimodal",
  prompt_engineering: "Prompt Eng.",
  consistency: "Consistency",
  consensus_mediator: "Consensus",
};

function getPhaseLabel(agentType: string): string {
  return PHASE_LABELS[agentType] ?? agentType;
}

// ── Status badge ──────────────────────────────────────────────────

function StatusBadge({
  success,
  error,
}: {
  success: boolean;
  error: string | null;
}) {
  // success=true + error present → partial execution
  if (success && error !== null) {
    return (
      <div className="flex items-center gap-1.5 rounded-full bg-amber-500/20 px-2.5 py-1 text-xs font-medium text-amber-300">
        <AlertTriangle className="h-3.5 w-3.5" />
        Partial
      </div>
    );
  }
  if (success) {
    return (
      <div className="flex items-center gap-1.5 rounded-full bg-green-500/20 px-2.5 py-1 text-xs font-medium text-green-300">
        <CheckCircle2 className="h-3.5 w-3.5" />
        Success
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 rounded-full bg-red-500/20 px-2.5 py-1 text-xs font-medium text-red-300">
      <XCircle className="h-3.5 w-3.5" />
      Failed
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────

export function ThoughtSummary({ trace }: ThoughtSummaryProps) {
  const level = getConfidenceLevel(trace.confidence);
  const config = CONFIDENCE_CONFIG[level];
  const pct = Math.round(trace.confidence * 100);
  const publicOutputKeys = trace.output_keys.filter((k) => !k.startsWith("_"));

  return (
    <div className="space-y-4">
      {/* ── Header card ─────────────────────────────────────────── */}
      <div className="rounded-lg bg-slate-900 p-4 text-white">
        {/* Agent name + status */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
              <Brain className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Agent</p>
              <h3 className="text-base font-semibold leading-tight text-white">
                {getAgentDisplayName(trace.agent_name)}
              </h3>
            </div>
          </div>

          <StatusBadge success={trace.success} error={trace.error} />
        </div>

        {/* Badges — phase + position + elapsed */}
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Badge
            variant="outline"
            className="border-white/20 bg-white/10 text-xs text-white hover:bg-white/10"
          >
            <Layers className="mr-1 h-3 w-3" />
            {getPhaseLabel(trace.agent_type)}
          </Badge>
          <Badge
            variant="outline"
            className="border-white/20 bg-white/10 text-xs text-white hover:bg-white/10"
          >
            #{trace.sequence + 1} in pipeline
          </Badge>
          <Badge
            variant="outline"
            className="border-white/20 bg-white/10 text-xs text-white hover:bg-white/10"
          >
            <Clock className="mr-1 h-3 w-3" />
            {formatElapsedMs(trace.elapsed_ms)}
          </Badge>
        </div>

        {/* Confidence bar */}
        <div className="mt-3">
          <div className="mb-1 flex items-center justify-between">
            <span className="flex items-center gap-1 text-xs text-slate-400">
              <ShieldCheck className="h-3 w-3" />
              {config.label}
            </span>
            <span
              className={cn(
                "rounded-full border px-2 py-0.5 text-[10px] font-bold",
                config.badge,
              )}
            >
              {pct}%
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
            <div
              className={cn(
                "h-full rounded-full transition-all duration-500",
                config.bar,
              )}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Trace IDs — demonstrates observability during thesis defense */}
        <div className="mt-3 border-t border-white/10 pt-3">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                Trace ID
              </p>
              <p
                className="mt-0.5 cursor-default font-mono text-[11px] text-slate-300"
                title={trace.trace_id}
              >
                {trace.trace_id.slice(0, 8)}…
              </p>
            </div>
            {trace.correlation_id && (
              <div>
                <p className="text-[10px] font-medium uppercase tracking-wide text-slate-500">
                  Correlation
                </p>
                <p
                  className="mt-0.5 cursor-default font-mono text-[11px] text-slate-300"
                  title={trace.correlation_id}
                >
                  {trace.correlation_id.slice(0, 8)}…
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Decision summary ─────────────────────────────────────── */}
      <div>
        <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Decision Summary
        </p>
        <div className="rounded-md border-l-4 border-slate-900 bg-slate-50 px-4 py-3">
          <p className="text-sm leading-relaxed text-slate-800">
            {trace.decision_summary || "No summary recorded for this agent."}
          </p>
        </div>
      </div>

      <hr className="border-slate-200" />

      {/* ── Stats grid ───────────────────────────────────────────── */}
      <div>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Reasoning Components
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          <StatCard
            icon={Database}
            label="Evidence"
            value={trace.evidence.length}
            color="violet"
          />
          <StatCard
            icon={GitBranch}
            label="Dimensions"
            value={trace.dimensions.length}
            color="blue"
          />
          <StatCard
            icon={ListOrdered}
            label="Steps"
            value={trace.reasoning_steps.length}
            color="emerald"
          />
          <StatCard
            icon={Server}
            label="Memory reads"
            value={trace.memory_records_queried}
            color="amber"
            tooltip={
              trace.memory_records_queried === 0
                ? "No shared memory accessed"
                : `${trace.memory_records_queried} SharedMemory records read`
            }
          />
        </div>
      </div>

      {/* ── Output keys (internal keys filtered out) ─────────────── */}
      {publicOutputKeys.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Output Keys
          </p>
          <div className="flex flex-wrap gap-1.5">
            {publicOutputKeys.map((key) => (
              <span
                key={key}
                className="rounded-md bg-slate-100 px-2 py-0.5 font-mono text-[11px] text-slate-600"
              >
                {key}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ── Error / warning block ─────────────────────────────────── */}
      {trace.error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3">
          <div className="mb-1 flex items-center gap-1.5 text-xs font-semibold text-red-700">
            <AlertTriangle className="h-3.5 w-3.5" />
            {trace.success ? "Warning" : "Agent Error"}
          </div>
          <p className="font-mono text-xs text-red-600">{trace.error}</p>
        </div>
      )}
    </div>
  );
}

// ── StatCard ──────────────────────────────────────────────────────

const STAT_COLORS = {
  violet: "bg-violet-50 text-violet-700 border-violet-100",
  blue: "bg-blue-50 text-blue-700 border-blue-100",
  emerald: "bg-emerald-50 text-emerald-700 border-emerald-100",
  amber: "bg-amber-50 text-amber-700 border-amber-100",
} as const;

interface StatCardProps {
  icon: ElementType;
  label: string;
  value: number;
  color: keyof typeof STAT_COLORS;
  tooltip?: string;
}

function StatCard({ icon: Icon, label, value, color, tooltip }: StatCardProps) {
  return (
    <div
      title={tooltip}
      className={cn(
        "rounded-lg border p-3 text-center",
        STAT_COLORS[color],
        value === 0 && "opacity-50",
      )}
    >
      <Icon className="mx-auto mb-1 h-4 w-4 opacity-70" />
      <p className="text-lg font-bold leading-none">{value}</p>
      <p className="mt-0.5 text-[10px] font-medium opacity-70">{label}</p>
    </div>
  );
}
