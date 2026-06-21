import { useState, useMemo } from "react";
import type { ElementType } from "react";
import { cn } from "@/lib/utils";
import { useTrace } from "@/hooks/useTrace";
import { formatElapsedMs } from "@/types/trace";
import { AgentList } from "./AgentList";
import { AgentThoughtWindow } from "./AgentThoughtWindow";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BrainCircuit,
  Database,
  GitBranch,
  ListOrdered,
  Clock,
  Sparkles,
  Activity,
  AlertTriangle,
} from "lucide-react";

// ── Props ─────────────────────────────────────────────────────────

interface TraceExplorerProps {
  sessionId?: string;
}

// ── Metrics ───────────────────────────────────────────────────────

interface MetricsData {
  agents: number;
  evidence: number;
  dimensions: number;
  steps: number;
  elapsed_ms: number;
  pipeline_decision: string | null;
}

interface MetricChipProps {
  icon: ElementType;
  value: number | string;
  label?: string;
  colorClass: string;
  title?: string;
}

function MetricChip({
  icon: Icon,
  value,
  label,
  colorClass,
  title,
}: MetricChipProps) {
  return (
    <span title={title} className={cn("flex items-center gap-1 text-xs", colorClass)}>
      <Icon className="h-3 w-3" />
      <span className="font-semibold tabular-nums">{value}</span>
      {label && <span className="text-slate-400">{label}</span>}
    </span>
  );
}

function MetricsBar({
  metrics,
  sessionId,
}: {
  metrics: MetricsData;
  sessionId: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {/* Live indicator + label + session ID */}
      <div className="flex items-center gap-1.5">
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
        </span>
        <div>
          <p className="text-xs font-semibold leading-none text-slate-700">
            Pipeline Trace
          </p>
          <p
            className="mt-0.5 font-mono text-[10px] leading-none text-slate-400"
            title={sessionId}
          >
            {sessionId.slice(0, 8)}…
          </p>
        </div>
      </div>

      <div className="h-3.5 w-px bg-slate-200" />

      <MetricChip
        icon={BrainCircuit}
        value={metrics.agents}
        label="agents"
        colorClass="text-blue-600"
        title="Agents in this pipeline run"
      />
      <MetricChip
        icon={Database}
        value={metrics.evidence}
        label="ev"
        colorClass="text-violet-600"
        title="Evidence items read by agents"
      />
      <MetricChip
        icon={GitBranch}
        value={metrics.dimensions}
        label="dim"
        colorClass="text-blue-500"
        title="Decision dimensions evaluated"
      />
      <MetricChip
        icon={ListOrdered}
        value={metrics.steps}
        label="steps"
        colorClass="text-emerald-600"
        title="Reasoning steps recorded"
      />
      <MetricChip
        icon={Clock}
        value={formatElapsedMs(metrics.elapsed_ms)}
        colorClass="text-slate-500"
        title="Total pipeline elapsed time"
      />

      {/* Pipeline decision — the key output of the entire pipeline */}
      {metrics.pipeline_decision && (
        <>
          <div className="h-3.5 w-px bg-slate-200" />
          <div
            title={metrics.pipeline_decision}
            className="flex max-w-[14rem] items-center gap-1.5 rounded-full bg-slate-900 px-2.5 py-1 text-[11px] font-semibold text-white"
          >
            <Sparkles className="h-3 w-3 shrink-0 text-amber-400" />
            <span className="truncate">{metrics.pipeline_decision}</span>
          </div>
        </>
      )}
    </div>
  );
}

// ── State screens ─────────────────────────────────────────────────

function NoSessionState() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <Activity className="mb-3 h-12 w-12 text-slate-200" />
      <p className="text-sm font-medium text-slate-500">No active session.</p>
      <p className="mt-1 text-xs text-slate-400">
        Run a learning session to inspect agent reasoning.
      </p>
    </div>
  );
}

function ExplorerError() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <AlertTriangle className="mb-3 h-12 w-12 text-red-300" />
      <p className="text-sm font-medium text-red-600">
        Unable to load trace data.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Check that the backend /api/trace/session endpoint is reachable.
      </p>
    </div>
  );
}

function EmptyTraceState() {
  return (
    <div className="flex h-full flex-col items-center justify-center p-8 text-center">
      <BrainCircuit className="mb-3 h-12 w-12 text-slate-200" />
      <p className="text-sm font-medium text-slate-600">
        No trace data for this session.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Run the multi-agent pipeline to observe agent reasoning chains.
      </p>
    </div>
  );
}

function ExplorerLoadingSkeleton() {
  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Metrics bar skeleton */}
      <div className="shrink-0 border-b border-slate-200 px-4 py-2.5">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <Skeleton className="h-2 w-2 rounded-full" />
            <div className="space-y-1">
              <Skeleton className="h-3 w-20" />
              <Skeleton className="h-2 w-12" />
            </div>
          </div>
          <Skeleton className="h-3.5 w-px" />
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-4 w-14" />
          ))}
        </div>
      </div>

      {/* Split panel skeleton */}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <div className="h-52 shrink-0 border-b border-slate-200 p-2 md:h-auto md:w-80 md:border-b-0 md:border-r">
          <div className="space-y-1.5">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        </div>
        <div className="flex-1 p-4">
          <Skeleton className="h-full min-h-[200px] w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

// ── Component ─────────────────────────────────────────────────────

export function TraceExplorer({ sessionId }: TraceExplorerProps) {
  const { data, isLoading, isError } = useTrace(sessionId);

  // Tracks the ID the user explicitly clicked in AgentList
  const [userSelectedId, setUserSelectedId] = useState<string | undefined>(
    undefined,
  );

  // Render-phase state update: reset user selection when session changes.
  // React-recommended pattern for deriving state from props without useEffect.
  // See: react.dev/learn/you-might-not-need-an-effect#adjusting-some-state-when-a-prop-changes
  const [prevSessionId, setPrevSessionId] = useState<string | undefined>(
    sessionId,
  );
  if (sessionId !== prevSessionId) {
    setPrevSessionId(sessionId);
    setUserSelectedId(undefined);
  }

  // Derive effective selection: user choice if still valid, otherwise first agent by sequence.
  // This eliminates the useEffect auto-select pattern entirely.
  const selectedTraceId = useMemo(() => {
    if (!data || data.nodes.length === 0) return undefined;
    if (userSelectedId && data.nodes.some((n) => n.id === userSelectedId)) {
      return userSelectedId;
    }
    const first = [...data.nodes].sort((a, b) => a.sequence - b.sequence)[0];
    return first?.id;
  }, [data, userSelectedId]);

  // Aggregate metrics computed from the full chain
  const metrics = useMemo((): MetricsData | null => {
    if (!data) return null;
    return {
      agents: data.total_agents,
      evidence: data.chain.reduce((s, t) => s + t.evidence.length, 0),
      dimensions: data.chain.reduce((s, t) => s + t.dimensions.length, 0),
      steps: data.chain.reduce((s, t) => s + t.reasoning_steps.length, 0),
      elapsed_ms: data.total_elapsed_ms,
      pipeline_decision: data.pipeline_decision,
    };
  }, [data]);

  // Guards — hooks always called before early returns (React rules)
  if (!sessionId) return <NoSessionState />;
  if (isLoading) return <ExplorerLoadingSkeleton />;
  if (isError) return <ExplorerError />;
  if (!data || data.nodes.length === 0) return <EmptyTraceState />;

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* ── Metrics bar ─────────────────────────────────────────── */}
      <div className="shrink-0 border-b border-slate-200 px-4 py-2.5">
        {metrics && <MetricsBar metrics={metrics} sessionId={sessionId} />}
      </div>

      {/* ── Split panel ──────────────────────────────────────────── */}
      {/* min-h-0: flex children can't shrink below intrinsic height  */}
      {/* without this, overflow-y-auto inside children doesn't work  */}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* AgentList column — w-80 for long agent names, h-52 on mobile */}
        <div className="h-52 shrink-0 border-b border-slate-200 p-2 md:h-auto md:w-80 md:border-b-0 md:border-r">
          <AgentList
            sessionId={sessionId}
            selectedTraceId={selectedTraceId}
            onSelect={setUserSelectedId}
          />
        </div>

        {/* AgentThoughtWindow — fills remaining space */}
        {/* min-h-0 required on mobile (flex-col child) for scroll to work */}
        <div className="min-h-0 flex-1 overflow-hidden">
          <AgentThoughtWindow
            sessionId={sessionId}
            traceId={selectedTraceId}
          />
        </div>
      </div>
    </div>
  );
}
